"""One polar measurement using the existing, exclusive capture services."""
from pathlib import Path
import math
import uuid
from .polar_camera import PolarSample,orientation
from .timekeeping import load_settings,utc_now
from .solve import solve_frame


def require_idle_guiding():
    from .guiding import PHD2Client
    from .guide_profile import phd_running
    try:
        with PHD2Client() as client:state=client.request('get_app_state')
    except (OSError,RuntimeError) as exc:
        if phd_running():raise RuntimeError('PHD2 está abierto y no se pudo comprobar su estado. Detén sus exposiciones o ciérralo antes de alinear.') from exc
        return
    if state not in ('Stopped','Selected'):
        raise RuntimeError('Detén las exposiciones y el guiado de PHD2 antes de medir la alineación polar. No se detuvo ni desconectó ningún equipo automáticamente.')


def configuration(source,sensor,focal,guide_field,exposure,ready):
    from .optics import field_width
    from .recommendations import SENSORS
    from .equipment import load
    from .guide_camera import profile
    if not ready:raise ValueError('Primero comprueba el enfoque, la firmeza del equipo y la fecha/hora, y marca la casilla de preparación.')
    settings=load_settings()
    if not settings.get('clock_confirmed') or settings.get('latitude') is None or settings.get('longitude') is None:
        raise ValueError('Conecta el OAT y lee hora/ubicación, o completa esos datos en «Hora y ubicación».')
    site=tuple(float(settings.get(k,0)) for k in ('latitude','longitude','elevation'))
    from .polar_camera import local_frame
    local_frame(utc_now(settings).isoformat(),*site)
    seconds=float(exposure)
    if not math.isfinite(seconds) or not .1<=seconds<=15:raise ValueError('Usa una exposición de prueba de 0.1 a 15 segundos.')
    if source=='main':
        width=field_width(SENSORS[sensor][0],float(focal));equipment=load()
        identity='main:'+equipment['main_model']+'|'+equipment['main_port']
    elif source=='guide':
        saved=profile()
        if not saved.get('indi_device') or not saved.get('path'):raise ValueError('Conecta y prueba primero tu cámara USB desde Autoguiado. La cámara guía es opcional.')
        width=float(guide_field) if str(guide_field).strip() else None
        if width is not None and (not math.isfinite(width) or not .01<=width<=170):raise ValueError('Campo guía en grados: deja vacío si no lo conoces.')
        identity='guide:'+saved['path']+'|'+saved.get('bus','')
    else:raise ValueError('Selecciona la cámara que tomará las imágenes.')
    return {'source':source,'identity':identity,'width_deg':width,'seconds':seconds,'site':site}


def measure(config,stop=None,mount_dec=None):
    from .capture_service import capture_one,require_persistence
    from .solve import solver_status
    if not solver_status()['ready']:raise RuntimeError('Falta el motor o los índices de plate solving. Usa la Live completa antes de tomar fotos para alinear.')
    require_persistence();require_idle_guiding()
    if stop and stop.is_set():raise RuntimeError('Medición detenida antes de capturar.')
    if config['source']=='main':
        shot=capture_one(Path.home()/'.cache/astroall/jpg',config['seconds'],stop=stop)
        if shot.get('interrupted'):raise RuntimeError('La exposición se interrumpió. Esta imagen no se usará para alinear.')
        image,mid=shot['jpeg'],shot['approx_mid_utc']
    else:
        from .guide_preview import capture_preview
        from .storage import JpegCache
        cache=JpegCache(Path.home()/'.cache/astroall/polar-guide',budget=16*1024*1024,max_file=4*1024*1024)
        cache.reserve(4*1024*1024)
        destination=cache.root/(uuid.uuid4().hex+'.jpg')
        shot=capture_preview(stop=stop,exposure=config['seconds'],destination=destination,full_size=True)
        mid=shot['approx_mid_utc'];image=shot['jpeg']
    if stop and stop.is_set():raise RuntimeError('Medición detenida después de capturar. La foto permanece guardada; no se volverá a disparar automáticamente.')
    solved=solve_frame(image,config['width_deg'],[Path.home()/'astroall-data/indexes','/usr/share/astrometry'])
    basis=orientation(solved,mid,*config['site'])
    return PolarSample(solved,mid,str(image),config['identity'],basis.tolist(),mount_dec)
