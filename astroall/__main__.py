"""Run with python3 -m astroall. Real hardware is always opt-in by command."""
import argparse
from dataclasses import asdict
import json
import math
from pathlib import Path
import sys
import time

from .camera import open_camera
from .doctor import report
from .solve import Position, drift_report, solve_jpeg
from .storage import JpegCache


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2), flush=True)


def capture_sequence(count, delay, cache_dir, emit_result=emit, stop=None,exposure=None,iso=None):
    if not 1 <= count <= 10000 or not math.isfinite(delay) or not 0 <= delay <= 3600:
        raise ValueError("Usa entre 1 y 10000 fotos y una pausa de 0 a 3600 segundos.")
    # A nonpersistent Live session stores writes in RAM. Refuse that storage mode.
    cmdline = Path("/proc/cmdline")
    if cmdline.exists() and "boot=live" in cmdline.read_text():
        if "/run/live/persistence/" not in Path("/proc/mounts").read_text():
            raise RuntimeError("Configura la persistencia USB antes de capturar en modo Live.")
    from .capture_service import capture_one
    for i in range(count):
        if stop and stop.is_set(): break
        result=capture_one(cache_dir,exposure,iso,stop)
        if result.get('interrupted'): break
        emit_result(dict(result,shot=i+1,total=count))
        if i+1<count:
            if stop:
                if stop.wait(delay): break
            else: time.sleep(delay)


def main(argv=None):
    from . import __version__
    parser = argparse.ArgumentParser(description="Astro One4All · prueba Live "+__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Diagnóstico sin mover ni disparar")
    sub.add_parser("camera-info", help="Consultar ajustes; desconecta antes la cámara en Ekos")
    sub.add_parser("panel", help="Panel de escritorio en español")
    sub.add_parser("demo", help="Simular deriva sin dispositivos")
    oat = sub.add_parser("oat-info", help="Consultar :GVP# y :GVN# con el OAT en reposo e INDI desconectado")
    oat.add_argument("--port", required=True)
    oat.add_argument("--baud", type=int, default=19200)
    capture = sub.add_parser("capture", help="Disparar realmente a SD y descargar solo JPG")
    capture.add_argument("--count", type=int, default=1)
    capture.add_argument("--delay", type=float, default=3)
    capture.add_argument('--exposure',type=float,help='Segundos; >30 usa Bulb compatible')
    capture.add_argument('--iso',help='Valor de ISO anunciado por la cámara')
    capture.add_argument('--bulb',action='store_true',help='Probar Bulb incluso con exposiciones cortas (requiere --exposure)')
    capture.add_argument("--cache", default=str(Path.home() / ".cache/astroall/jpg"))
    solve = sub.add_parser("solve", help="Resolver un JPG con índices locales")
    solve.add_argument("image")
    solve.add_argument("--width-deg", type=float, required=True)
    solve.add_argument("--index-dir", action="append", required=True)
    drift = sub.add_parser("drift", help="Comparar dos centros; no envía movimientos")
    drift.add_argument("--reference", type=float, nargs=2, metavar=("RA_DEG", "DEC_DEG"), required=True)
    drift.add_argument("--current", type=float, nargs=2, metavar=("RA_DEG", "DEC_DEG"), required=True)
    drift.add_argument("--threshold", type=float, default=60)
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            emit(report())
        elif args.command == "camera-info":
            with open_camera() as camera:
                emit(camera.inspect())
        elif args.command == "capture":
            if args.bulb:
                from .capture_service import capture_one
                if args.count!=1 or args.exposure is None: raise ValueError('La prueba --bulb requiere --count 1 y --exposure en segundos.')
                emit(capture_one(args.cache,args.exposure,args.iso,force_bulb=True))
            else: capture_sequence(args.count,args.delay,args.cache,exposure=args.exposure,iso=args.iso)
        elif args.command == "oat-info":
            from .oat import probe
            emit(probe(args.port, args.baud))
        elif args.command == "solve":
            emit(asdict(solve_jpeg(args.image, args.width_deg, args.index_dir)))
        elif args.command == "drift":
            emit(drift_report(Position(*args.reference), Position(*args.current), args.threshold))
        elif args.command == "demo":
            emit({"mode": "SIMULACIÓN · sin cámara ni motores",
                  "example": drift_report(Position(359.99, 20), Position(.03, 20)),
                  "raw_destination": "SD de cámara (diseño; pendiente de prueba real)",
                  "jpeg_cache_MiB": 64, "automatic_recenter_implemented": True,"recenter_hardware_validated":False})
        elif args.command == "panel":
            from .panel import run
            run()
    except (Exception, KeyboardInterrupt) as exc:
        print(f"Detenido: {exc or 'interrupción solicitada'}. No se reintenta el disparo.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
