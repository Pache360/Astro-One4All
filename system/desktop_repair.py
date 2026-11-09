"""Repair the logout routes without altering unrelated desktop preferences."""
from pathlib import Path
import re
import os


def repair(root,write):
    root=Path(root)
    original_write=write
    def write(path,text,mode=0o755):
        previous=path.stat() if path.exists() else None
        original_write(path,text,mode)
        if previous and os.name=='posix': os.chown(path,previous.st_uid,previous.st_gid)
    write(root/'usr/local/bin/lxde-logout', '#!/bin/sh\nexec /usr/bin/lxsession-logout --banner /usr/share/lxde/images/logout-banner.png --side=top "$@"\n')
    paths=[root/'etc/xdg/lxpanel/LXDE/config',root/'home/astro/.config/lxpanel/LXDE/config']
    for path in paths:
        if not path.exists() and 'home' in path.relative_to(root).parts: continue
        text=path.read_text() if path.exists() else '[Command]\n'
        if re.search(r'(?m)^Logout=',text): text=re.sub(r'(?m)^Logout=.*$', 'Logout=/usr/bin/lxsession-logout',text)
        elif '[Command]' in text: text=text.replace('[Command]','[Command]\nLogout=/usr/bin/lxsession-logout',1)
        else: text+='\n[Command]\nLogout=/usr/bin/lxsession-logout\n'
        path.parent.mkdir(parents=True,exist_ok=True);write(path,text,0o644)
    for relative in ('etc/xdg/lxsession/LXDE/desktop.conf','home/astro/.config/lxsession/LXDE/desktop.conf'):
        path=root/relative
        if path.exists():
            text=re.sub(r'(?m)^quit_manager/command=(?:lxde-logout|lxsession-logout)$',
                        'quit_manager/command=/usr/bin/lxsession-logout',path.read_text())
            write(path,text,0o644)
    path=root/'usr/share/applications/lxde-logout.desktop'
    if path.exists():
        text=re.sub(r'(?m)^Exec=.*$', 'Exec=/usr/bin/lxsession-logout',path.read_text())
        write(path,text,0o644)
    path=root/'etc/xdg/openbox/LXDE/menu.xml'
    if path.exists(): write(path,path.read_text().replace('<command>lxde-logout</command>','<command>/usr/bin/lxsession-logout</command>'),0o644)
