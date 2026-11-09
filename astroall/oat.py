"""Read-only direct OAT identity probe, separate from INDI port ownership."""
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import subprocess
import time

# Only these two commands are exposed. Other OAT commands need their own spec.
IDENTITY_COMMANDS = {":GVP#": "hash", ":GVN#": "hash"}


def read_hash_reply(serial, timeout=3, max_bytes=256):
    deadline = time.monotonic() + timeout
    data = bytearray()
    while time.monotonic() < deadline:
        chunk = serial.read(1)
        if chunk:
            data.extend(chunk)
            if len(data) > max_bytes:
                raise RuntimeError("Respuesta OAT demasiado larga.")
            if chunk == b"#":
                return bytes(data).decode("ascii", errors="strict")
    raise TimeoutError("OAT no completó la respuesta terminada en #; no se reenvió el comando.")


def identify(serial):
    replies = {}
    for command, response_type in IDENTITY_COMMANDS.items():
        serial.write(command.encode("ascii"))
        serial.flush()
        if response_type == "hash":
            replies[command] = read_hash_reply(serial)
        else:
            raise RuntimeError("Tipo de respuesta no implementado.")
    return {"observed_utc": datetime.now(timezone.utc).isoformat(),
            "replies": replies, "reported_product": replies[":GVP#"].rstrip("#\r\n"),
            "reported_version": replies[":GVN#"].rstrip("#\r\n"),
            "source": "respuesta real del puerto serie; no inferida del HEX"}


def probe(port, baud=19200):
    if not 300 <= int(baud) <= 1000000:
        raise ValueError("Velocidad serie inválida.")
    try:
        import serial
    except ImportError as exc:
        raise RuntimeError("Falta python3-serial para consultar la identidad OAT directamente.") from exc
    if os.name == "posix":
        # Refuse an already-used tty before opening; TIOCEXCL then blocks later opens.
        import shutil
        if not shutil.which("fuser"):
            raise RuntimeError("Falta fuser (paquete psmisc) para comprobar quién utiliza el puerto.")
        existing = subprocess.run(["fuser", str(Path(port).resolve())], capture_output=True, timeout=3)
        if existing.returncode == 0:
            raise RuntimeError("El puerto está en uso. Desconecta INDI u otro programa antes de identificar OAT.")
        if existing.returncode != 1:
            raise RuntimeError("No se pudo comprobar si el puerto está libre.")
    from .serial_transport import open_mount_serial
    connection = open_mount_serial(port,baud)
    try:
        result = dict(identify(connection), port=port, baud=int(baud), framing="8N1")
    finally:
        connection.close()
    log = Path.home()/".local/state/astroall/oat-identity.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    if log.exists() and log.stat().st_size > 128*1024:
        log.replace(log.with_suffix(".previous.jsonl"))
    with log.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(result, ensure_ascii=False)+"\n")
    return result
