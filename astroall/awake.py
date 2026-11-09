"""Keep the dedicated Live display awake without touching host OS settings."""
from datetime import datetime,timezone
import ctypes as ct
import ctypes.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def state_path():return Path.home()/'.local/state/astroall/power.json'

def _run(args):
    try:
        result=subprocess.run(args,capture_output=True,text=True,timeout=4,env=dict(os.environ,LC_ALL='C'))
        return result.returncode,(result.stdout+result.stderr).strip()[-6000:]
    except (OSError,subprocess.TimeoutExpired) as exc:return -1,str(exc)

def live():return os.name=='posix' and Path('/etc/astroall-live').is_file()

def screen_state(timeout,dpms_supported,dpms_enabled):
    disabled=timeout==0
    dpms_disabled=not dpms_supported or not dpms_enabled
    return {'screensaver_disabled':disabled,'dpms_disabled_or_unavailable':dpms_disabled,
            'screen_kept_on':disabled and dpms_disabled,'screensaver_timeout_seconds':timeout,
            'dpms_supported':dpms_supported,'dpms_enabled':dpms_enabled}

def display_state(enforce=False):
    x11=ct.CDLL(ctypes.util.find_library('X11') or 'libX11.so.6')
    x11.XOpenDisplay.argtypes=[ct.c_char_p];x11.XOpenDisplay.restype=ct.c_void_p
    x11.XCloseDisplay.argtypes=[ct.c_void_p]
    x11.XFlush.argtypes=[ct.c_void_p]
    x11.XSetScreenSaver.argtypes=[ct.c_void_p,ct.c_int,ct.c_int,ct.c_int,ct.c_int]
    x11.XForceScreenSaver.argtypes=[ct.c_void_p,ct.c_int]
    x11.XGetScreenSaver.argtypes=[ct.c_void_p]+[ct.POINTER(ct.c_int)]*4
    display=x11.XOpenDisplay(None)
    if not display:raise RuntimeError('No se pudo consultar la pantalla X11.')
    try:
        if enforce:
            x11.XSetScreenSaver(display,0,0,0,1);x11.XForceScreenSaver(display,0)
        ext=ct.CDLL(ctypes.util.find_library('Xext') or 'libXext.so.6')
        ext.DPMSQueryExtension.argtypes=[ct.c_void_p,ct.POINTER(ct.c_int),ct.POINTER(ct.c_int)]
        ext.DPMSCapable.argtypes=[ct.c_void_p]
        ext.DPMSInfo.argtypes=[ct.c_void_p,ct.POINTER(ct.c_ushort),ct.POINTER(ct.c_ubyte)]
        ext.DPMSForceLevel.argtypes=[ct.c_void_p,ct.c_ushort]
        ext.DPMSDisable.argtypes=[ct.c_void_p]
        event,error=ct.c_int(),ct.c_int()
        supported=bool(ext.DPMSQueryExtension(display,ct.byref(event),ct.byref(error)) and ext.DPMSCapable(display))
        enabled,level=ct.c_ubyte(),ct.c_ushort()
        if supported:
            if not ext.DPMSInfo(display,ct.byref(level),ct.byref(enabled)):raise RuntimeError('No se confirmó el estado DPMS.')
            if enforce:
                if enabled.value:ext.DPMSForceLevel(display,0)
                ext.DPMSDisable(display)
                if not ext.DPMSInfo(display,ct.byref(level),ct.byref(enabled)):raise RuntimeError('No se confirmó el nuevo estado DPMS.')
        x11.XFlush(display)
        timeout,interval,blanking,exposures=[ct.c_int() for _ in range(4)]
        x11.XGetScreenSaver(display,ct.byref(timeout),ct.byref(interval),ct.byref(blanking),ct.byref(exposures))
        result=screen_state(timeout.value,supported,bool(enabled.value));result['monitor_power_level']=level.value if supported else None
        return result
    finally:x11.XCloseDisplay(display)

def status():
    try:value=json.loads(state_path().read_text(encoding='utf-8'))
    except (OSError,ValueError):value={}
    if not live():return {'live':False,'applied':False}
    value.update(live=True)
    if os.environ.get('DISPLAY'):
        try:value.update(display_state())
        except Exception as exc:value.update(screen_kept_on=False,power_query_error=str(exc))
    policy=Path('/etc/systemd/sleep.conf.d/90-astroall-awake.conf')
    value['sleep_policy_installed']=policy.is_file() and 'AllowSuspend=no' in policy.read_text()
    return value

def apply():
    if not live() or not os.environ.get('DISPLAY'):return {'live':live(),'applied':False,'reason':'Sin sesión gráfica Live'}
    errors=[]
    # Exit only the screen saver belonging to this X session. The installer
    # removes its autostart, so it will not undo the X11 settings later.
    if shutil.which('xscreensaver-command'):_run(['xscreensaver-command','-exit'])
    try:display_state(enforce=True)
    except Exception as exc:errors.append(str(exc))
    value=status();value.update(applied=bool(value.get('screen_kept_on')),errors=errors,utc=datetime.now(timezone.utc).isoformat())
    boot=Path('/proc/sys/kernel/random/boot_id')
    if boot.exists():value['boot_id']=boot.read_text().strip()
    path=state_path();path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,prefix='power-',delete=False) as temp:
        json.dump(value,temp,ensure_ascii=False,indent=2);temporary=Path(temp.name)
    temporary.replace(path)
    return value

if __name__=='__main__':print(json.dumps(apply(),ensure_ascii=False))
