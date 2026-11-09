"""Explicit, resumable capture plans and closed-loop JPEG recentering."""
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import time
from .capture_service import capture_one
from .geometry import correction_target
from .indi import IndiClient
from .mount_service import profile
from .sky import Site,eod_position,visibility
from .solve import Position,separation_arcsec,solve_jpeg
from .timekeeping import load_settings,utc_now

@dataclass
class Block:
    count:int=10
    exposure:float=30
    iso:str='Cámara'
    frame_type:str='Light'
    delay:float=3
    def validate(self):
        if not isinstance(self.count,int) or not 1<=self.count<=10000: raise ValueError('Entre 1 y 10000 tomas por bloque.')
        if not all(math.isfinite(x) for x in (self.exposure,self.delay)) or not .001<=self.exposure<=3600 or not 0<=self.delay<=3600: raise ValueError('Exposición o pausa fuera de rango.')
        if self.frame_type not in ('Light','Dark','Flat','Bias'): raise ValueError('Tipo de toma inválido.')
        if len(self.iso)>20: raise ValueError('ISO inválido.')

def state_path(): return Path.home()/'.local/state/astroall/session.json'
def save_state(value,path=None):
    path=Path(path or state_path());path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(path)

def recenter(target,field_deg,exposure=2,iso='Cámara',stop=None,emit=lambda _:None,tolerance_arcsec=60,max_correction_deg=2,max_attempts=3,capture=capture_one,solver=solve_jpeg,client_factory=IndiClient,first_shot=None):
    if not 5<=tolerance_arcsec<=3600 or not 0<max_correction_deg<=5 or not 1<=max_attempts<=5: raise ValueError('Límites de centrado inválidos.')
    site=Site.from_settings(load_settings());cfg=profile();cache=Path.home()/'.cache/astroall/jpg'
    with client_factory() as client:
        device=cfg['device'];client.get(device,'EQUATORIAL_EOD_COORD')
        for attempt in range(max_attempts+1):
            if stop and stop.is_set(): client.abort(device);raise RuntimeError('Centrado detenido.')
            view=visibility(target,site)
            if view['alt_deg']<10: raise ValueError('El objetivo está por debajo de 10°; centrado cancelado.')
            client.wait_slew(device,stop)
            shot=first_shot if attempt==0 and first_shot is not None else capture(cache,exposure,iso,stop)
            if shot.get('interrupted'): raise RuntimeError('Toma de centrado interrumpida.')
            solved=solver(shot['jpeg'],field_deg,[Path.home()/'astroall-data/indexes','/usr/share/astrometry'])
            distance=separation_arcsec(solved,target)
            emit({'event':'center','attempt':attempt,'error_arcsec':distance,'jpeg':shot['jpeg']})
            if distance<=tolerance_arcsec: return {'centered':True,'error_arcsec':distance,'attempts':attempt,'jpeg':shot['jpeg']}
            if attempt==max_attempts: raise RuntimeError(f'No se alcanzó el centrado: error {distance:.0f}″. No se iniciaron las tomas principales.')
            client.collect(.2);coords=client.get(device,'EQUATORIAL_EOD_COORD')['values']
            now=utc_now()
            mount_position=Position(float(coords['RA'])*15,float(coords['DEC']))
            correction=correction_target(mount_position,eod_position(solved,site,now),eod_position(target,site,now),max_correction_deg)
            if abs((correction.ra_deg-mount_position.ra_deg+180)%360-180)>5 or abs(correction.dec_deg-mount_position.dec_deg)>5:
                raise ValueError('La corrección exige más de 5° en un eje; centra manualmente, especialmente cerca del polo. No se envió movimiento.')
            client.goto_eod(device,correction.ra_deg/15,correction.dec_deg);client.wait_slew(device,stop)
            if stop and stop.wait(2): client.abort(device);raise RuntimeError('Centrado detenido.')
    raise RuntimeError('Centrado no confirmado.')

def execute(blocks,targets=None,guide=False,dither_every=0,recenter_every=0,field_deg=None,stop=None,emit=lambda _:None,capture=capture_one,state_file=None,goto_first=False,recenter_options=None):
    blocks=list(blocks);targets=list(targets or [None])
    if not blocks or len(blocks)>100 or not targets or len(targets)>81: raise ValueError('Plan vacío o demasiado grande.')
    for block in blocks: block.validate()
    if not isinstance(dither_every,int) or not 0<=dither_every<=1000 or not isinstance(recenter_every,int) or not 0<=recenter_every<=1000: raise ValueError('Intervalos de corrección inválidos.')
    if dither_every and not guide: raise ValueError('Dither requiere cámara guía y PHD2 estabilizado.')
    if recenter_every and (not field_deg or targets==[None]): raise ValueError('Centrado requiere un objetivo del atlas y el campo de tu lente.')
    if recenter_every and (not math.isfinite(field_deg) or not .01<=field_deg<=170):raise ValueError('Campo de la lente inválido para el centrado.')
    if len(targets)>1 and not recenter_every: raise ValueError('Los mosaicos requieren activar centrado para verificar cada encuadre.')
    total=sum(b.count for b in blocks)*len(targets);completed=0
    state={'version':1,'status':'ready','completed':0,'total':total,'blocks':[asdict(b) for b in blocks],
           'targets':[asdict(t) if t else None for t in targets],'last_shot':None,'uncertain_shot':False,
           'note':'Nunca se reanuda ni se repite una exposición automáticamente después de reiniciar.'}
    cache=Path.home()/'.cache/astroall/jpg';phd=None
    options=dict(recenter_options or {})
    if not set(options)<= {'exposure','tolerance_arcsec'}:raise ValueError('Opciones de centrado inválidas.')
    try:
        if guide:
            from .guiding import PHD2Client
            phd=PHD2Client().__enter__();phd.assert_guiding()
        for target_index,target in enumerate(targets):
            if stop and stop.is_set(): break
            if target and (goto_first or recenter_every) and any(b.frame_type=='Light' for b in blocks):
                site=Site.from_settings(load_settings());view=visibility(target,site)
                if view['alt_deg']<10: raise ValueError('Objetivo no visible por encima de 10°.')
                if phd: phd.request('set_paused',[True,'full'])
                with IndiClient() as client:
                    device=profile()['device'];client.goto_eod(device,view['ra_hours_eod'],view['dec_deg_eod']);client.wait_slew(device,stop)
                if recenter_every: recenter(target,field_deg,stop=stop,emit=emit,capture=capture,**options)
                if phd:
                    phd.request('set_paused',[False]);phd.start_guiding(stop=stop)
            for block_index,block in enumerate(blocks):
                if block.frame_type in ('Dark','Bias'): emit({'event':'notice','message':'Comprueba que la tapa esté colocada; la aplicación no controla una tapa motorizada.'})
                for shot_index in range(block.count):
                    if stop and stop.is_set(): break
                    if phd and block.frame_type=='Light': phd.assert_guiding()
                    if target and block.frame_type=='Light':
                        site=Site.from_settings(load_settings())
                        if visibility(target,site)['alt_deg']<10: raise ValueError('El objetivo bajó de 10°; secuencia detenida.')
                    state.update(status='exposing',uncertain_shot=True,target_index=target_index,block_index=block_index,shot_index=shot_index)
                    save_state(state,state_file)
                    result=capture(cache,block.exposure,block.iso,stop)
                    state.update(uncertain_shot=False,last_shot=result)
                    if result.get('interrupted'): state['status']='stopped';save_state(state,state_file);return state
                    completed+=1;state.update(completed=completed,status='between_exposures');save_state(state,state_file)
                    emit(dict(result,event='shot',shot=completed,total=total,frame_type=block.frame_type,target=target.label if target else 'Campo actual'))
                    if completed<total and not (stop and stop.is_set()):
                        if recenter_every and target and block.frame_type=='Light' and completed%recenter_every==0:
                            if phd: phd.request('set_paused',[True,'full'])
                            recenter(target,field_deg,stop=stop,emit=emit,capture=capture,first_shot=result,**options)
                            if phd:
                                phd.request('set_paused',[False]);phd.start_guiding(stop=stop)
                        if phd and dither_every and block.frame_type=='Light' and completed%dither_every==0:
                            emit({'event':'notice','message':'Dither: esperando estabilización real de PHD2…'});phd.dither(stop=stop)
                        if stop:
                            if stop.wait(block.delay): break
                        else: time.sleep(block.delay)
                if stop and stop.is_set(): break
        state['status']='complete' if completed==total else 'stopped';save_state(state,state_file);return state
    except Exception as exc:
        state.update(status='error',error=str(exc));save_state(state,state_file);raise
    finally:
        if phd: phd.__exit__()
