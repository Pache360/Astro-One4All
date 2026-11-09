"""Read OAT's stored site/clock with the v1.13 Meade sign conventions.

read_site_time() only reads: it cannot establish a current satellite fix.
The LCD is the source of that confirmation; no acquisition, clock-setting
or EEPROM command is sent by the reader.

gps_sync() is the explicit opt-in exception: it sends :gT<timeout_ms>#
(the OAT GPS acquisition command, ported from Poly OAT) and waits for the
single-character reply '1' (fix) or '0' (timeout). It only runs when the
user asks for it, never on connect and never inside read_site_time().
No EEPROM command is sent anywhere in this module.
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

def gps_sync(protocol, timeout_ms=30000):
    """Send :gT<timeout_ms># and wait for the GPS fix reply.

    Returns True when the firmware answers '1' (fix acquired; clock and
    site updated from the NEO-6M), False when it answers '0' (no fix
    within the timeout). The call can block up to timeout_ms plus a 10 s
    margin: run it from the driver process or a worker thread, never
    from the UI thread. Ported from Poly OAT (gps.py: fetch_gps /
    gps_sync). This is a GPS acquisition command, not an EEPROM write
    and not a motion-parameter change.
    """
    if not 1000 <= int(timeout_ms) <= 120000:
        raise ValueError('Tiempo máximo GPS fuera de rango (1000–120000 ms).')
    reply = protocol.command(':gT%d#' % int(timeout_ms), 'char', timeout=int(timeout_ms) / 1000 + 10)
    if reply not in ('0', '1'):
        raise ValueError('Respuesta GPS OAT no reconocida: %r.' % reply)
    return reply == '1'

def sync_site_time(protocol, timeout_ms=30000):
    """Sync clock/site from GPS (:gT#) and then read the stored values.

    Returns the read_site_time() dict plus 'GPS_SYNC' ('1' with fix, '0'
    without) and a SOURCE that says whether the values come from a fresh
    GPS fix or from the stored clock/site. When there is no fix the
    stored values are still returned, clearly marked, so the caller can
    decide: nothing here invents a position or a time.
    """
    synced = gps_sync(protocol, timeout_ms)
    result = read_site_time(protocol)
    result['GPS_SYNC'] = '1' if synced else '0'
    result['SOURCE'] = ('OAT GPS sync (:gT#); fix adquirido' if synced else
                        'OAT stored clock/site; GPS sync sin fix (:gT#=0) — confirma GPS en el LCD')
    return result

def read_site_time(protocol):
    command=lambda text:protocol.command(text,'hash')
    date=command(':GC#');before=time.monotonic();clock=command(':GL#');sampled=(before+time.monotonic())/2
    offset=command(':GG#');latitude=degrees(command(':Gt#'),90)
    # LX200/OAT Gg: west positive; the rest of the application: east positive.
    longitude=(-degrees(command(':Gg#'),360)+180)%360-180
    if command(':GC#')!=date: raise ValueError('Cambió la fecha al consultar OAT; pulsa Sincronizar GPS otra vez.')
    if not re.fullmatch(r'[+-]?\d{1,2}',offset) or not -14<=int(offset)<=14: raise ValueError('Desfase UTC OAT inválido.')
    local=datetime.strptime(date+' '+clock,'%m/%d/%y %H:%M:%S')
    utc=(local+timedelta(hours=int(offset))).replace(tzinfo=timezone.utc)
    if not 2023<=utc.year<=2099: raise ValueError('El reloj OAT no tiene una fecha utilizable; comprueba GPS en el LCD.')
    return {'UTC':utc.isoformat(),'LAT':str(latitude),'LON':str(longitude),'MONOTONIC':str(sampled),
            'LST_HOURS':str(hours(command(':XGL#'))),'OAT_HA_HOURS':str(hours(command(':XGH#'))),
            'SOURCE':'OAT stored clock/site; GPS fix must be confirmed on LCD'}
