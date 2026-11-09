"""User-selected equipment, independent of optional guiding/focus workflows."""
import json,os,re
from pathlib import Path

def path():return Path.home()/'.config/astroall/equipment.json'

def load():
    defaults={'main_model':'','main_port':'','guide_enabled':False,'guide_path':'','focus':'manual'}
    try:defaults.update(json.loads(path().read_text(encoding='utf-8')))
    except (OSError,ValueError):pass
    return defaults

def save(value):
    value={key:value.get(key,default) for key,default in {'main_model':'','main_port':'','guide_enabled':False,'guide_path':'','focus':'manual'}.items()}
    if not isinstance(value['main_model'],str) or len(value['main_model'])>200:raise ValueError('Modelo de cámara inválido.')
    if value['main_port'] and not re.fullmatch(r'usb:\d+,\d+',value['main_port']):raise ValueError('Selecciona un puerto USB de la lista detectada.')
    if not isinstance(value['guide_enabled'],bool) or value['focus']!='manual':raise ValueError('Configuración de accesorios inválida.')
    if value['guide_path'] and (not value['guide_path'].startswith('/dev/') or len(value['guide_path'])>256):raise ValueError('Cámara guía inválida.')
    target=path();target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(target)
    return value

def inventory():
    from .mount_service import serial_ports
    from .guide_camera import video_devices
    result={'ports':serial_ports(),'cameras':[],'guide':video_devices(),'note':''}
    if os.name!='posix':result['note']='Busca los dispositivos físicos dentro de la Live Linux.';return result
    try:
        import gphoto2 as gp
        result['cameras']=[{'model':str(model),'port':str(port),'label':str(model)+' · '+str(port)} for model,port in gp.Camera.autodetect()]
    except Exception as exc:result['note']='No se pudo enumerar la cámara principal: '+str(exc)
    return result

def apply_camera_selection(camera,gp,settings=None,context=None):
    settings=load() if settings is None else settings
    model,port=settings.get('main_model'),settings.get('main_port')
    detections=[(str(m),str(p)) for m,p in gp.Camera.autodetect(context)]
    if not detections:raise RuntimeError('No se detectó una cámara principal por USB. Enciéndela en modo foto/M, comprueba el cable de datos y su opción de conexión USB.')
    matches=[(m,p) for m,p in detections if (not model or m==model) and (not port or p==port)]
    # USB bus addresses are not stable across power cycles or hub reconnects.
    # A unique selected MODEL may move; never substitute a different model or
    # guess between two identical cameras.
    moved=False
    if not matches and model:
        matches=[(m,p) for m,p in detections if m==model];moved=bool(matches)
    if len(matches)!=1:raise RuntimeError('La cámara principal seleccionada no está disponible de forma única. Busca equipo en Sistema y elígela otra vez; no se usó otra cámara.')
    model,port=matches[0]
    ports=gp.PortInfoList();ports.load();camera.set_port_info(ports[ports.lookup_path(port)])
    abilities=gp.CameraAbilitiesList();abilities.load(context);camera.set_abilities(abilities[abilities.lookup_model(model)])
    return {'model':model,'port':port,'port_changed':moved,'detected_count':len(detections)}
