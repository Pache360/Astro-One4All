#!/usr/bin/python3
"""Read-only Canon connection probe. Never captures, resets USB or kills owners."""
import fcntl
import json
import locale
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime,timezone


def run(gp,home=None):
    home=Path(home or Path.home())
    data={'probe_only':True,'photos_requested':0,'started_utc':datetime.now(timezone.utc).isoformat(),
          'stage':'preparing','driver_messages':[],'uid':os.getuid(),'groups':os.getgroups()}
    def message(*args):
        values=[str(arg) for arg in args if isinstance(arg,str)]
        if values: data['driver_messages']=(data['driver_messages']+[' '.join(values)[:2000]])[-30:]
    lock_dir=home/'.cache/astroall';lock_dir.mkdir(parents=True,exist_ok=True)
    camera=None;initialized=False
    with (lock_dir/'camera.lock').open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            data['library']=list(gp.gp_library_version(0))
            context=gp.Context();context_callbacks=[context.set_error_func(message,None),context.set_status_func(message,None)]
            data['stage']='detecting_usb'
            detected=gp.Camera.autodetect(context)
            data['detected']=[{'model':str(model),'port':str(port)} for model,port in detected]
            selected=[item for item in data['detected'] if item['model']=='Canon EOS R50']
            if len(selected)!=1: raise RuntimeError('Se necesita una sola Canon EOS R50 por USB. No se abrió otra cámara.')
            selected=selected[0]
            camera=gp.Camera()
            abilities=gp.CameraAbilitiesList();abilities.load(context)
            camera.set_abilities(abilities[abilities.lookup_model(selected['model'])])
            ports=gp.PortInfoList();ports.load()
            camera.set_port_info(ports[ports.lookup_path(selected['port'])])
            if selected['port'].startswith('usb:'):
                bus,number=selected['port'][4:].split(',')
                device=Path('/dev/bus/usb')/bus/number
                data['usb_access']={'path':str(device),'readable':os.access(device,os.R_OK),'writable':os.access(device,os.W_OK)}
                owners=subprocess.run(['/usr/bin/fuser','-v',str(device)],capture_output=True,text=True,timeout=5)
                data['usb_owners']=(owners.stdout+owners.stderr)[:6000]
            data['stage']='initializing_usb'
            camera.init(context);initialized=True
            data['stage']='reading_settings';data['settings']={}
            for name in ('autoexposuremode','imageformat','capturetarget','shutterspeed'):
                widget=camera.get_single_config(name,context)
                data['settings'][name]=str(widget.get_value())
            data.update(stage='complete',result='connection_ok')
        except Exception as exc:
            data.update(result='failed',failed_stage=data['stage'],error=str(exc),error_type=type(exc).__name__)
        finally:
            if initialized:
                try: camera.exit(context)
                except Exception as exc: data['exit_error']=str(exc)
    path=home/'.local/state/astroall/canon-usb-check.json';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    return data,path


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    os.environ.update(LC_ALL='C',LANGUAGE='C');locale.setlocale(locale.LC_ALL,'C')
    import gphoto2 as gp
    print('Comprobación USB Canon · no toma fotos ni cambia ajustes. Cierra antes Astro One4All y otros programas de cámara.\n',flush=True)
    data,path=run(gp)
    print(json.dumps(data,ensure_ascii=False,indent=2))
    print('\nRegistro guardado en '+str(path))
