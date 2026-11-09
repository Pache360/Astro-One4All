#!/bin/bash
set -euo pipefail
export LC_ALL=C
ROOT=/home/builder/live/chroot
test -f "$ROOT/opt/astroall/qa-unit.log"
mkdir -p "$ROOT/tmp/astroall-phd2"
tar -xzf /home/builder/phd2-2.6.13.tar.gz -C "$ROOT/tmp/astroall-phd2" --strip-components=1
chroot "$ROOT" cmake -S /tmp/astroall-phd2 -B /tmp/astroall-phd2/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local \
  -DOPENSOURCE_ONLY=ON -DUSE_SYSTEM_LIBINDI=ON -DUSE_SYSTEM_CFITSIO=ON \
  -DUSE_SYSTEM_EIGEN3=ON -DUSE_SYSTEM_GTEST=ON -DUSE_SYSTEM_LIBUSB=ON
chroot "$ROOT" cmake --build /tmp/astroall-phd2/build --target phd2 -j 4
chroot "$ROOT" cmake --install /tmp/astroall-phd2/build
echo PHD2_BUILD_READY
