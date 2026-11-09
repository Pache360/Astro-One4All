"""Offline visibility and explicit ICRS to apparent-of-date transformations."""
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
import math
from zoneinfo import ZoneInfo
from .solve import Position

@dataclass(frozen=True)
class Site:
    latitude:float
    longitude:float
    elevation:float=0
    zone:str='America/Mexico_City'

    def __post_init__(self):
        if not (math.isfinite(self.latitude) and -90<=self.latitude<=90 and math.isfinite(self.longitude) and -180<=self.longitude<=180 and math.isfinite(self.elevation) and -500<=self.elevation<=10000):
            raise ValueError('Ubicación inválida. Longitud oeste es negativa.')
        ZoneInfo(self.zone)

    @classmethod
    def from_settings(cls,settings,require_clock=True):
        if require_clock and not settings.get('clock_confirmed'):
            raise ValueError('Comprueba y confirma el reloj UTC en Ubicación y tiempo antes de planificar o mover la montura.')
        if settings.get('latitude') is None or settings.get('longitude') is None:
            raise ValueError('Configura tu latitud y longitud reales en Ubicación y tiempo.')
        return cls(float(settings['latitude']),float(settings['longitude']),float(settings.get('elevation',0)),settings.get('timezone','America/Mexico_City'))

def utc_instant(value=None):
    from .timekeeping import utc_now
    value=value or utc_now()
    if isinstance(value,str): value=datetime.fromisoformat(value.replace('Z','+00:00'))
    if value.tzinfo is None: raise ValueError('El instante debe incluir su zona UTC.')
    return value.astimezone(timezone.utc)

def runtime(site):
    import astropy.units as u
    from astropy.coordinates import EarthLocation
    from .earthtime import configure_iers
    configure_iers()
    return u,EarthLocation.from_geodetic(site.longitude*u.deg,site.latitude*u.deg,site.elevation*u.m)

def eod_position(position,site,when=None,inverse=False):
    u,location=runtime(site)
    from astropy.coordinates import SkyCoord,TETE
    from astropy.time import Time
    frame=TETE(obstime=Time(utc_instant(when)),location=location)
    sky=SkyCoord(ra=position.ra_deg*u.deg,dec=position.dec_deg*u.deg,frame=frame if inverse else 'icrs')
    converted=sky.icrs if inverse else sky.transform_to(frame)
    return Position(float(converted.ra.deg)%360,float(converted.dec.deg))

def visibility(position,site,when=None):
    u,location=runtime(site)
    from astropy.coordinates import SkyCoord,AltAz,get_body
    from astropy.time import Time
    instant=utc_instant(when);t=Time(instant)
    horizon=AltAz(obstime=t,location=location,pressure=0*u.hPa)
    sky=SkyCoord(ra=position.ra_deg*u.deg,dec=position.dec_deg*u.deg,frame='icrs')
    local=sky.transform_to(horizon)
    moon=get_body('moon',t,location).transform_to(horizon)
    sun=get_body('sun',t,location).transform_to(horizon)
    apparent=eod_position(position,site,instant)
    lst=float(t.sidereal_time('apparent',longitude=site.longitude*u.deg).hour)
    return {'utc':instant.isoformat(),'local':instant.astimezone(ZoneInfo(site.zone)).isoformat(),
            'alt_deg':float(local.alt.deg),'az_deg':float(local.az.deg),'visible':bool(local.alt.deg>=0),'visibility_label':visibility_label(float(local.alt.deg)),
            'moon_separation_deg':float(local.separation(moon).deg),'moon_alt_deg':float(moon.alt.deg),
            'moon_illumination_approx':float((1-math.cos(moon.separation(sun).rad))/2),
            'sun_alt_deg':float(sun.alt.deg),'astronomical_darkness':bool(sun.alt.deg<-18),
            'sidereal_hours':lst,'ha_hours':(lst-apparent.ra_deg/15+12)%24-12,
            'ra_hours_eod':apparent.ra_deg/15,'dec_deg_eod':apparent.dec_deg,'refraction':False}

def visibility_label(altitude):
    if not math.isfinite(altitude): raise ValueError('Altura inválida.')
    return 'No visible ahora' if altitude<0 else 'Muy cercano al horizonte' if altitude<20 else 'Visible'

def atlas_visibility(targets,site,when=None):
    """One vector transform for the bounded catalogue page, offline."""
    if not targets: return []
    u,location=runtime(site)
    from astropy.coordinates import SkyCoord,AltAz
    from astropy.time import Time
    sky=SkyCoord(ra=[t.ra_deg for t in targets]*u.deg,dec=[t.dec_deg for t in targets]*u.deg,frame='icrs')
    altitudes=sky.transform_to(AltAz(obstime=Time(utc_instant(when)),location=location,pressure=0*u.hPa)).alt.deg
    return [{'alt_deg':float(alt),'label':visibility_label(float(alt))} for alt in altitudes]

def night_tracks(targets,site,day=None,min_alt=20,min_moon_sep=20,step_minutes=30):
    if not 0<=min_alt<=85 or not 0<=min_moon_sep<=180 or not 5<=step_minutes<=60:
        raise ValueError('Límites de planificación inválidos.')
    u,location=runtime(site)
    from astropy.coordinates import SkyCoord,AltAz,get_body
    from astropy.time import Time
    local_now=utc_instant().astimezone(ZoneInfo(site.zone))
    date=(local_now-timedelta(hours=12)).date() if day is None else datetime.fromisoformat(str(day)).date()
    start=datetime(date.year,date.month,date.day,12,tzinfo=ZoneInfo(site.zone)).astimezone(timezone.utc)
    end=(datetime(date.year,date.month,date.day,12,tzinfo=ZoneInfo(site.zone))+timedelta(days=1)).astimezone(timezone.utc)
    times=[];instant=start
    while instant<=end:
        times.append(instant);instant+=timedelta(minutes=step_minutes)
    t=Time(times);frame=AltAz(obstime=t,location=location,pressure=0*u.hPa)
    sun=get_body('sun',t,location).transform_to(frame)
    moon=get_body('moon',t,location).transform_to(frame)
    tracks=[]
    for target in list(targets)[:300]:
        local=SkyCoord(ra=target.ra_deg*u.deg,dec=target.dec_deg*u.deg,frame='icrs').transform_to(frame)
        alt=local.alt.deg;separation=local.separation(moon).deg
        usable=[bool(alt[i]>=min_alt and sun.alt.deg[i]<-18 and (moon.alt.deg[i]<0 or separation[i]>=min_moon_sep)) for i in range(len(times))]
        # Only count intervals whose two endpoints meet the requested limits.
        minutes=sum(step_minutes for a,b in zip(usable,usable[1:]) if a and b)
        tracks.append({'identifier':target.identifier,'label':target.label,'max_alt_deg':float(max(alt)),
                       'usable_minutes':minutes,'altitudes':[float(x) for x in alt],'usable':usable})
    return {'timezone':site.zone,'times_utc':[x.isoformat() for x in times],
            'times_local':[x.astimezone(ZoneInfo(site.zone)).isoformat() for x in times],
            'sun_altitudes':[float(x) for x in sun.alt.deg],'moon_altitudes':[float(x) for x in moon.alt.deg],
            'tracks':tracks,'sampling_minutes':step_minutes,'note':'Ventanas aproximadas; se comprueba la altura de nuevo antes de mover o exponer.'}
