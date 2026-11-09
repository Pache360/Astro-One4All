"""Explicit V4L2 capture-device selection. Never substitutes another camera."""
import json
import os
from pathlib import Path
import re
import struct
from datetime import datetime,timezone

def state_path(): return Path.home()/'.local/state/astroall/guide-camera-diagnostic.json'

def diagnostic(**values):
    path=state_path();path.parent.mkdir(parents=True,exist_ok=True)
    try: previous=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError): previous={}
    previous.update(values,utc=datetime.now(timezone.utc).isoformat())
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(previous,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)

def device_identity(node,sys_root=Path('/sys/class/video4linux')):
    try:
        device=(sys_root/Path(node).name/'device').resolve()
        for parent in (device,*device.parents):
            if (parent/'idVendor').is_file() and (parent/'idProduct').is_file():
                def read(name):
                    try: return (parent/name).read_text().strip()
                    except OSError: return ''
                removable=read('removable')
                return {'usb_id':read('idVendor')+':'+read('idProduct'),'removable':removable,
                        'role':'internal' if removable=='fixed' else 'external' if removable=='removable' else 'unknown'}
    except OSError: pass
    return {'role':'unknown','removable':'unknown'}


def profile_path(): return Path.home()/'.config/astroall/guide-camera.json'


def profile():
    try: return json.loads(profile_path().read_text(encoding='utf-8'))
    except (OSError,ValueError): return {}


def save_profile(value):
    path=profile_path();path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)


def query_device(path):
    """QUERYCAP only: no streaming, exposure or format changes."""
    import fcntl
    with open(path,'rb',buffering=0) as stream:
        data=bytearray(104);fcntl.ioctl(stream.fileno(),0x80685600,data,True)
    driver,card,bus,version,caps,device_caps=struct.unpack_from('16s32s32sIII',data)
    capabilities=device_caps if caps & 0x80000000 else caps
    return {'name':card.split(b'\0')[0].decode(errors='replace'),
            'bus':bus.split(b'\0')[0].decode(errors='replace'),
            'capture':bool(capabilities & 1)}


def video_devices(dev_root=Path('/dev'),probe=query_device,identify=device_identity):
    """Exclude metadata-only nodes; keep stable by-id/by-path aliases."""
    aliases={}
    for directory in ('v4l/by-path','v4l/by-id'):
        for link in sorted((dev_root/directory).glob('*')):
            if link.is_symlink(): aliases[str(link.resolve())]=str(link)
    devices=[]
    try: confirmed=json.loads(state_path().read_text(encoding='utf-8')).get('confirmed_usb',{})
    except (OSError,ValueError): confirmed={}
    for node in sorted(dev_root.glob('video*')):
        if not re.fullmatch(r'video\d+',node.name): continue
        try: info=probe(str(node))
        except (OSError,ValueError): continue
        if not info['capture']: continue
        stable=aliases.get(str(node.resolve()),str(node))
        identity=identify(str(node))
        # A name is only a hint; a fixed USB port is stronger evidence.
        # "Integrated Camera" is also the actual Acteck USB product name.
        # Only the fixed sysfs port establishes an internal camera. A product
        # name alone must not hide a removable camera.
        if confirmed.get('path')==stable and confirmed.get('name')==info['name']: identity['role']='external_confirmed'
        role={'internal':'Integrada','external':'USB externa','external_confirmed':'USB identificada','possibly_internal':'Posible integrada','unknown':'USB / verificar'}[identity['role']]
        devices.append(dict(info,**identity,path=stable,node=str(node),
                            label=f"{role} — {info['name']} · {node.name}"))
    return devices

def scan_devices():
    devices=video_devices();diagnostic(stage='inventory',devices=devices)
    return devices

def usb_difference(before,after):
    """Identify the unplugged webcam, without guessing from /dev/video numbers."""
    current={d['path'] for d in after}
    missing=[d for d in before if d['path'] not in current]
    buses={d['bus'] for d in missing}
    if len(buses)!=1: raise RuntimeError('No se identificó una única cámara retirada. Desconecta solo la webcam USB y vuelve a intentarlo.')
    return sorted(missing,key=lambda d:d['node'])[0]

def compatible_video(client,device):
    """Prefer a small decoded UVC mode on the explicitly selected webcam."""
    def choose(name,member,force=False):
        prop=client.properties.get((device,name))
        if not prop or member not in prop['values'] or (prop['values'][member]=='On' and not force):return False
        if client.properties.get((device,'CCD_VIDEO_STREAM'),{}).get('values',{}).get('STREAM_ON')=='On' or client.properties.get((device,'CCD_EXPOSURE'),{}).get('state')=='Busy':
            raise RuntimeError('Detén las exposiciones de PHD2 antes de cambiar el formato de la webcam.')
        client.switch(device,name,member)
        return True
    formats=client.properties.get((device,'V4L2_FORMAT'),{}).get('values',{})
    yuyv=next((name for name in formats if name.strip().upper().startswith('YUYV')),None)
    if yuyv:choose('V4L2_FORMAT',yuyv)
    # INDI 1.9.9 may renegotiate the kernel size when changing pixel format
    # without updating PrimaryCCD/Streamer. Reapply even an already-On size:
    # the size handler synchronizes the dimensions and allocates the buffers.
    if not choose('V4L2_SIZE_DISCRETE','640x480',force=True):return {}
    import time
    import xml.etree.ElementTree as ET
    client.send(ET.Element('getProperties',{'version':'1.7','device':device}))
    deadline=time.monotonic()+3
    while True:
        client.collect(.25)
        frames={}
        for name in ('CCD_FRAME','CCD_STREAM_FRAME'):
            values=client.properties.get((device,name),{}).get('values',{})
            if 'WIDTH' in values and 'HEIGHT' in values:frames[name]=[int(float(values['WIDTH'])),int(float(values['HEIGHT']))]
        if frames.get('CCD_FRAME')==[640,480] and all(size==[640,480] for size in frames.values()):
            return {'width':640,'height':480,'confirmed_frames':frames}
        if time.monotonic()>=deadline:
            diagnostic(stage='geometry_error',expected_frame=[640,480],reported_frames=frames)
            raise RuntimeError(f'El controlador no sincronizó la resolución 640 × 480: {frames}. No se inició vídeo con tamaños diferentes.')


def monochrome(client,device,force=False):
    for name,member in (('CCD_CAPTURE_FORMAT','INDI_MONO'),('Image Depth','8 bits'),
                        ('CCD_TRANSFER_FORMAT','FORMAT_FITS'),('CCD_STREAM_ENCODER','RAW')):
        prop=client.properties.get((device,name))
        if prop and member in prop['values'] and (prop['values'].get(member)!='On' or (force and name=='CCD_CAPTURE_FORMAT')):
            if client.properties.get((device,'CCD_VIDEO_STREAM'),{}).get('values',{}).get('STREAM_ON')=='On' or client.properties.get((device,'CCD_EXPOSURE'),{}).get('state')=='Busy':
                raise RuntimeError('Detén las exposiciones de PHD2 antes de configurar el vídeo monocromo.')
            client.switch(device,name,member)


def selected_device(path,devices=None,expected=None):
    if devices is None: devices=video_devices()
    selected=next((d for d in devices if d['path']==path),None)
    if not selected: raise RuntimeError('La cámara elegida no está disponible. Conéctala y pulsa Buscar cámaras; no se usará la integrada como sustituta.')
    if expected is not None:
        if any(expected.get(k)!=selected[k] for k in ('path','name','bus')):
            raise RuntimeError('La lista de cámaras cambió. Pulsa Buscar cámaras y vuelve a elegir la USB.')
        return selected
    saved=profile()
    if path==saved.get('path') and any(saved.get(k) and saved[k]!=selected[k] for k in ('name','bus')):
        raise RuntimeError('El puerto ahora corresponde a otra cámara. Vuelve a seleccionarla en Buscar cámaras.')
    return selected


def configure_camera(client,device,selected,allow_switch=False):
    # libindi/V4L2 1.9.9 has a short device-name buffer. Some real by-id
    # names (including ALK-1054-200710) are truncated. Persist the stable ID,
    # but pass the freshly verified, short kernel node to this driver.
    driver_path=selected['node']
    if not re.fullmatch(r'/dev/video\d+',driver_path): raise ValueError('Puerto de vídeo Linux inválido.')
    def same_port(value):
        return value in (selected['path'],driver_path) or (value and Path(value).resolve()==Path(driver_path).resolve())
    port=client.get(device,'DEVICE_PORT')['values'].get('PORT')
    connected=client.get(device,'CONNECTION')['values'].get('CONNECT')=='On'
    busy=client.properties.get((device,'CCD_EXPOSURE'),{}).get('state')=='Busy'
    streaming=client.properties.get((device,'CCD_VIDEO_STREAM'),{}).get('values',{}).get('STREAM_ON')=='On'
    if connected and (not same_port(port) or (allow_switch and (busy or streaming))):
        if not allow_switch:
            raise RuntimeError('Desconecta la cámara en PHD2 antes de cambiarla; el guiado actual no se interrumpió.')
        # An abandoned preview can leave video active. When PHD2 is not running,
        # this explicit connection action closes only the guide-camera driver
        # and reopens the selected webcam, never the mount or Canon USB.
        client.switch(device,'CONNECTION','DISCONNECT');connected=False
    if not connected:
        client.write(device,'DEVICE_PORT',{'PORT':driver_path},'Text')
        client.switch(device,'CONNECTION','CONNECT')
    actual=client.get(device,'DEVICE_PORT')['values'].get('PORT')
    if not same_port(actual) or client.get(device,'CONNECTION')['values'].get('CONNECT')!='On':
        raise RuntimeError('INDI no confirmó la cámara seleccionada. No se probó otra cámara.')
    video_mode=compatible_video(client,device)
    # Changing a hardware format can also leave Streamer's RGB/mono layout
    # stale even when the public INDI_MONO switch already says On.
    monochrome(client,device,force=True)
    save_profile(dict(selected,indi_device=device,driver_port=driver_path,video_mode=video_mode))
    diagnostic(stage='connected',selected=dict(selected,indi_device=device),video_mode=video_mode,error=None)
    return f"Cámara conectada: {selected['name']} ({selected['node']}). En PHD2: INDI Camera → {device}."
