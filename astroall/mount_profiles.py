"""Named OAT connections; board metadata never programs pins or motor drivers."""
import json,uuid
from pathlib import Path

BOARDS=['Sin especificar','Mega 2560 + RAMPS 1.4','Arduino Mega 2560','MKS Gen L v1','MKS Gen L v2','MKS Gen L v2.1','ESP32 ESP32DEV','Otra placa con firmware OAT']
DRIVERS={'OAT propio · firmware 1.13.x':'indi_astroall_oat','INDI OpenAstroTech · verificar versión':'indi_lx200_OpenAstroTech','Simulador explícito':'indi_simulator_telescope'}

def path():return Path.home()/'.config/astroall/mount-profiles.json'
def load():
    try:
        data=json.loads(path().read_text(encoding='utf-8'))
        if data['selected'] in data['profiles'] and 1<=len(data['profiles'])<=20:return data
    except (OSError,ValueError,KeyError,TypeError):pass
    from .mount_service import profile
    from .timekeeping import load_settings
    return {'selected':'default','profiles':{'default':{'label':'Mi OpenAstroTracker','board':'Sin especificar',
            'time_source':'oat' if load_settings().get('use_mount_time',True) else 'pc','connection':profile()}}}
def write(data):
    target=path();target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(target)
def sync_active(connection):
    if not path().exists():return
    bank=load();bank['profiles'][bank['selected']]['connection']=dict(connection);write(bank)
def create(label,board,connection,time_source='pc'):
    from .mount_service import MOUNT_DRIVERS
    if not label.strip() or len(label)>80 or board not in BOARDS:raise ValueError('Nombre o placa del perfil inválidos.')
    if connection.get('driver') not in MOUNT_DRIVERS or str(connection.get('baud')) not in ('9600','19200','38400','57600','115200'):
        raise ValueError('Controlador o baudios no válidos.')
    if connection.get('port') and (not connection['port'].startswith('/dev/') or len(connection['port'])>256):raise ValueError('Puerto serie Linux inválido.')
    if time_source not in ('oat','pc'):raise ValueError('Fuente de hora inválida.')
    bank=load()
    if len(bank['profiles'])>=20:raise ValueError('Máximo de 20 perfiles.')
    if any(p['label'].casefold()==label.strip().casefold() for p in bank['profiles'].values()):raise ValueError('Ya existe un perfil con ese nombre; elige otro.')
    key=uuid.uuid4().hex[:12];bank['profiles'][key]={'label':label.strip(),'board':board,'connection':dict(connection),'time_source':time_source};write(bank)
    return key
def activate(key):
    bank=load()
    if key not in bank['profiles']:raise ValueError('Perfil no encontrado.')
    changed=bank['selected']!=key;bank['selected']=key;write(bank)
    from .mount_service import save_profile
    current=bank['profiles'][key];save_profile(current['connection'])
    from .timekeeping import load_settings,write_settings
    clock=load_settings();clock['use_mount_time']=current['time_source']=='oat'
    if changed and clock.pop('clock_anchor',None):
        clock['clock_confirmed']=False;clock.pop('clock_source',None)
    write_settings(clock);return current
