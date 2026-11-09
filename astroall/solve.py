"""Serial, time-limited offline plate solving and spherical drift measurement."""
from dataclasses import dataclass, asdict
from pathlib import Path
import math
import os
import re
import shutil
import subprocess
import tempfile


@dataclass(frozen=True)
class Position:
    ra_deg: float
    dec_deg: float

    def __post_init__(self):
        if not (math.isfinite(self.ra_deg) and 0 <= self.ra_deg < 360
                and math.isfinite(self.dec_deg) and -90 <= self.dec_deg <= 90):
            raise ValueError("Coordenadas inválidas: AR en grados [0,360), DEC [-90,90].")


@dataclass(frozen=True)
class SolvedFrame:
    """Small WCS metadata only; image pixels remain in the disk JPEG cache."""
    header: str
    width: int
    height: int

    def wcs(self):
        from astropy.io.fits import Header
        from astropy.wcs import WCS
        return WCS(Header.fromstring(self.header, sep='\n')).celestial

    def sky(self, x, y):
        from astropy.wcs.utils import pixel_to_skycoord
        return pixel_to_skycoord(x, y, self.wcs(), origin=0, mode='all').icrs

    @classmethod
    def read(cls, path, image):
        from astropy.io.fits import Header
        from astropy.wcs import WCS
        from PIL import Image
        if not path.is_file() or path.stat().st_size > 256*1024:
            raise RuntimeError('El solver no entregó una orientación WCS válida.')
        with Image.open(image) as source:
            width,height=source.size
        if not 0 < width*height <= 30_000_000:
            raise ValueError('El JPG supera 30 megapíxeles.')
        header=Header.fromfile(path)
        wcs=WCS(header).celestial
        if not wcs.has_celestial or wcs.pixel_n_dim != 2:
            raise RuntimeError('El solver no entregó una orientación celeste de dos ejes.')
        frame=cls(wcs.to_header(relax=True).tostring(sep='\n',endcard=False,padding=False),width,height)
        center=frame.sky((width-1)/2,(height-1)/2)
        Position(float(center.ra.deg)%360,float(center.dec.deg))
        return frame


def separation_arcsec(a, b):
    ra1, ra2, d1, d2 = map(math.radians, (a.ra_deg, b.ra_deg, a.dec_deg, b.dec_deg))
    h = math.sin((d2-d1)/2)**2 + math.cos(d1)*math.cos(d2)*math.sin((ra2-ra1)/2)**2
    return math.degrees(2 * math.asin(math.sqrt(min(1, max(0, h))))) * 3600


def drift_report(reference, current, threshold=60):
    if not math.isfinite(threshold) or threshold <= 0:
        raise ValueError("El umbral debe ser positivo.")
    distance = separation_arcsec(reference, current)
    return {"reference": asdict(reference), "current": asdict(current),
            "error_arcsec": round(distance, 3), "threshold_arcsec": threshold,
            "recenter_suggested": distance > threshold,
            "mount_command_sent": False,
            "note": "Medición entre fotos; no es autoguiado durante la exposición."}


def indexes_available(index_dirs):
    return any(next(Path(d).expanduser().glob('index-*.fits'),None) is not None for d in index_dirs)

def solver_status(index_dirs=None):
    dirs=index_dirs or [Path.home()/'astroall-data/indexes','/usr/share/astrometry']
    files=[p for directory in dirs for p in Path(directory).expanduser().glob('index-*.fits')]
    engine=shutil.which('solve-field');ready=bool(engine and files)
    return {'ready':ready,'engine':engine,'index_count':len(files),
            'label':f'Plate solving offline listo · {len(files)} índices' if ready else 'Plate solving · falta motor o índices de la Live'}

def solve_jpeg(image, width_deg, index_dirs, work_root=None):
    return _solve_jpeg(image, width_deg, index_dirs, work_root)


def solve_frame(image, width_deg, index_dirs, work_root=None):
    """Polar alignment needs orientation, parity and distortion as well as centre.

    A missing scale hint is permitted for a guide camera with unknown optics.
    The same CPU, wall time and memory limits still apply to a blind solve.
    """
    return _solve_jpeg(image, width_deg, index_dirs, work_root, full=True)


def _solve_jpeg(image, width_deg, index_dirs, work_root=None, full=False):
    image = Path(image).resolve()
    if image.suffix.lower() not in (".jpg", ".jpeg") or not image.is_file():
        raise ValueError("Selecciona un JPG existente.")
    if image.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("El JPG excede 16 MiB.")
    if width_deg is None and not full:
        raise ValueError('Indica el ancho del campo en grados.')
    if width_deg is not None and (not math.isfinite(width_deg) or not 0.01 <= width_deg <= 170):
        raise ValueError("Indica el ancho del campo en grados, entre 0.01 y 170.")
    if not shutil.which("solve-field"):
        raise RuntimeError("No está instalado astrometry.net (solve-field).")
    dirs = [Path(d).expanduser().resolve() for d in index_dirs]
    if any(any(c.isspace() for c in str(d)) for d in dirs):
        raise ValueError("Las rutas de índices astrométricos no deben contener espacios.")
    if not any(list(d.glob("index-*.fits")) for d in dirs):
        raise RuntimeError("Faltan índices astrométricos para resolver sin Internet.")
    # Work files live on the persistent USB, not /tmp or a growing RAM disk.
    root = Path(work_root or Path.home() / ".cache/astroall/solve")
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as temp:
        temp = Path(temp)
        config = temp / "astrometry.cfg"
        config.write_text("\n".join(["add_path " + str(d) for d in dirs] + ["autoindex"]), encoding="utf-8")
        solved = temp / "field.solved"
        cmd = ["solve-field", str(image), "--config", str(config), "--dir", str(temp),
               "--out", "field", "--solved", str(solved), "--no-plots", "--overwrite",
               "--cpulimit", "45", "--downsample", "2",
               "--new-fits", "none"]
        if width_deg is not None:
            cmd += ['--scale-units','degwidth','--scale-low',str(width_deg*.8),'--scale-high',str(width_deg*1.2)]
        if os.name == "posix" and shutil.which("prlimit"):
            cmd = ["prlimit", "--as=1073741824", "--"] + cmd
        env = dict(os.environ, LC_ALL="C", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
        # A disk log avoids retaining the solver's complete output in RAM.
        log_path = temp / "solver.log"
        try:
            with log_path.open("w", encoding="utf-8") as log:
                result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
                                        timeout=90, env=env, check=False)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("El solver agotó 90 s. Revisa campo, enfoque e índices.") from exc
        with log_path.open(encoding="utf-8", errors="replace") as log:
            center = None
            for line in log:
                match = re.search(r"Field center: \(RA,Dec\) = \(([\d.eE+-]+),\s*([\d.eE+-]+)\) deg", line)
                if match:
                    center = Position(float(match[1]) % 360, float(match[2]))
        if result.returncode or not solved.exists() or solved.read_bytes() != b"\x01" or center is None:
            raise RuntimeError("No se resolvió el campo. No se enviará ninguna corrección.")
        return SolvedFrame.read(temp/'field.wcs',image) if full else center
