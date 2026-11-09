"""Shared mount profile, explicit server start and bounded worker hand control."""
import json
from pathlib import Path
import queue
import shutil
import socket
import subprocess
import threading
import time
import os
import stat
from .indi import IndiClient,IndiRejected

SERVER_LOCK=threading.RLock()
MOUNT_DRIVERS=('indi_astroall_oat','indi_lx200_OpenAstroTech','indi_simulator_telescope')
CAMERA_DRIVERS=('indi_v4l2_ccd','indi_simulator_ccd')

def profile_path(): return Path.home()/'.config/astroall/mount.json'
def profile():
    defaults={'driver':'indi_astroall_oat','device':'Astro One4All OAT','port':'','baud':'19200'}
    try: defaults.update(json.loads(profile_path().read_text(encoding='utf-8')))
    except (OSError,ValueError): pass
    # Migrate the prototype's generic GPS driver to the OAT-specific profile.
    if defaults['driver']=='indi_lx200gps': defaults.update(driver='indi_astroall_oat',device='Astro One4All OAT')
    return defaults
def save_profile(value):
    path=profile_path();path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2),encoding='utf-8');temp.replace(path)
    from .mount_profiles import sync_active
    sync_active(value)
def serial_ports():
    paths=sorted(str(x) for x in Path('/dev/serial/by-id').glob('*'))
    return paths or sorted(str(x) for pattern in ('ttyACM*','ttyUSB*') for x in Path('/dev').glob(pattern))
def fifo_path(): return Path.home()/'.cache/astroall/indi.fifo'
def _start_server(driver):
    if driver not in ('indi_astroall_oat','indi_lx200_OpenAstroTech','indi_simulator_telescope'): raise ValueError('Perfil no permitido.')
    try:
        with socket.create_connection(('127.0.0.1',7624),timeout=.5): return 'Ya hay un servidor INDI en funcionamiento; se utilizará el existente.'
    except OSError: pass
    if not shutil.which('indiserver') or not shutil.which(driver): raise RuntimeError('Este controlador necesita la Live USB de Astro One4All.')
    log=Path.home()/'.local/state/astroall/indi.log';log.parent.mkdir(parents=True,exist_ok=True)
    fifo=fifo_path();fifo.parent.mkdir(parents=True,exist_ok=True)
    if fifo.exists():
        info=fifo.stat()
        if not stat.S_ISFIFO(info.st_mode) or info.st_uid!=os.getuid(): raise RuntimeError('El canal de control INDI no pertenece a este usuario.')
    else: os.mkfifo(fifo,0o600)
    if log.exists() and log.stat().st_size>1024*1024: log.replace(log.with_suffix('.previous.log'))
    with log.open('ab') as stream: subprocess.Popen(['indiserver','-p','7624','-f',str(fifo),driver],stdout=subprocess.DEVNULL,stderr=stream,start_new_session=True)
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        try:
            with socket.create_connection(('127.0.0.1',7624),timeout=.3): return 'Controlador disponible. El puerto del Arduino se abre al pulsar Conectar.'
        except OSError: time.sleep(.1)
    raise RuntimeError('El controlador no inició; revisa el diagnóstico de INDI.')

def driver_devices(client,driver):
    return [d for (d,n),p in client.properties.items() if n=='DRIVER_INFO'
            and p['values'].get('DRIVER_EXEC','').rsplit('/',1)[-1]==driver
            and (d,'CONNECTION') in client.properties]

def load_driver(driver):
    if driver not in MOUNT_DRIVERS+CAMERA_DRIVERS or not shutil.which(driver):
        raise RuntimeError('Ese controlador no está instalado en esta Live.')
    fifo=fifo_path()
    if not fifo.exists() or not stat.S_ISFIFO(fifo.stat().st_mode) or fifo.stat().st_uid!=os.getuid():
        raise RuntimeError('El servidor INDI existente no usa el canal de esta aplicación. Configura el controlador en ese servidor.')
    descriptor=os.open(fifo,os.O_WRONLY|os.O_NONBLOCK)
    try: os.write(descriptor,('start '+driver+'\n').encode('ascii'))
    finally: os.close(descriptor)

def start_server(driver):
    with SERVER_LOCK:
        result=_start_server(driver)
        with IndiClient() as client:
            deadline=time.monotonic()+(5 if result.startswith('Controlador disponible') else 1)
            while not driver_devices(client,driver) and time.monotonic()<deadline: client.collect(.3)
            if not driver_devices(client,driver):
                if result.startswith('Controlador disponible'): raise RuntimeError('El controlador iniciado no anunció su montura; revisa el diagnóstico INDI.')
                load_driver(driver)
                deadline=time.monotonic()+6
                while not driver_devices(client,driver) and time.monotonic()<deadline: client.collect(.3)
                if not driver_devices(client,driver): raise RuntimeError('El servidor INDI no anunció el controlador solicitado.')
        return result

def add_guide_camera(driver='indi_v4l2_ccd',path=None,expected=None):
    if driver not in ('indi_v4l2_ccd','indi_simulator_ccd'): raise ValueError('Perfil de cámara guía no permitido.')
    if not shutil.which(driver): raise RuntimeError('Ese controlador de cámara guía no está instalado.')
    from .guide_camera import selected_device,configure_camera
    selected=selected_device(path,expected=expected) if driver=='indi_v4l2_ccd' else None
    with SERVER_LOCK:
        start_server(profile()['driver'])
        with IndiClient() as client:
            devices=driver_devices(client,driver)
            if not devices:
                load_driver(driver);deadline=time.monotonic()+6
                while not devices and time.monotonic()<deadline:
                    client.collect(.3);devices=driver_devices(client,driver)
            if driver=='indi_v4l2_ccd':
                matching=[d for d in devices if client.get(d,'DEVICE_PORT')['values'].get('PORT') in (selected['path'],selected['node'])]
                device=matching[0] if len(matching)==1 else devices[0] if len(devices)==1 else None
                if not device: raise RuntimeError('INDI anuncia varias cámaras; selecciona el dispositivo exacto en PHD2.')
                from .guide_profile import phd_running
                try: return configure_camera(client,device,selected,allow_switch=not phd_running())
                except Exception as exc:
                    from .guide_camera import diagnostic
                    diagnostic(stage='connection_error',selected=selected,error=str(exc));raise
            if len(devices)!=1: raise RuntimeError('No se encontró una única cámara simulada.')
            client.switch(devices[0],'CONNECTION','CONNECT')
            return 'Cámara simulada conectada en INDI: '+devices[0]

class HandController:
    """Persistent INDI client; no UI-thread network waits or serial ownership."""
    def __init__(self,post,status,error):
        self.post,self.status,self.error=post,status,error
        self.commands=queue.Queue(maxsize=32);self.closing=threading.Event();self.held=None
        self.device=None;self.client=None
        self.connecting=False
        threading.Thread(target=self.run,daemon=True).start()
    def submit(self,action,*args):
        if action=='connect':self.connecting=True
        try: self.commands.put_nowait((action,args))
        except queue.Full:
            if action=='connect':self.connecting=False
            self.held=None;self.error('Mando ocupado; se soltó el movimiento manual.')
    def hold(self,direction): self.held=direction
    def release(self): self.held=None
    def close(self): self.held=None;self.closing.set()
    def run(self):
        last=None;heartbeat=0;next_status=0
        try:
            while not self.closing.is_set():
                try:
                    action,args=self.commands.get(timeout=.05)
                    if action=='connect':
                        cfg=args[0];start_server(cfg['driver'])
                        if self.client: self.client.__exit__()
                        self.client=IndiClient().__enter__()
                        devices=driver_devices(self.client,cfg['driver'])
                        self.device=cfg['device'] if cfg['device'] in devices else devices[0] if len(devices)==1 else None
                        if not self.device: raise RuntimeError('No se encontró la montura de ese perfil en INDI; una cámara no puede ocupar su lugar.')
                        save_profile(dict(cfg,device=self.device))
                        self.client.connect_mount(self.device,cfg['port'],cfg['baud'])
                        sample=self.client.properties.get((self.device,'OAT_SITE_TIME'),{}).get('values',{})
                        if sample.get('MONOTONIC') and time.monotonic()-float(sample['MONOTONIC'])>110:
                            try: self.client.switch(self.device,'OAT_READ_SITE_TIME','READ')
                            except IndiRejected as exc:
                                message=str(exc);self.post(lambda m=message:self.error('Montura conectada; refresca hora/ubicación al terminar el movimiento: '+m))
                        save_profile(dict(cfg,device=self.device));last=None;self.connecting=False
                    elif not self.client: raise RuntimeError('Conecta primero la montura.')
                    elif action=='disconnect':
                        self.held=None;self.client.switch(self.device,'CONNECTION','DISCONNECT');self.client.__exit__();self.client=None
                        self.post(lambda:self.status({}))
                    elif action=='abort': self.held=None;self.client.abort(self.device);last=None
                    elif action=='track': self.client.switch(self.device,'TELESCOPE_TRACK_STATE','TRACK_ON' if args[0] else 'TRACK_OFF')
                    elif action=='rate':
                        keys=list(self.client.get(self.device,'TELESCOPE_SLEW_RATE')['values']);self.client.switch(self.device,'TELESCOPE_SLEW_RATE',keys[int(args[0])])
                    elif action=='read_time': self.client.switch(self.device,'OAT_READ_SITE_TIME','READ')
                    elif action=='home': self.held=None;self.client.switch(self.device,'OAT_EXISTING_HOME','GO')
                    elif action=='park': self.held=None;self.client.switch(self.device,'TELESCOPE_PARK','PARK' if args[0] else 'UNPARK')
                    elif action=='goto': self.held=None;self.client.goto_eod(self.device,*args)
                except queue.Empty: pass
                except Exception as exc:
                    if action=='connect':self.connecting=False
                    self.held=None;message=str(exc);self.post(lambda m=message:self.error(m))
                    if action=='connect' and self.client:
                        self.client.__exit__();self.client=None
                        self.post(lambda:self.status({}))
                if self.client:
                    try:
                        now=time.monotonic();held=self.held
                        if held!=last:
                            if last: self.client.motion(self.device,axis='NS' if last in 'ns' else 'WE')
                            last=held;heartbeat=0
                        if held and now>=heartbeat:
                            self.client.motion(self.device,held);heartbeat=time.monotonic()+.35
                        self.client.collect(.03)
                        if now>=next_status:
                            snapshot=self.client.snapshot(self.device);self.post(lambda s=snapshot:self.status(s));next_status=now+.7
                    except IndiRejected as exc:
                        self.held=None;last=None
                        # A rejected move is not a lost serial connection. Explicitly
                        # release this client's manual axes; leave GoTo/tracking alone.
                        for axis in ('NS','WE'):
                            try: self.client.motion(self.device,axis=axis)
                            except IndiRejected: pass
                            except Exception:
                                self.client.__exit__();self.client=None
                                self.post(lambda:self.status({}));break
                        message=str(exc);self.post(lambda m=message:self.error('Orden no aplicada: '+m))
                    except Exception as exc:
                        self.held=None;last=None;message=str(exc)
                        self.post(lambda m=message:self.error('Enlace perdido: '+m))
                        self.client.__exit__();self.client=None
                        self.post(lambda:self.status({}))
        finally:
            if self.client:
                try:
                    if last: self.client.motion(self.device,axis='NS' if last in 'ns' else 'WE')
                except Exception: pass
                self.client.__exit__()
