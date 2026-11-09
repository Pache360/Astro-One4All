#!/bin/bash
set -euo pipefail
export LC_ALL=C DEBIAN_FRONTEND=noninteractive
ROOT=/home/builder/live/chroot
test -f "$ROOT/opt/astroall/qa-unit.log"
cp /etc/resolv.conf "$ROOT/etc/resolv.conf"
printf '#!/bin/sh\nexit 101\n' > "$ROOT/usr/sbin/policy-rc.d"
chmod +x "$ROOT/usr/sbin/policy-rc.d"
trap 'rm -f "$ROOT/usr/sbin/policy-rc.d"' EXIT
chroot "$ROOT" apt-get update
chroot "$ROOT" apt-get install -y --no-install-recommends cmake ninja-build libwxgtk3.2-dev libcfitsio-dev libnova-dev libudev-dev libindi-dev libcurl4-openssl-dev libgtest-dev libeigen3-dev libv4l-dev zlib1g-dev
echo PHD2_DEPENDENCIES_READY
