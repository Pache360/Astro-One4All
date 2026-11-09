"""Read-only readiness report; does not connect to or move the mount."""
import importlib.util
import os
from pathlib import Path
import platform
import shutil
import subprocess


def run_optional(command):
    if not shutil.which(command[0]):
        return None
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=15,
                                env=dict(os.environ, LC_ALL="C"), check=False)
        return (result.stdout + result.stderr).strip()[:150000]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return str(exc)


def report():
    from .awake import status as power_status
    from .guide_camera import video_devices
    from .solve import solver_status
    memory = {}
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text().splitlines():
            key, value = line.split(":", 1)
            if key in ("MemTotal", "MemAvailable", "SwapTotal"):
                memory[key + "_MiB"] = int(value.strip().split()[0]) // 1024
    models = run_optional(["gphoto2", "--list-cameras"]) or ""
    cmdline = Path("/proc/cmdline").read_text() if Path("/proc/cmdline").exists() else ""
    mounts = Path("/proc/mounts").read_text() if Path("/proc/mounts").exists() else ""
    executables = ("indi_astroall_oat", "indiserver", "indi_lx200_OpenAstroTech", "indi_simulator_telescope",
                   "indi_canon_ccd", "solve-field", "phd2", "gphoto2")
    warnings = []
    if platform.system() != "Linux":
        warnings.append("Este equipo permite probar la lógica; el sistema dedicado requiere Linux.")
    if '"Canon EOS R50"' not in models:
        warnings.append("La biblioteca utilizada por gphoto2 no anuncia la R50 exacta. Verifica libgphoto2 >= 2.5.32.")
    if "boot=live" in cmdline and "/run/live/persistence/" not in mounts:
        warnings.append("No se detectó persistencia Live: no inicies una sesión de fotos todavía.")
    if "toram" in cmdline:
        warnings.append("Arranque toram detectado: copia el sistema a RAM; evita esa opción con 2 GB.")
    if memory.get("MemAvailable_MiB", 2048) < 700:
        warnings.append("Hay menos de 700 MiB disponibles. Cierra programas antes de resolver imágenes.")
    return {"platform": platform.platform(), "memory": memory,'power':power_status(),
            "tools": {name: shutil.which(name) for name in executables},
            "python_gphoto2": importlib.util.find_spec("gphoto2") is not None,
            "gphoto_version": run_optional(["gphoto2", "--version"]),
            "r50_in_camera_list": '"Canon EOS R50"' in models,
            "serial_ports": sorted(str(p) for p in Path("/dev/serial/by-id").glob("*")),
            "guide_video_devices": sorted(str(p) for p in Path("/dev").glob("video*")),
            "guide_cameras":video_devices() if platform.system()=='Linux' else [],
            "plate_solving":solver_status(),
            "warnings": warnings,
            "hardware_validated": False}
