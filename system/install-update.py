#!/usr/bin/python3
"""Offline, versioned installation. Keeps the 0.2 tree and all home settings."""
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import shutil
import sys
import tarfile
import tempfile

def atomic_text(path,text,mode=0o755):
    path=Path(path);temporary=path.with_name(path.name+'.astroall-new')
    temporary.write_text(text,encoding='utf-8');temporary.chmod(mode);temporary.replace(path)

def install(archive_path,system_root=Path('/')):
    root=Path(system_root).resolve();archive_path=Path(archive_path).resolve()
    if root==Path('/') and os.geteuid()!=0: raise RuntimeError('Ejecuta el actualizador con sudo desde tu Live USB.')
    if root==Path('/') and not (root/'etc/astroall-live').exists(): raise RuntimeError('Este paquete actualiza Astro One4All Live; no instala ni modifica otra distribución.')
    releases=root/'opt/astroall-releases';releases.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.install-',dir=releases) as temporary:
        staging=Path(temporary)
        with tarfile.open(archive_path,'r:gz') as archive:
            total=0;names=set()
            for item in archive.getmembers():
                path=PurePosixPath(item.name)
                if path.is_absolute() or '..' in path.parts or item.issym() or item.islnk() or not (item.isdir() or item.isfile()): raise RuntimeError('El paquete contiene una ruta o enlace no permitido.')
                if item.name in names: raise RuntimeError('Nombre duplicado en el paquete.')
                names.add(item.name);total+=item.size
                if total>600*1024*1024 or len(names)>10000: raise RuntimeError('Paquete de actualización demasiado grande.')
                destination=staging.joinpath(*path.parts)
                if item.isdir(): destination.mkdir(parents=True,exist_ok=True);continue
                destination.parent.mkdir(parents=True,exist_ok=True)
                with archive.extractfile(item) as source,destination.open('wb') as output: shutil.copyfileobj(source,output,1024*1024)
                destination.chmod(0o755 if item.mode&0o111 else 0o644)
        manifest_path=staging/'manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        version=manifest.get('version')
        if version not in ('0.3.0','0.3.1','0.3.2','0.3.3','0.3.4','0.3.5','0.3.6','0.3.7','0.3.8','0.3.9','0.3.10','0.3.11','0.3.12','0.3.13') or manifest.get('architecture')!='amd64': raise RuntimeError('Versión o arquitectura de paquete incorrecta.')
        expected=set(manifest['files'])
        actual={p.relative_to(staging).as_posix() for p in staging.rglob('*') if p.is_file()}-{'manifest.json'}
        if expected!=actual: raise RuntimeError('El contenido no coincide con el manifiesto.')
        for name,digest in manifest['files'].items():
            path=staging/name
            if hashlib.sha256(path.read_bytes()).hexdigest()!=digest: raise RuntimeError('Archivo alterado o incompleto: '+name)
        target=releases/version
        if target.exists():
            previous=json.loads((target/'manifest.json').read_text(encoding='utf-8'))
            if previous!=manifest: raise RuntimeError('Ya hay otra compilación '+version+'. Conserva esa instalación y utiliza un paquete con versión nueva.')
        else:
            # Publish the verified directory atomically on the same filesystem.
            # TemporaryDirectory starts at 0700; the normal Live user needs read access.
            staging.chmod(0o755);staging.rename(target)
    current=root/'opt/astroall-current';new=current.with_name('astroall-current.new')
    if new.exists() or new.is_symlink(): new.unlink()
    new.symlink_to(target)
    new.replace(current)
    local_bin=root/'usr/local/bin';local_bin.mkdir(parents=True,exist_ok=True)
    atomic_text(local_bin/'astroall','#!/bin/sh\nexport PYTHONPATH="/opt/astroall-current${PYTHONPATH:+:$PYTHONPATH}"\nexport OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1\nexec /usr/bin/python3 -m astroall "$@"\n')
    atomic_text(local_bin/'indi_astroall_oat','#!/bin/sh\ncd /opt/astroall-current\nexec /usr/bin/python3 -m astroall.oat_driver\n')
    atomic_text(local_bin/'phd2','#!/bin/sh\nexport LD_LIBRARY_PATH="/opt/astroall-current/runtime/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\nexec /opt/astroall-current/runtime/bin/phd2 "$@"\n')
    share=root/'usr/local/share/phd2'
    share.parent.mkdir(parents=True,exist_ok=True)
    if share.exists() and not share.is_symlink():
        backup=share.with_name('phd2-before-astroall03')
        if not backup.exists(): share.rename(backup)
        else: raise RuntimeError('Hay una instalación PHD2 y una copia previa; no se reemplazó.')
    if not share.exists() and not share.is_symlink(): share.symlink_to('/opt/astroall-current/runtime/share/phd2')
    if version in ('0.3.2','0.3.3','0.3.4','0.3.5','0.3.6','0.3.7','0.3.8','0.3.9','0.3.10','0.3.11','0.3.12','0.3.13'):
        import importlib.util
        spec=importlib.util.spec_from_file_location('astroall_desktop_repair',target/'system/desktop_repair.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.repair(root,atomic_text)
    if version in ('0.3.12','0.3.13'):
        import importlib.util
        spec=importlib.util.spec_from_file_location('astroall_power_policy',target/'system/power_policy.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.install(root,atomic_text)
    print('Astro One4All '+version+' instalado. Se conservaron las versiones anteriores y las preferencias de tu usuario. Cierra la aplicación y vuelve a abrir Astro One4All.')

if __name__=='__main__':
    try: install(sys.argv[1])
    except Exception as exc: print('No se completó la actualización: '+str(exc),file=sys.stderr);sys.exit(1)
