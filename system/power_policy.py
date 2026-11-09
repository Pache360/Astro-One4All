"""Dedicated Live policy: awake display, no automatic suspend/hibernate."""
from pathlib import Path
import os
import re
import shutil

SLEEP='[Sleep]\nAllowSuspend=no\nAllowHibernation=no\nAllowHybridSleep=no\nAllowSuspendThenHibernate=no\n'
LOGIN='[Login]\nIdleAction=ignore\nHandleLidSwitch=ignore\nHandleLidSwitchExternalPower=ignore\nHandleLidSwitchDocked=ignore\n'

def install(root,write):
    root=Path(root)
    def put(relative,text,mode=0o644):
        path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
        previous=path.stat() if path.exists() else None
        write(path,text,mode)
        if previous and os.name=='posix':os.chown(path,previous.st_uid,previous.st_gid)
        return path
    put('etc/systemd/sleep.conf.d/90-astroall-awake.conf',SLEEP)
    put('etc/systemd/logind.conf.d/90-astroall-awake.conf',LOGIN)
    put('usr/local/bin/astroall-awake','#!/bin/sh\nexport PYTHONPATH="/opt/astroall-current:/opt/astroall${PYTHONPATH:+:$PYTHONPATH}"\nexec /usr/bin/python3 -m astroall.awake\n',0o755)
    put('etc/xdg/autostart/astroall-awake.desktop','[Desktop Entry]\nType=Application\nName=Astro One4All - Pantalla encendida\nExec=/usr/local/bin/astroall-awake\nTerminal=false\n')
    put('etc/xdg/autostart/xscreensaver.desktop','[Desktop Entry]\nType=Application\nName=Screen saver\nHidden=true\n')
    # Preserve unrelated desktop startup programs and retain the original file.
    for relative in ('etc/xdg/lxsession/LXDE/autostart','etc/skel/.config/lxsession/LXDE/autostart','home/astro/.config/lxsession/LXDE/autostart'):
        path=root/relative
        if not path.exists():continue
        text=path.read_text();updated=re.sub(r'(?m)^\s*@?(?:/usr/bin/)?xscreensaver\b[^\n]*\n?','',text)
        if updated!=text:
            backup=path.with_name(path.name+'.before-astroall0312')
            if not backup.exists():shutil.copy2(path,backup)
            put(relative,updated)

if __name__=='__main__':
    root=Path('/')
    if not (root/'etc/astroall-live').is_file():raise SystemExit('Solo para Astro One4All Live.')
    def atomic(path,text,mode):
        temp=path.with_name(path.name+'.astroall-new');temp.write_text(text);temp.chmod(mode);temp.replace(path)
    install(root,atomic)
