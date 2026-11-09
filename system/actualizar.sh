#!/bin/bash
set -euo pipefail
BASE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd -- "$BASE"
echo 'Astro One4All 0.3 · actualización sin borrar la USB'
echo 'Termina cualquier captura y desconecta los equipos desde sus aplicaciones antes de actualizar.'
echo 'Este paquete conserva tus preferencias y la versión 0.2.'
sha256sum --check SHA256SUMS
sudo python3 "$BASE/install-update.py" "$BASE/Astro-One4All-0.3-actualizacion.tar.gz"
echo
echo 'Actualización terminada. Reinicia Astro One4All desde el menú.'
read -r -p 'Pulsa Enter para cerrar.' _astroall_answer
