#!/bin/bash
set -euo pipefail
ROOT=/home/builder/live/chroot
chroot "$ROOT" cmake --build /tmp/astroall-phd2/build --target phd2 -j 4
chroot "$ROOT" cmake --install /tmp/astroall-phd2/build
echo PHD2_BUILD_READY
