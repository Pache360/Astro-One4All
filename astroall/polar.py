"""Experimental three-point polar axis estimate with manual RA rotation.

The geometry uses local horizon directions at EACH exposure's time, so Earth's
rotation between exposures isn't mistaken for a change in the mount axis.
"""
import math
from datetime import datetime, timezone


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def unit(vector):
    norm = math.sqrt(dot(vector, vector))
    if norm < 1e-7:
        raise ValueError("Geometría degenerada: separa más los tres puntos girando solamente AR.")
    return tuple(v / norm for v in vector)


def horizon_vector(az_deg, alt_deg):
    az, alt = math.radians(az_deg), math.radians(alt_deg)
    return math.cos(alt)*math.cos(az), math.cos(alt)*math.sin(az), math.sin(alt)


def estimate_from_vectors(vectors, latitude):
    if len(vectors) != 3 or not math.isfinite(latitude) or not -90 <= latitude <= 90:
        raise ValueError("Se requieren tres puntos y una latitud válida.")
    vectors = [unit(v) for v in vectors]
    for i in range(3):
        for j in range(i):
            angle = math.degrees(math.acos(max(-1, min(1, dot(vectors[i], vectors[j])))))
            if angle < 5:
                raise ValueError("Los puntos deben separarse al menos 5°; no cambies DEC, trípode ni lente.")
    a = tuple(x-y for x, y in zip(vectors[1], vectors[0]))
    b = tuple(x-y for x, y in zip(vectors[2], vectors[0]))
    normal = unit((a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]))
    target_az = 0 if latitude >= 0 else 180
    target_alt = abs(latitude)
    target = horizon_vector(target_az, target_alt)
    if dot(normal, target) < 0:
        normal = tuple(-x for x in normal)
    return axis_report(normal, latitude)


def axis_report(normal, latitude):
    """Physical base corrections in a north/east/up horizon frame."""
    if not math.isfinite(latitude) or not -90 <= latitude <= 90:
        raise ValueError('Latitud inválida.')
    normal=unit(normal)
    target_az=0 if latitude >= 0 else 180
    target_alt=abs(latitude)
    target=horizon_vector(target_az,target_alt)
    az = math.degrees(math.atan2(normal[1], normal[0])) % 360
    alt = math.degrees(math.asin(max(-1, min(1, normal[2]))))
    error = math.degrees(math.acos(max(-1, min(1, dot(normal, target)))))
    return {"estimated_axis_az_deg": az, "estimated_axis_alt_deg": alt,
            "target_axis_az_deg": target_az,
            "polar_error_arcmin": error * 60,
            "alt_adjustment_deg": target_alt-alt,
            "az_adjustment_deg": (target_az-az+180) % 360-180,
            "experimental": True,
            "instruction": "Ajusta físicamente altitud/azimut de la base, después vuelve a medir. No hay movimiento automático."}


def estimate_polar(samples, latitude, longitude, elevation=0):
    if len(samples) != 3 or not math.isfinite(latitude) or not -90 <= latitude <= 90:
        raise ValueError("Se requieren tres puntos y una latitud válida.")
    if not math.isfinite(longitude) or not -180 <= longitude <= 180:
        raise ValueError("Longitud debe estar entre -180 y 180°; oeste negativo.")
    try:
        import astropy.units as u
        from astropy.coordinates import SkyCoord, EarthLocation, AltAz
        from astropy.time import Time
        from astropy.utils import iers
    except ImportError as exc:
        raise RuntimeError("Falta python3-astropy para transformar cada foto al horizonte local.") from exc
    from .earthtime import configure_iers
    configure_iers()
    location = EarthLocation.from_geodetic(longitude*u.deg, latitude*u.deg, elevation*u.m)
    vectors = []
    for sample in samples:
        instant=datetime.fromisoformat(str(sample['utc']).replace('Z','+00:00'))
        if instant.tzinfo is None:
            raise ValueError('La hora de cada foto debe incluir su zona UTC explícita.')
        sky = SkyCoord(ra=sample["ra_deg"]*u.deg, dec=sample["dec_deg"]*u.deg, frame="icrs")
        local = sky.transform_to(AltAz(obstime=Time(instant.astimezone(timezone.utc)), location=location, pressure=0*u.hPa))
        vectors.append(horizon_vector(local.az.deg, local.alt.deg))
    return estimate_from_vectors(vectors, latitude)
