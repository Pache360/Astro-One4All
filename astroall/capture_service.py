"""Camera USB lives in a non-daemon process, with a Bulb close deadline.

If the GUI exits unexpectedly, an already opened Bulb still reaches its own
deadline and finally sends ReleaseFull. No process is killed mid exposure.
"""
import multiprocessing as mp
from pathlib import Path
import time

def require_persistence():
    cmdline=Path('/proc/cmdline')
    if cmdline.exists() and 'boot=live' in cmdline.read_text():
        if '/run/live/persistence/' not in Path('/proc/mounts').read_text(): raise RuntimeError('Activa la persistencia de la USB antes de capturar; así los JPG no se acumulan en RAM.')

def _worker(connection,stop,cache_dir,exposure,iso,force_bulb=False):
    import signal
    import os
    import locale
    # gphoto widgets are translated using gettext. Use the driver's documented
    # English protocol labels in this isolated worker; our UI stays in Spanish.
    os.environ.update(LC_ALL='C',LANGUAGE='C')
    locale.setlocale(locale.LC_ALL,'C')
    from .camera import open_camera
    from .storage import JpegCache
    from .camera_diagnostic import CaptureReport
    report=CaptureReport(exposure_seconds=exposure,iso=iso,force_bulb=force_bulb)
    for name in ('SIGTERM','SIGINT'):
        if hasattr(signal,name): signal.signal(getattr(signal,name),lambda *_:stop.set())
    try:
        with open_camera(report) as camera: result=camera.capture_jpeg(JpegCache(cache_dir),exposure=exposure,iso=iso,stop=stop,force_bulb=force_bulb)
        connection.send(('result',result))
    except Exception as exc:
        if report.data.get('stage')!='error': report.failed(exc)
        phase=report.data.get('failed_stage','connecting_usb')
        try: connection.send(('error',f'{exc}\nFase: {phase}. El diagnóstico conserva los detalles.'))
        except (BrokenPipeError,EOFError,OSError): pass
    finally: connection.close()

def capture_one(cache_dir,exposure=None,iso=None,stop=None,force_bulb=False):
    require_persistence()
    context=mp.get_context('spawn');receive,send=context.Pipe(duplex=False);cancel=context.Event()
    process=context.Process(target=_worker,args=(send,cancel,str(cache_dir),exposure,iso,force_bulb),daemon=False)
    process.start();send.close();deadline=time.monotonic()+2*float(exposure or 30)+180
    try:
        while time.monotonic()<deadline:
            if stop and stop.is_set(): cancel.set()
            if receive.poll(.15):
                try: kind,result=receive.recv()
                except EOFError: raise RuntimeError('La tarea de cámara terminó sin confirmación. Revisa el diagnóstico y la SD antes de repetir.') from None
                process.join(5)
                if kind=='error': raise RuntimeError(result)
                return result
            if not process.is_alive(): raise RuntimeError('La captura terminó sin confirmación. Revisa la SD antes de repetir.')
        cancel.set()
        raise RuntimeError('La cámara no respondió a tiempo. La tarea de cierre sigue activa; revisa el obturador y la SD antes de continuar.')
    finally:
        receive.close()
        # Never terminate(): a USB call could still be holding the shutter open.
        if not process.is_alive(): process.join()
