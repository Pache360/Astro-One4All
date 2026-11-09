"""Small validated beginner preferences. No device is opened by saving them."""
import json,math
from pathlib import Path
from .recommendations import SENSORS

DEFAULTS={'sensor':'APS-C Canon','focal':50.,'iso':'800','minutes':60,'delay':3.,'jpg_correction':True,
          'jpg_every':10,'jpg_exposure':2.,'tolerance_arcsec':60.,'night_start':False,'show_internal_guide':False}
def path():return Path.home()/'.config/astroall/preferences.json'
def validate(value):
    value={k:value.get(k,d) for k,d in DEFAULTS.items()}
    if value['sensor'] not in SENSORS or str(value['iso']) not in ('Cámara','100','200','400','800','1600','3200','6400'):raise ValueError('Formato de sensor o ISO inválido.')
    for name,low,high in (('focal',1,5000),('minutes',1,600),('delay',0,3600),('jpg_every',1,1000),('jpg_exposure',.1,30),('tolerance_arcsec',5,3600)):
        number=float(value[name])
        label={'focal':'Focal','minutes':'Minutos de integración','delay':'Pausa','jpg_every':'Intervalo de corrección','jpg_exposure':'Exposición de comprobación','tolerance_arcsec':'Error permitido'}[name]
        if not math.isfinite(number) or not low<=number<=high:raise ValueError(f'{label}: usa un valor entre {low} y {high}.')
        if name in ('minutes','jpg_every') and not number.is_integer():raise ValueError('La cantidad debe ser un número entero.')
        value[name]=int(number) if name in ('minutes','jpg_every') else number
    for name in ('jpg_correction','night_start','show_internal_guide'):
        if not isinstance(value[name],bool):raise ValueError('Opción de configuración inválida.')
    return value
def load():
    try:return validate(json.loads(path().read_text(encoding='utf-8')))
    except (OSError,ValueError,TypeError):return dict(DEFAULTS)
def save(value):
    value=validate(value);target=path();target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(target)
    return value
