"""Use the image's bundled IERS orientation table without network at runtime."""
from pathlib import Path

_configured=False


def configure_iers():
    global _configured
    from astropy.utils import iers
    iers.conf.auto_download=False
    leap_seconds=Path('/usr/share/zoneinfo/leap-seconds.list')
    if leap_seconds.exists():
        iers.conf.system_leap_second_file=str(leap_seconds)
    if not _configured:
        path=Path('/usr/share/astroall/iers/finals2000A.all')
        if path.exists():
            iers.earth_orientation_table.set(iers.IERS_A.open(str(path)))
        _configured=True
