#!/bin/bash
set -euo pipefail
BASE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd -- "$BASE"
test -e /etc/astroall-live || { echo 'Esta reparación corresponde a Astro One4All Live.' >&2; exit 1; }
test "$(dpkg --print-architecture)" = amd64 || { echo 'Este paquete requiere Linux amd64.' >&2; exit 1; }
if grep -qw 'boot=live' /proc/cmdline && ! grep -q '/run/live/persistence/' /proc/mounts; then
    echo 'Primero activa la persistencia de la USB para conservar la reparación.' >&2
    exit 1
fi
sha256sum --check --strict SHA256SUMS
echo 'Instalando los componentes del explorador desde esta carpeta, sin internet...'
# Disable repository sources, while allowing APT's local-file acquisition step.
sudo apt-get -y --no-install-recommends --no-remove \
  -o Dir::Etc::sourcelist=/dev/null -o Dir::Etc::sourceparts=- \
  install "$BASE"/pkg*.deb
echo
echo 'Reparación instalada. Reinicia Linux para que el explorador cargue el componente nuevo.'
echo 'La vista Dispositivos muestra almacenamiento. Canon y Arduino se controlan desde Astro One4All.'
if [[ -t 0 ]]; then read -r -p 'Pulsa Enter para cerrar.' _astroall_close; fi
