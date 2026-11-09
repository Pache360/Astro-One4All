"""UTC-first clocks. Never silently substitute Oaxaca city coordinates or GPS."""
from datetime import datetime, timezone, timedelta
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo
import time
import os

DEFAULT_ZONE = "America/Mexico_City"


def settings_path():
    return Path.home()/".config/astroall/time.json"


def load_settings():
    try:
        value = json.loads(settings_path().read_text(encoding="utf-8"))
        ZoneInfo(value["timezone"])
        if value.get('clock_anchor') and not anchor_valid(value['clock_anchor']):
            value['clock_confirmed']=False
            value['clock_note']='Vuelve a conectar el OAT o confirma el reloj del PC después de arrancar.'
        return value
    except (OSError, ValueError, KeyError):
        return {"timezone": DEFAULT_ZONE, "longitude": None, "clock_confirmed": False}


def save_settings(zone_name, longitude=None, clock_confirmed=False, latitude=None, elevation=None):
    ZoneInfo(zone_name)
    if longitude is not None and (not math.isfinite(longitude) or not -180 <= longitude <= 180):
        raise ValueError("Longitud inválida: oeste negativo, entre -180 y 180°.")
    previous=load_settings()
    if latitude is None: latitude=previous.get('latitude')
    if elevation is None: elevation=previous.get('elevation',0)
    if latitude is not None and (not math.isfinite(latitude) or not -90<=latitude<=90): raise ValueError('Latitud inválida.')
    if not math.isfinite(elevation) or not -500<=elevation<=10000: raise ValueError('Elevación inválida.')
    value = {"timezone": zone_name, "longitude": longitude, "latitude":latitude,'elevation':elevation,"clock_confirmed": bool(clock_confirmed),
             'use_mount_time':previous.get('use_mount_time',True)}
    write_settings(value)
    return value

def write_settings(value):
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value, indent=2), encoding="utf-8");temporary.replace(path)

def boot_id():
    try: return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    except OSError: return 'process-'+str(os.getpid())

def anchor_valid(anchor):
    try:
        delta=time.monotonic()-float(anchor['monotonic'])
        return anchor['boot_id']==boot_id() and 0<=delta<48*3600
    except (KeyError,TypeError,ValueError): return False

def utc_now(settings=None):
    settings=load_settings() if settings is None else settings
    anchor=settings.get('clock_anchor')
    if anchor and anchor_valid(anchor):
        return datetime.fromisoformat(anchor['utc'])+timedelta(seconds=time.monotonic()-float(anchor['monotonic']))
    return datetime.now(timezone.utc)

def import_mount_time(sample):
    """Anchor to the monotonic clock shared by Linux processes, not a bad RTC."""
    settings=load_settings()
    if settings.get('use_mount_time',True) is False: return settings
    utc=datetime.fromisoformat(sample['UTC']);lat=float(sample['LAT']);lon=float(sample['LON']);tick=float(sample['MONOTONIC'])
    if utc.tzinfo is None or not 2023<=utc.year<=2099 or not -90<=lat<=90 or not -180<=lon<=180 or not all(math.isfinite(x) for x in (lat,lon,tick)):
        raise ValueError('Hora/ubicación OAT inválidas.')
    if not 0<=time.monotonic()-tick<120: raise ValueError('La lectura OAT ya caducó; vuelve a leer hora/ubicación.')
    # An uninitialized site must not silently become a valid GPS fix.
    if lat==0 and lon==0: raise ValueError('OAT informa 0°, 0°: comprueba la ubicación/GPS en el LCD antes de usarla.')
    settings.update(latitude=lat,longitude=lon,clock_confirmed=True,clock_source='Hora/ubicación leídas de OAT',
                    clock_anchor={'utc':utc.astimezone(timezone.utc).isoformat(),'monotonic':tick,'boot_id':boot_id()},
                    oat_lst_hours=sample.get('LST_HOURS'),oat_ha_hours=sample.get('OAT_HA_HOURS'))
    write_settings(settings);return settings


def clock_snapshot(settings, ra_hours=None, when=None):
    utc = when or utc_now(settings)
    if utc.tzinfo is None:
        raise ValueError("El instante debe llevar zona UTC explícita.")
    utc = utc.astimezone(timezone.utc)
    local = utc.astimezone(ZoneInfo(settings.get("timezone", DEFAULT_ZONE)))
    result = {"utc": utc.isoformat(timespec="seconds"), "local": local.isoformat(timespec="seconds"),
              "timezone": settings.get("timezone", DEFAULT_ZONE), "source": settings.get('clock_source','reloj del ordenador, no GPS') if anchor_valid(settings.get('clock_anchor',{})) else 'reloj del ordenador, no GPS',
              "sidereal_hours": None, "ha_hours": None}
    longitude = settings.get("longitude")
    if longitude is not None and settings.get("clock_confirmed"):
        if not math.isfinite(longitude) or not -180 <= longitude <= 180:
            raise ValueError("Longitud inválida.")
        try:
            from astropy.time import Time
            from astropy.utils import iers
            import astropy.units as u
            from .earthtime import configure_iers
            configure_iers()
            sidereal = float(Time(utc).sidereal_time("apparent", longitude=longitude*u.deg).hour)
            result["sidereal_hours"] = sidereal
            if ra_hours is not None:
                if not math.isfinite(ra_hours) or not 0 <= ra_hours < 24:
                    raise ValueError("AR de fecha inválida.")
                result["ha_hours"] = (sidereal-ra_hours+12) % 24-12
        except ImportError:
            result["sidereal_note"] = "Falta Astropy. No se inventa una hora sidérea."
    return result
