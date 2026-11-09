"""Experimental SD-first Canon adapter. No delete/download-RAW operation exists."""
from contextlib import contextmanager
from fractions import Fraction
from pathlib import PurePosixPath
from datetime import datetime, timezone, timedelta
import time
import re


class CameraError(RuntimeError):
    pass


def shutter_seconds(value):
    try:
        seconds = float(Fraction(str(value).strip().rstrip('"s')))
    except (ValueError, ZeroDivisionError):
        raise CameraError("No se reconoce esa velocidad fija. Elige una exposición en segundos o la prueba Bulb.")
    if not 0 < seconds <= 30:
        raise CameraError("Esta versión experimental admite exposiciones fijas de hasta 30 s.")
    return seconds


def require_raw_jpeg(value):
    text = str(value).lower()
    # libgphoto2 2.5.32+ Canon labels are abbreviated: e.g. "RAW + M".
    parts = [part.strip() for part in text.split('+')]
    canon_jpeg = {'l','m','s','cl','cm','cs','s1','s2','s3','cs1','cs2','cs3','m1','m2','cm1','cm2'}
    explicit = 'raw' in text and ('jpeg' in text or 'jpg' in text)
    abbreviated = len(parts) == 2 and parts[0] in {'raw','craw','mraw','sraw'} and parts[1] in canon_jpeg
    if not (explicit or abbreviated):
        raise CameraError("Selecciona RAW + JPG Med en la cámara. No se reconoce ese formato combinado.")


class CanonSD:
    raw_suffixes=('.cr3','.cr2')
    def __init__(self, camera, gp, report=None):
        self.camera, self.gp, self.report = camera, gp, report
        self.context=None

    def stage(self, name, **values):
        if self.report: self.report.update(name, **values)

    def widget(self, name):
        try:
            if hasattr(self.camera, 'get_single_config'):
                return self.camera.get_single_config(name)
            return self.camera.get_config().get_child_by_name(name)
        except Exception as exc:
            raise CameraError(f"La cámara no expone el ajuste {name}: {exc}") from exc

    def inspect(self):
        result = {"model": self.camera.get_abilities().model}
        result['application_version'] = __import__('astroall').__version__
        try: result['libgphoto2'] = list(self.gp.gp_library_version(0))
        except (AttributeError, TypeError): pass
        for key in ("capturetarget", "imageformat", "shutterspeed", "iso", "autoexposuremode", "drivemode", "eosremoterelease"):
            try:
                widget = self.widget(key)
                result[key] = {"value": str(widget.get_value())}
                try: result[key]['choices'] = [str(c) for c in widget.get_choices()]
                except Exception: pass # Some status widgets are text, not menus.
            except Exception as exc:
                result[key] = {"error": str(exc)}
        return result

    def write_widget(self, name, value):
        try:
            self.operation('read_configuration', name, value)
            if hasattr(self.camera,'set_single_config') and hasattr(self.camera,'get_single_config'):
                widget=self.widget(name);widget.set_value(value)
                self.operation('write_configuration',name,value)
                self.camera.set_single_config(name,widget)
            else:
                config=self.camera.get_config();config.get_child_by_name(name).set_value(value)
                self.operation('write_configuration',name,value)
                self.camera.set_config(config)
        except Exception as exc:
            raise CameraError(f'No se pudo aplicar {name}={value}: {exc}. No se disparó.') from exc

    def operation(self, operation, name, value):
        if self.report:
            self.report.update(self.report.data.get('stage','configuring_exposure'),
                               operation=operation, setting=name, requested_value=str(value))

    def set_named(self,name,value):
        widget=self.widget(name)
        choices=[str(c) for c in widget.get_choices()]
        if str(value) not in choices: raise CameraError(f'{name}: ajuste no disponible entre {choices}.')
        if str(widget.get_value())==str(value): return
        self.write_widget(name, str(value))
        self.operation('confirm_configuration',name,value)
        if str(self.widget(name).get_value())!=str(value): raise CameraError(f'La cámara no confirmó {name}. No se disparó.')

    def configure_exposure(self,exposure=None,iso=None,force_bulb=False):
        if iso not in (None,'','Cámara'): self.set_named('iso',str(iso))
        if exposure is None and not force_bulb: return shutter_seconds(self.widget('shutterspeed').get_value()),False
        import math
        if exposure is None: raise CameraError('Indica la duración de Bulb en segundos.')
        duration=float(exposure)
        if not math.isfinite(duration) or not .001<=duration<=3600: raise CameraError('Exposición entre 0.001 y 3600 segundos.')
        # Python-gphoto2's lazy choice iterator borrows the native widget.
        # Keep its owner alive until iteration has finished.
        shutter_widget=self.widget('shutterspeed')
        choices=[str(c) for c in shutter_widget.get_choices()]
        if duration>30 or force_bulb:
            bulb=next((c for c in choices if c.strip().lower()=='bulb'),None)
            if bulb is None: raise CameraError('La cámara no anuncia Bulb mediante este método USB. No se disparó.')
            self.set_named('shutterspeed',bulb)
            self.release_pair() # Verify named command choices BEFORE opening the shutter.
            return duration,True
        matches=[]
        for choice in choices:
            try: seconds=shutter_seconds(choice)
            except CameraError: continue
            if abs(seconds-duration)<=max(.00001,duration*.015): matches.append(choice)
        if not matches: raise CameraError(f'La cámara no ofrece exposición fija de {duration:g} s. Consulta sus ajustes disponibles.')
        self.set_named('shutterspeed',matches[0]);return shutter_seconds(matches[0]),False

    def release_pair(self):
        release_widget=self.widget('eosremoterelease')
        choices=[str(c) for c in release_widget.get_choices()]
        # 2.5.33 publishes "Press Full" / "Release Full" (with spaces).
        # 2.5.34+ adds "Press Full MF" and "Release". Always send the exact
        # advertised text, never invented concatenations or numeric indexes.
        normalize=lambda value: re.sub(r'[\s_-]+', '', value).casefold()
        by_name={normalize(c):c for c in choices}
        for press,release in [('pressfullmf','release'), ('pressfullmf','releasefull'),
                              ('pressfull','releasefull'), ('pressfull','release')]:
            if press in by_name and release in by_name: return by_name[press],by_name[release]
        raise CameraError(f'El controlador no anuncia un par de pulsar/soltar compatible con Bulb: {choices}. No se disparó.')

    def remote(self,value):
        self.write_widget('eosremoterelease',value)
        # This widget is an actuator: get_value() always reports None, not shutter state.

    def prepare(self,bulb=False):
        model = self.camera.get_abilities().model
        if "Canon EOS R50" != model:
            raise CameraError(f"Este perfil solo se ha diseñado para Canon EOS R50; detectada: {model}.")
        if str(self.widget("autoexposuremode").get_value()).lower() not in ("m", "manual"):
            raise CameraError("Selecciona modo M en la cámara antes de capturar.")
        require_raw_jpeg(self.widget("imageformat").get_value())
        if not bulb: shutter_seconds(self.widget("shutterspeed").get_value())
        # Never assume numeric choice 1 means SD. Require an explicit named choice.
        target = self.widget("capturetarget")
        choices = list(target.get_choices())
        card_labels={'memory card','tarjeta de memoria','sd card','tarjeta sd'}
        selected = next((c for c in choices if str(c).strip().lower() in card_labels), None)
        if selected is None:
            raise CameraError(f"No se identifica un destino SD seguro entre: {choices}")
        self.write_widget('capturetarget', selected)
        if str(self.widget("capturetarget").get_value()) != str(selected):
            raise CameraError("La cámara no confirmó la tarjeta como destino. No se disparó.")

    def capture_jpeg(self, cache, timeout=25, exposure=None, iso=None, stop=None, force_bulb=False):
        self.stage('checking_camera', camera=self.inspect())
        # Validate camera mode and storage BEFORE changing ISO or shutter speed.
        self.prepare(bulb=True)
        self.stage('configuring_exposure')
        duration,bulb=self.configure_exposure(exposure,iso,force_bulb)
        self.stage('ready', duration_seconds=duration, bulb=bulb)
        if stop and stop.is_set(): raise CameraError('Captura cancelada antes del disparo.')
        # capture() triggers a real exposure at the current camera settings, to SD.
        from .timekeeping import utc_now
        started = utc_now()
        interrupted=False
        if bulb:
            press,release=self.release_pair()
            # Reject a non-quiescent queue instead of attributing an older capture to this shot.
            for _ in range(100):
                event,_data=self.camera.wait_for_event(30)
                if event==self.gp.GP_EVENT_TIMEOUT: break
            else: raise CameraError('Eventos antiguos pendientes en la cámara; no se abrió Bulb.')
            # Prepare both actuator widgets before opening the shutter. Their
            # owners remain alive through release, without configuration reads.
            single=hasattr(self.camera,'set_single_config') and hasattr(self.camera,'get_single_config')
            if single:
                press_widget=self.widget('eosremoterelease');press_widget.set_value(press)
                release_widget=self.widget('eosremoterelease');release_widget.set_value(release)
                send_press=lambda:self.camera.set_single_config('eosremoterelease',press_widget)
                send_release=lambda:self.camera.set_single_config('eosremoterelease',release_widget)
            else:
                # Prepare complete trees for older Python bindings, too.
                press_config=self.camera.get_config()
                press_config.get_child_by_name('eosremoterelease').set_value(press)
                release_config=self.camera.get_config()
                release_config.get_child_by_name('eosremoterelease').set_value(release)
                send_press=lambda:self.camera.set_config(press_config)
                send_release=lambda:self.camera.set_config(release_config)
            captured=None;opened=False;press_time=time.monotonic();early_file=False
            try:
                self.stage('opening_bulb', press_command=press, release_command=release)
                opened=True;send_press();press_time=time.monotonic()
                self.stage('bulb_exposing')
                deadline=press_time+duration
                while time.monotonic()<deadline:
                    if stop and stop.is_set(): interrupted=True;break
                    # Poll EOS events in the same open PTP session; do not let
                    # the camera's event queue build up during long exposures.
                    event,data=self.camera.wait_for_event(max(1,int(min(.1,max(0,deadline-time.monotonic()))*1000)))
                    if event==self.gp.GP_EVENT_FILE_ADDED:
                        captured=data;early_file=True;break
            finally:
                if opened:
                    try:
                        send_release()
                        self.stage('bulb_released')
                    except Exception as exc: raise CameraError('No se confirmó la orden de cerrar Bulb. Revisa y cierra el obturador en la cámara; la secuencia se detuvo.') from exc
            duration=time.monotonic()-press_time
            if early_file: raise CameraError('La cámara terminó la foto antes de la duración Bulb solicitada. Se envió soltar y se detuvo el plan; revisa la SD y los ajustes de disparo.')
            self.stage('waiting_for_sd')
            # Long-exposure noise reduction can occupy the camera for another
            # exposure duration. Allow this wait without redriving the shutter.
            deadline=time.monotonic()+timeout+duration
            while captured is None and time.monotonic()<deadline:
                event,data=self.camera.wait_for_event(250)
                if event==self.gp.GP_EVENT_FILE_ADDED:
                    captured=data;break
            if captured is None: raise CameraError('Bulb cerrado, pero no llegó el archivo capturado; no se repitió la foto.')
        else:
            self.stage('fixed_exposing')
            captured = self.capture_fixed()
        self.stage('checking_sd_pair')
        folder, stem = captured.folder, PurePosixPath(captured.name).stem
        if not folder.startswith("/store_") or "/DCIM/" not in folder + "/":
            raise CameraError("No se confirmó una ruta de tarjeta DCIM; se detuvo sin descargar.")
        deadline = time.monotonic() + timeout
        while True:
            # Query names only, never read RAW payload. Match the exact exposure stem.
            listing = self.camera.folder_list_files(folder)
            names = [entry[0] for entry in listing]
            same = [n for n in names if PurePosixPath(n).stem == stem]
            jpeg = next((n for n in same if PurePosixPath(n).suffix.lower() in (".jpg", ".jpeg")), None)
            raw = next((n for n in same if PurePosixPath(n).suffix.lower() in self.raw_suffixes), None)
            if jpeg and raw:
                break
            if time.monotonic() >= deadline:
                raise CameraError("No se confirmó el par RAW+JPG en SD. La foto puede estar guardada; no se reintentó.")
            self.camera.wait_for_event(500)
        # Metadata check BEFORE downloading; at most one JPEG enters RAM.
        info = self.camera.file_get_info(folder, jpeg)
        size = int(info.file.size)
        cache.reserve(size)
        self.stage('downloading_jpeg', sd_folder=folder, sd_raw=raw, sd_jpeg=jpeg, downloaded_bytes=size)
        jpeg_file = self.camera.file_get(folder, jpeg, self.gp.GP_FILE_TYPE_NORMAL)
        try:
            local = cache.save(jpeg_file, size)
        finally:
            del jpeg_file
        self.stage('complete')
        return {"jpeg": str(local), "sd_folder": folder, "sd_raw": raw,
                "sd_jpeg": jpeg, "downloaded_bytes": size,
                "exposure_seconds":duration,"interrupted":interrupted,"bulb":bulb,
                "approx_mid_utc": (started + timedelta(seconds=duration/2)).isoformat(),
                "timestamp_note": "Estimado con el reloj UTC de la aplicación; latencia USB no calibrada."}


    def capture_fixed(self):
        try:
            if self.context is None:return self.camera.capture(self.gp.GP_CAPTURE_IMAGE)
            return self.camera.capture(self.gp.GP_CAPTURE_IMAGE,self.context)
        except Exception as exc:
            if getattr(exc,'code',None)==-110:
                self.stage('fixed_exposing',uncertain_photo=True,controller_error=str(exc))
                raise CameraError('La cámara informó trabajo USB en curso [-110] y no confirmó esta toma. La foto puede estar en su SD. La secuencia se detuvo sin repetir el disparo; revisa la cámara y la tarjeta antes de continuar.') from exc
            raise


@contextmanager
def open_camera(report=None):
    # No dependency import at startup: doctor and simulation work without hardware.
    try:
        import gphoto2 as gp
    except ImportError as exc:
        raise CameraError("Falta python3-gphoto2. El control real requiere Linux con libgphoto2 >= 2.5.32.") from exc
    import os
    if os.name != "posix":
        raise CameraError("El control real de la cámara está preparado para Linux.")
    import fcntl
    from pathlib import Path
    lock_dir = Path.home() / ".cache" / "astroall"
    lock_dir.mkdir(parents=True, exist_ok=True)
    with (lock_dir / "camera.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise CameraError("Otra tarea Astro One4All utiliza la cámara.") from exc
        camera = gp.Camera()
        initialized = False
        context=gp.Context();driver_messages=[];selected=None
        def driver_message(*args):
            words=[arg.decode('utf-8',errors='replace') if isinstance(arg,bytes) else arg for arg in args if isinstance(arg,(str,bytes))]
            if words:
                driver_messages.append(' '.join(words)[:1500]);del driver_messages[:-12]
                if report:report.update(report.data.get('stage','initializing_usb'),driver_messages=list(driver_messages))
        # python-gphoto2 returns native CallbackDetails owners. Losing these
        # silently unregisters callbacks, leaving only "Unspecified error".
        context_callbacks=[context.set_error_func(driver_message,None),context.set_status_func(driver_message,None)]
        try:
            if report: report.update('detecting_usb',library=list(gp.gp_library_version(0)))
            from .equipment import apply_camera_selection
            selected=apply_camera_selection(camera,gp,context=context)
            if report:report.update('initializing_usb',selected_camera=selected)
            if report and selected['port'].startswith('usb:'):
                try:
                    import subprocess
                    bus,number=selected['port'][4:].split(',');device=Path('/dev/bus/usb')/bus/number
                    owners=subprocess.run(['fuser','-v',str(device)],capture_output=True,text=True,timeout=3)
                    report.update('initializing_usb',usb_access={'readable':os.access(device,os.R_OK),'writable':os.access(device,os.W_OK)},usb_owners=(owners.stdout+owners.stderr)[-3000:])
                except (OSError,ValueError,subprocess.TimeoutExpired):pass
            camera.init(context)
            initialized = True
            from .camera_adapters import adapter_for
            adapter=adapter_for(camera,gp,report);adapter.context=context
            yield adapter
        except Exception as exc:
            if report: report.failed(exc)
            if not initialized:
                detail=' · '.join(driver_messages[-3:])
                if not detail:detail=str(exc)
                model=selected['model'] if selected else 'la cámara seleccionada'
                raise CameraError(f'No se pudo abrir {model} por USB. {detail}\nComprueba modo foto/M y conexión USB para control de fotos; vuelve a encender la cámara si continúa. No se tomó ninguna foto.') from exc
            raise
        finally:
            try:camera.exit(context)
            except Exception as exc:
                if report:report.update(report.data.get('stage','error'),exit_warning=str(exc))
