#!/bin/bash
set -euo pipefail
BASE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd -- "$BASE"
echo 'Astro One4All 0.3.9 · atlas, GPS OAT y captura modular'
echo 'Termina las capturas y cierra Astro One4All y PHD2 antes de continuar.'
if ! test -f /etc/astroall-live; then echo 'Ejecuta este archivo dentro de Astro One4All Live.'; exit 1; fi
if ! grep -q '/run/live/persistence/' /proc/mounts; then echo 'Arranca con persistencia antes de actualizar.'; exit 1; fi
sha256sum --check SHA256SUMS
sudo python3 "$BASE/install-update.py" "$BASE/Astro-One4All-0.3.9-actualizacion.tar.gz"
echo 'Listo. Reinicia Linux. Al volver, la aplicación debe mostrar 0.3.9.'
if test -t 0; then read -r -p 'Pulsa Enter para cerrar.' _astroall_answer; fi
