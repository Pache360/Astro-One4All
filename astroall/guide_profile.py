"""Add a dedicated PHD2 profile while preserving the user's other profiles."""
import configparser
import io
import math
import os
from pathlib import Path
import re
import shutil
import subprocess

NAME='Astro One4All - USB + OAT'

def phd_running():
    return os.name=='posix' and subprocess.run(['pgrep','-u',str(os.getuid()),'-x',r'phd2(\.bin)?'],capture_output=True).returncode==0


def prepare(camera,mount,focal=None,pixel=None,path=None,check_running=True,camera_id=''):
    if check_running and phd_running():
        raise RuntimeError('Cierra PHD2 antes de preparar su perfil. Después vuelve a abrirlo desde aquí.')
    for value,label in ((camera,'cámara'),(mount,'montura')):
        if not value or any(c in value for c in '\n\r[]='): raise ValueError('Nombre de '+label+' inválido.')
    dimensions={}
    for value,label,key in ((focal,'Focal guía','FocalLength'),(pixel,'Tamaño de píxel','pixelsize')):
        if value not in (None,''):
            number=float(value)
            if not math.isfinite(number) or not 0<number<100000: raise ValueError(label+' debe ser positivo.')
            dimensions[key]=number
    path=Path(path) if path else Path.home()/'.PHDGuidingV2'
    original=path.read_text(encoding='utf-8') if path.exists() else ''
    config=configparser.RawConfigParser(strict=True,interpolation=None,delimiters=('='));config.optionxform=str
    config.read_string('[root]\n'+original)
    identifiers=[int(m.group(1)) for section in config.sections() if (m:=re.fullmatch(r'profile/(\d+)',section))]
    existing=next((i for i in identifiers if config.get(f'profile/{i}','name',fallback='').startswith(NAME)
                   and config.get(f'profile/{i}','AstroallCameraID',fallback='')==camera_id
                   and config.get(f'profile/{i}/indi','INDImount',fallback='')==mount),None)
    identifier=existing or max(identifiers,default=0)+1
    base=f'profile/{identifier}'
    def set_values(section,values):
        if not config.has_section(section): config.add_section(section)
        for key,value in values.items(): config.set(section,key,str(value))
    set_values('root',{'ConfigVersion':2001,'currentProfile':identifier,'ServerMode':1})
    set_values(base,{'name':NAME+f' ({identifier})','AstroallCameraID':camera_id})
    set_values(base+'/camera',{'LastMenuChoice':'INDI Camera','AutoLoadDarks':0,'AutoLoadDefectMap':0})
    set_values(base+'/scope',{'LastMenuChoice':'INDI Mount'})
    # Let PHD2 use its translated "None" defaults in every interface language.
    for section,key in ((base+'/scope','LastAuxMenuChoice'),(base+'/stepguider','LastMenuChoice'),(base+'/rotator','LastMenuChoice')):
        if config.has_section(section): config.remove_option(section,key)
    set_values(base+'/indi',{'INDIhost':'localhost','INDIport':7624,'INDIcam':camera,'INDImount':mount,
                             'INDIcam_ccd':0,'INDIcam_forcevideo':1,'INDIcam_forceexposure':0})
    if 'FocalLength' in dimensions: set_values(base+'/frame',{'focalLength':dimensions['FocalLength']})
    if 'pixelsize' in dimensions: set_values(base+'/camera',{'pixelsize':dimensions['pixelsize']})
    # Preserve calibration for the same equipment; a new camera requires a new calibration.
    stream=io.StringIO();config.write(stream,space_around_delimiters=False)
    content=stream.getvalue().removeprefix('[root]\n')
    if path.exists():
        backup=path.with_name(path.name+'.before-astroall033')
        if not backup.exists(): shutil.copy2(path,backup)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.astroall-new');temporary.write_text(content,encoding='utf-8');temporary.replace(path)
    return f'Perfil PHD2 preparado: {NAME}. Cámara {camera}; montura {mount}. Abre PHD2 y conecta el equipo. Verifica focal y tamaño de píxel reales antes de calibrar.'
