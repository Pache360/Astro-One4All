#!/bin/sh
set -eu
test -d /opt/astroall/astroall
test -e /etc/astroall-live
printf '%s\n' '#!/bin/sh' 'export PYTHONPATH="/opt/astroall${PYTHONPATH:+:$PYTHONPATH}"' 'export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1' 'exec python3 -m astroall "$@"' | sudo tee /usr/local/bin/astroall.previous >/dev/null
sudo chmod 755 /usr/local/bin/astroall.previous
sudo mv /usr/local/bin/astroall.previous /usr/local/bin/astroall
echo 'Lanzador 0.2 restaurado. Cierra la aplicación y ábrela de nuevo. Preferencias conservadas.'
