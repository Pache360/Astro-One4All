"""A bounded, disk-backed cache. Never used to store camera RAW data."""
from pathlib import Path
import os
import shutil

MIB = 1024 * 1024


class JpegCache:
    def __init__(self, root, budget=64 * MIB, max_file=16 * MIB):
        self.root = Path(root).expanduser()
        self.budget = budget
        self.max_file = max_file
        if not 0 < max_file <= budget:
            raise ValueError("El límite por JPG debe ser menor que el de caché.")
        self.root.mkdir(parents=True, exist_ok=True)

    def reserve(self, size):
        if not isinstance(size, int) or not 0 < size <= self.max_file:
            raise ValueError("JPG sin tamaño válido o mayor que el límite de descarga.")
        files = sorted((p for p in self.root.glob("*.jpg") if p.is_file()
                        and not p.is_symlink()), key=lambda p: p.stat().st_mtime_ns)
        total = sum(p.stat().st_size for p in files)
        while files and total + size > self.budget:
            old = files.pop(0)
            total -= old.stat().st_size
            old.unlink()
        if shutil.disk_usage(self.root).free < size + 8 * MIB:
            raise OSError("No hay espacio libre suficiente para el JPG.")

    def save(self, camera_file, size):
        """libgphoto holds one bounded JPEG; release it before the next capture."""
        import uuid
        self.reserve(size)
        target = self.root / (uuid.uuid4().hex + ".jpg")
        partial = target.with_suffix(".part")
        try:
            camera_file.save(str(partial))
            if partial.stat().st_size != size:
                raise OSError("El JPG recibido no coincide con el tamaño anunciado.")
            with partial.open("rb") as stream:
                if stream.read(2) != b"\xff\xd8":
                    raise ValueError("El archivo recibido no tiene cabecera JPEG.")
            os.replace(partial, target)
        finally:
            partial.unlink(missing_ok=True)
        return target
