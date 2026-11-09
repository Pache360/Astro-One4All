"""Native mount, optics, and polar assistant windows."""
import json
from pathlib import Path
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk
from .indi import IndiClient
from .optics import LENSES, field_width
from .polar import estimate_polar
from .oat import probe
from .timekeeping import load_settings, save_settings, clock_snapshot


def window(root, title):
    dialog = tk.Toplevel(root)
    dialog.title("Astro One4All · " + title)
    dialog.configure(bg=root.cget("bg"))
    frame = ttk.Frame(dialog, padding=18)
    frame.pack(fill="both", expand=True)
    return dialog, frame


def entry(frame, title, value="", choices=None):
    variable = tk.StringVar(value=value)
    ttk.Label(frame, text=title).pack(anchor="w")
    widget=ttk.Combobox(frame,textvariable=variable,values=choices,width=57) if choices is not None else ttk.Entry(frame,textvariable=variable,width=60)
    widget.pack(fill="x",pady=4)
    return variable


def mount_window(root, task, write, post):
    dialog, frame = window(root, "Montura")
    config_path = Path.home()/".config/astroall/mount.json"
    try:
        saved = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    ports=sorted(str(path) for path in Path('/dev/serial/by-id').glob('*'))
    if not ports:
        ports=sorted(str(path) for pattern in ('ttyACM*','ttyUSB*') for path in Path('/dev').glob(pattern))
    fields = {key: entry(frame, label, saved.get(key, default), ports if key=='port' else ['19200','9600','38400','57600','115200'] if key=='baud' else None) for label, key, default in (
        ("Controlador", "driver", "indi_lx200gps"), ("Nombre INDI (Detectar)", "device", ""),
        ("Puerto /dev/serial/by-id/…", "port", ""), ("Baudios del firmware", "baud", "19200"),
        ("AR de fecha / JNow (horas)", "ra", ""), ("DEC de fecha / JNow (grados)", "dec", ""))}
    if len(ports)==1 and not fields['port'].get(): fields['port'].set(ports[0])
    ttk.Label(frame,text='Puerto USB detectado; revisa que corresponda al OAT.' if ports else 'Conecta el Arduino por USB y vuelve a abrir este panel.').pack(anchor='w',pady=4)
    ttk.Label(frame, text="Antes de GoTo: hora, ubicación, home y límites configurados en tu OAT.").pack(anchor="w", pady=6)
    def launch():
        driver = fields["driver"].get()
        if driver not in ("indi_lx200gps", "indi_lx200_OpenAstroTech", "indi_simulator_telescope") or not shutil.which(driver) or not shutil.which("indiserver"):
            write("El controlador o indiserver no está instalado.")
            return
        subprocess.Popen(["indiserver", "-p", "7624", driver], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        write("Controlador iniciado sin conectar al Arduino. Pulsa Detectar. No se inició un controlador de cámara.")
    def discover():
        with IndiClient() as client:
            devices = sorted({dev for dev, name in client.properties if name == "CONNECTION"})
            if len(devices) == 1:
                post(lambda: fields["device"].set(devices[0]) if dialog.winfo_exists() else None)
            return client.snapshot()
    def connect():
        chosen, port, baud = (fields[k].get().strip() for k in ("device", "port", "baud"))
        def operation():
            with IndiClient() as client:
                return client.connect_mount(chosen, port, baud)
        task("Conectando montura…", operation)
    def identity():
        port, baud = fields["port"].get(), fields["baud"].get()
        task("Consultando :GVP# y :GVN# · puerto exclusivo…", lambda: probe(port, baud))
    def goto():
        try:
            chosen, ra, dec = fields["device"].get(), float(fields["ra"].get()), float(fields["dec"].get())
        except ValueError:
            write("AR debe estar en horas y DEC en grados.")
            return
        def operation():
            with IndiClient() as client:
                return client.goto_eod(chosen, ra, dec)
        task("Enviando GoTo real…", operation)
    def abort():
        chosen = fields["device"].get()
        def operation():
            try:
                with IndiClient() as client:
                    result = client.abort(chosen)
                post(lambda: write(result))
            except Exception as exc:
                error = str(exc)
                post(lambda: write("Parada no confirmada: " + error))
        threading.Thread(target=operation, daemon=True).start()
    def save():
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps({key: fields[key].get() for key in ("driver", "device", "port", "baud")}, indent=2), encoding="utf-8")
            write("Perfil guardado; no se conecta ni mueve al iniciar.")
        except OSError as exc:
            write(str(exc))
    for text, action in (("Iniciar controlador", launch), ("Detectar / estado", lambda: task("Leyendo montura…", discover)),
                         ("Identificar OAT (en reposo, INDI desconectado)", identity), ("Conectar", connect), ("GoTo real", goto), ("PARAR montura", abort), ("Guardar perfil", save)):
        ttk.Button(frame, text=text, command=action).pack(fill="x", pady=3)


def polar_window(root, task, write, post, capture_one, solve):
    dialog, frame = window(root, "Alineación polar experimental")
    lat, lon = entry(frame, "Latitud ° (norte positivo)"), entry(frame, "Longitud ° (oeste negativo)")
    samples = []
    status = tk.StringVar(value="0 de 3 puntos")
    ttk.Label(frame, text="1. Cámara fija en DEC: medir.\n2. Gira SOLO AR desde el mando del OAT y mide de nuevo.\n3. Repite hasta 3 puntos separados al menos 5°.\nNo cambies DEC, trípode, focal, altitud ni azimut entre puntos.").pack(anchor="w", pady=10)
    ttk.Label(frame, textvariable=status).pack(anchor="w")
    def sample():
        if len(samples) >= 3:
            write("Ya hay tres puntos; reinicia para volver a medir.")
            return
        def operation():
            shot = capture_one()
            position = solve(shot["jpeg"])
            value = {"ra_deg": position.ra_deg, "dec_deg": position.dec_deg, "utc": shot["approx_mid_utc"]}
            def update():
                if dialog.winfo_exists():
                    samples.append(value)
                    status.set(f"{len(samples)} de 3 puntos")
                write(value)
            post(update)
        task("Capturando y resolviendo punto polar…", operation)
    def calculate():
        try:
            latitude, longitude = float(lat.get()), float(lon.get())
        except ValueError:
            write("Introduce tu ubicación real en grados decimales.")
            return
        copied = list(samples)
        task("Estimando el eje polar…", lambda: estimate_polar(copied, latitude, longitude))
    def clear():
        samples.clear()
        status.set("0 de 3 puntos")
    for text, action in (("Medir punto (foto real)", sample), ("Calcular ajuste de base", calculate), ("Reiniciar puntos", clear)):
        ttk.Button(frame, text=text, command=action).pack(fill="x", pady=4)
    ttk.Label(frame, text="Ajuste físico de la base; el asistente no gira motores.\nEstimación por validar con cielo real y reloj correcto.").pack(anchor="w", pady=8)


def optics_window(root, width, write):
    dialog, frame = window(root, "Óptica")
    lens = tk.StringVar(value="50 mm f/1.8")
    ttk.Combobox(frame, textvariable=lens, values=list(LENSES), width=45, state="readonly").pack(fill="x", pady=5)
    focal = entry(frame, "Focal real mm (valor actual del zoom)", "50")
    sensor = entry(frame, "Ancho del sensor mm", "22.3")
    lens.trace_add("write", lambda *args: focal.set(str(LENSES[lens.get()][0])))
    def apply():
        try:
            value = field_width(float(sensor.get()), float(focal.get()))
            width.set(f"{value:.4f}")
            write(f"Campo horizontal estimado: {value:.4f}°.")
        except ValueError as exc:
            write(str(exc))
    ttk.Button(frame, text="Aplicar campo", command=apply).pack(fill="x", pady=8)


def clock_window(root, write):
    dialog, frame = window(root, "Tiempo y viaje")
    saved = load_settings()
    zone = entry(frame, "Zona IANA (se conserva al reiniciar)", saved["timezone"])
    longitude = entry(frame, "Longitud ° opcional (oeste negativo)", "" if saved.get("longitude") is None else str(saved["longitude"]))
    ra = entry(frame, "AR de fecha en horas, opcional para HA", "")
    confirmed = tk.BooleanVar(value=saved.get("clock_confirmed", False))
    ttk.Checkbutton(frame, text="He comprobado fecha/hora UTC del ordenador", variable=confirmed).pack(anchor="w", pady=4)
    ttk.Label(frame, text="Fuente actual: reloj del ordenador. El GPS del OAT usa UTC; aún no se importa automáticamente.").pack(anchor="w", pady=5)
    def apply():
        try:
            lon = float(longitude.get()) if longitude.get().strip() else None
            coordinate = float(ra.get()) if ra.get().strip() else None
            value = save_settings(zone.get().strip(), lon, confirmed.get())
            write(clock_snapshot(value, coordinate))
        except Exception as exc:
            write(str(exc))
    ttk.Button(frame, text="Guardar / mostrar UTC, local, sidérea y HA", command=apply).pack(fill="x", pady=8)
