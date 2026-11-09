#!/bin/bash
set -euo pipefail
BASE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd -- "$BASE"
echo 'Astro One4All 0.3.1 · corrección de captura Canon R50'
echo 'Termina las capturas y cierra Astro One4All y PHD2 antes de continuar.'
echo 'La actualización conserva las versiones anteriores y las preferencias.'
if ! test -f /etc/astroall-live; then echo 'Ejecuta este archivo dentro de Astro One4All Live.'; exit 1; fi
if ! grep -q '/run/live/persistence/' /proc/mounts; then echo 'Arranca con persistencia antes de actualizar.'; exit 1; fi
sha256sum --check SHA256SUMS
sudo python3 "$BASE/install-update.py" "$BASE/Astro-One4All-0.3.1-actualizacion.tar.gz"
echo
echo 'Listo. Abre Astro One4All desde el menú: debe mostrar 0.3.1.'
echo 'Equipo y sistema ofrece Prueba foto (1 s) y Prueba Bulb (3 s).'
if test -t 0; then read -r -p 'Pulsa Enter para cerrar.' _astroall_answer; fi
