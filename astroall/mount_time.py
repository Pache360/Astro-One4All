"""Read OAT's stored site/clock with the v1.13 Meade sign conventions.

These getters cannot establish a current satellite fix. The LCD is the source
of that confirmation; no acquisition, clock-setting or EEPROM command is sent.
"""
from datetime import datetime,timedelta,timezone
import re
import time

def degrees(text,limit):
    match=re.fullmatch(r'([+-]?)(\d{2,3})\*(\d{2})',text)
    if not match or int(match[3])>=60: raise ValueError('Coordenada OAT inválida: '+repr(text))
    value=(int(match[2])+int(match[3])/60)*(-1 if match[1]=='-' else 1)
    if abs(value)>limit: raise ValueError('Coordenada OAT fuera de rango.')
    return value

def hours(text):
    if not re.fullmatch(r'\d{6}',text): raise ValueError('Hora sidérea/HA OAT inválida.')
    h,m,s=int(text[:2]),int(text[2:4]),int(text[4:])
    if h>=24 or m>=60 or s>=60: raise ValueError('Hora OAT fuera de rango.')
    return h+m/60+s/3600

def read_site_time(protocol):
    command=lambda text:protocol.command(text,'hash')
    date=command(':GC#');before=time.monotonic();clock=command(':GL#');sampled=(before+time.monotonic())/2
    offset=command(':GG#');latitude=degrees(command(':Gt#'),90)
    # LX200/OAT Gg: west positive; the rest of the application: east positive.
    longitude=(-degrees(command(':Gg#'),360)+180)%360-180
    if command(':GC#')!=date: raise ValueError('Cambió la fecha al consultar OAT; pulsa Leer hora/ubicación otra vez.')
    if not re.fullmatch(r'[+-]?\d{1,2}',offset) or not -14<=int(offset)<=14: raise ValueError('Desfase UTC OAT inválido.')
    local=datetime.strptime(date+' '+clock,'%m/%d/%y %H:%M:%S')
    utc=(local+timedelta(hours=int(offset))).replace(tzinfo=timezone.utc)
    if not 2023<=utc.year<=2099: raise ValueError('El reloj OAT no tiene una fecha utilizable; comprueba GPS en el LCD.')
    return {'UTC':utc.isoformat(),'LAT':str(latitude),'LON':str(longitude),'MONOTONIC':str(sampled),
            'LST_HOURS':str(hours(command(':XGL#'))),'OAT_HA_HOURS':str(hours(command(':XGH#'))),
            'SOURCE':'OAT stored clock/site; GPS fix must be confirmed on LCD'}
