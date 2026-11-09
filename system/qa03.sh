#!/bin/bash
set -euo pipefail
ROOT=/home/builder/live/chroot
mountpoint -q "$ROOT/dev" || mount --bind /dev "$ROOT/dev"
mountpoint -q "$ROOT/dev/pts" || mount --bind /dev/pts "$ROOT/dev/pts"
mountpoint -q "$ROOT/proc" || mount -t proc proc "$ROOT/proc"
trap 'umount "$ROOT/proc"; umount "$ROOT/dev/pts"; umount "$ROOT/dev"' EXIT
cp -a /home/builder/project/astroall/. "$ROOT/opt/astroall/astroall/"
cp -a /home/builder/project/tests/. "$ROOT/opt/astroall/tests/"
cp -a /home/builder/project/docs/. "$ROOT/opt/astroall/docs/"
mkdir -p "$ROOT/opt/astroall/system"
cp -a /home/builder/project/system/. "$ROOT/opt/astroall/system/"
cp /home/builder/project/README.md /home/builder/project/LICENSE /home/builder/project/CONTRIBUTING.md /home/builder/project/pyproject.toml "$ROOT/opt/astroall/"
cp /home/builder/project/system/indi_astroall_oat "$ROOT/usr/local/bin/indi_astroall_oat"
chmod +x "$ROOT/usr/local/bin/indi_astroall_oat"
chroot "$ROOT" /bin/sh -c 'cd /opt/astroall && xvfb-run -a -s "-screen 0 1366x768x24" python3 -m unittest discover -s tests -q' > /home/builder/qa03-unit.log 2>&1
chroot "$ROOT" /bin/sh -c 'cd /opt/astroall && PYTHONPATH=/opt/astroall python3 tests/integration_oat.py' > /home/builder/qa03-oat.json 2>/home/builder/qa03-oat-error.log
echo ASTROALL_QA03_READY
