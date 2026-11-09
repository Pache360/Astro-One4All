"""Own small INDI mount client. Camera BLOBs are disabled on this connection."""
import socket
import time
import xml.etree.ElementTree as ET
from collections import deque


class IndiError(RuntimeError):
    pass

class IndiRejected(IndiError):
    """The driver rejected an operation; the transport is still connected."""
    pass


class IndiClient:
    def __init__(self, host="127.0.0.1", port=7624):
        self.host, self.port = host, port
        self.properties = {}
        self.revision = 0
        self.messages=deque(maxlen=20)

    def __enter__(self):
        self.sock = socket.create_connection((self.host, self.port), timeout=4)
        self.sock.settimeout(.25)
        self.parser = ET.XMLPullParser(events=("start", "end"))
        self.parser.feed("<stream>")
        self.depth, self.root = 0, None
        try:
            self.send(ET.Element("enableBLOB", {}), "Never")
            self.send(ET.Element("getProperties", {"version": "1.7"}))
            self.collect(1.2)
        except Exception:
            self.sock.close()
            raise
        return self

    def __exit__(self, *args):
        self.sock.close()

    def send(self, element, text=None):
        if text is not None:
            element.text = text
        self.sock.sendall(ET.tostring(element, encoding="utf-8") + b"\n")

    def ingest(self, data):
        if b"<!" in data:
            raise IndiError("Declaración XML no permitida en el enlace de montura.")
        self.parser.feed(data)
        for event, element in self.parser.read_events():
            if event == "start":
                self.depth += 1
                if self.depth == 1:
                    self.root = element
            else:
                if self.depth == 2:
                    device, name = element.get("device"), element.get("name")
                    if device and name and element.tag.startswith(("def", "set")) and element.tag.endswith("Vector") and 'BLOB' not in element.tag:
                        key = device, name
                        previous = self.properties.get(key, {})
                        values = dict(previous.get("values", {}))
                        values.update({child.get("name"): (child.text or "").strip() for child in element})
                        self.revision += 1
                        self.properties[key] = {"tag": element.tag, "values": values,
                                                "state": element.get("state", previous.get("state", "Idle")),
                                                "revision": self.revision,
                                                "permission": element.get("perm", previous.get("permission", "rw"))}
                    elif element.tag=='setBLOBVector': self.handle_blob(element)
                    # defBLOBVector advertises camera image capabilities. It has no
                    # image data and is normal on a shared camera/mount server.
                    elif element.tag=='message':
                        self.messages.append({'device':device,'message':element.get('message','')[:500]})
                    elif element.tag == "delProperty" and device:
                        for key in list(self.properties):
                            if key[0] == device and (not name or key[1] == name):
                                del self.properties[key]
                    self.root.remove(element)
                self.depth -= 1

    def collect(self, seconds):
        deadline = time.monotonic() + seconds
        received = 0
        while time.monotonic() < deadline:
            try:
                chunk = self.sock.recv(16384)
            except socket.timeout:
                continue
            if not chunk:
                raise IndiError("El servidor INDI cerró la conexión.")
            received += len(chunk)
            if received > getattr(self,'max_receive_bytes',2*1024*1024):
                raise IndiError("Respuesta de montura demasiado grande.")
            self.ingest(chunk)

    def handle_blob(self,element):
        raise IndiError("Se recibió una imagen en una conexión exclusiva de montura.")

    def get(self, device, name):
        try:
            return self.properties[device, name]
        except KeyError as exc:
            raise IndiError(f"El controlador no anuncia {device}/{name}.") from exc

    def write(self, device, name, values, kind):
        prop = self.get(device, name)
        if prop["permission"] == "ro":
            raise IndiError(f"{name} es de solo lectura.")
        if not set(values) <= set(prop["values"]):
            raise IndiError(f"El controlador no anuncia los miembros solicitados en {name}.")
        element = ET.Element("new" + kind + "Vector", {"device": device, "name": name})
        for key, value in values.items():
            ET.SubElement(element, "one" + kind, {"name": key}).text = str(value)
        revision = prop["revision"]
        self.send(element)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            self.collect(.3)
            latest = self.get(device, name)
            if latest["revision"] > revision:
                if latest["state"] == "Alert":
                    detail=next((m['message'] for m in reversed(self.messages) if m['device']==device),'')
                    raise IndiRejected(f"El controlador rechazó {name}. "+detail)
                matches = all(latest["values"].get(k) == str(v) for k, v in values.items())
                if kind == "Number" or (name in ("TELESCOPE_ABORT_MOTION","OAT_EXISTING_HOME","OAT_READ_SITE_TIME","CCD_ABORT_EXPOSURE") and latest['state']!='Busy') or (matches and (latest["state"] != "Busy" or name.startswith('TELESCOPE_MOTION_') or name=='CCD_VIDEO_STREAM')):
                    return latest
        raise IndiError(f"No se confirmó {name}; no se reenvió el comando.")

    def switch(self, device, name, selected):
        values = self.get(device, name)["values"]
        if selected not in values:
            raise IndiError(f"No se anuncia {name}/{selected}.")
        return self.write(device, name, {key: "On" if key == selected else "Off" for key in values}, "Switch")

    def connect_mount(self, device, serial_port, baud):
        executable=self.get(device,'DRIVER_INFO')['values'].get('DRIVER_EXEC','').rsplit('/',1)[-1]
        if executable=='indi_simulator_telescope':
            self.switch(device,'CONNECTION','CONNECT')
            self.collect(2)
            return self.snapshot(device)
        if (device,'DEVICE_PORT') not in self.properties:
            raise IndiError('El perfil OAT necesita un puerto serie anunciado por el controlador.')
        if not serial_port.startswith("/dev/"):
            raise ValueError("Selecciona el puerto serie Linux de la montura.")
        if self.get(device,'CONNECTION')['values'].get('CONNECT')=='On':
            from pathlib import Path
            actual=self.get(device,'DEVICE_PORT')['values'].get('PORT','')
            options=self.get(device,'DEVICE_BAUD_RATE')['values']
            same_baud=any(options.get(key)=='On' for key in (str(baud),'BAUD_'+str(baud)))
            if Path(actual).resolve()!=Path(serial_port).resolve() or not same_baud:
                raise IndiError('La montura ya está conectada con otro puerto o velocidad. Desconéctala antes de cambiar el perfil.')
            # Reuse the driver's existing serial connection, including PHD2 users.
            return self.snapshot(device)
        self.write(device, "DEVICE_PORT", {"PORT": serial_port}, "Text")
        options = self.get(device, "DEVICE_BAUD_RATE")["values"]
        selected = next((key for key in options if key == str(baud) or key == "BAUD_" + str(baud)), None)
        if selected is None:
            raise IndiError("El controlador no ofrece esa velocidad serie.")
        self.switch(device, "DEVICE_BAUD_RATE", selected)
        self.switch(device, "CONNECTION", "CONNECT")
        self.collect(2)
        if self.get(device, "CONNECTION")["values"].get("CONNECT") != "On" or self.get(device, "CONNECTION")["state"] == "Alert":
            raise IndiError("La montura no confirmó la conexión.")
        return self.snapshot(device)

    def snapshot(self, device=None):
        return {dev + "/" + name: prop for (dev, name), prop in self.properties.items() if device is None or dev == device}

    def goto_eod(self, device, ra_hours, dec_deg):
        import math
        if not (math.isfinite(ra_hours) and 0 <= ra_hours < 24 and math.isfinite(dec_deg) and -90 <= dec_deg <= 90):
            raise ValueError("AR en horas [0,24); DEC en grados [-90,90].")
        if self.get(device, "CONNECTION")["values"].get("CONNECT") != "On":
            raise IndiError("La montura está desconectada.")
        self.switch(device, "ON_COORD_SET", "TRACK")
        result = self.write(device, "EQUATORIAL_EOD_COORD", {"RA": ra_hours, "DEC": dec_deg}, "Number")
        return {"command": "goto", "state": result["state"], "ra_hours_eod": ra_hours,
                "dec_deg_eod": dec_deg, "note": "Comando recibido; no confirma que el movimiento haya finalizado."}

    def abort(self, device):
        return self.switch(device, "TELESCOPE_ABORT_MOTION", "ABORT")

    def motion(self,device,direction=None,axis=None):
        names={'n':('NS','MOTION_NORTH'),'s':('NS','MOTION_SOUTH'),'w':('WE','MOTION_WEST'),'e':('WE','MOTION_EAST')}
        if direction is not None:
            suffix,member=names[direction]
            return self.switch(device,'TELESCOPE_MOTION_'+suffix,member)
        if axis not in ('NS','WE'): raise ValueError('Eje inválido.')
        name='TELESCOPE_MOTION_'+axis
        return self.write(device,name,{k:'Off' for k in self.get(device,name)['values']},'Switch')

    def wait_slew(self,device,stop=None,timeout=300):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if stop and stop.is_set():
                self.abort(device);raise IndiError('Movimiento detenido por el usuario.')
            self.collect(.3)
            prop=self.get(device,'EQUATORIAL_EOD_COORD')
            if prop['state']=='Alert': raise IndiError('La montura informó un error de movimiento.')
            if prop['state']!='Busy': return prop
        self.abort(device)
        raise IndiError('Se agotó el tiempo de movimiento; se envió parada.')
