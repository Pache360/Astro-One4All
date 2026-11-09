#!/bin/bash
set -euo pipefail
export LC_ALL=C DEBIAN_FRONTEND=noninteractive
ROOT=/home/builder/live/chroot
test -f "$ROOT/etc/debian_version"
mkdir -p "$ROOT/tmp/astroall-explorer-debs/partial"
cp /etc/resolv.conf "$ROOT/etc/resolv.conf"
python3 - <<'PY'
from pathlib import Path
root=Path('/home/builder/live/chroot')
rows=[]
for line in Path('/home/builder/package-versions02.txt').read_text().splitlines():
    name,version=line.split('\t',1)
    package,separator,arch=name.partition(':')
    rows.append(f'Package: {package}\nStatus: install ok installed\nArchitecture: {arch if separator else "amd64"}\nVersion: {version}\n\n')
(root/'tmp/astroall-baseline02.status').write_text(''.join(rows))
PY
chroot "$ROOT" apt-get update
# Resolve against the oldest delivered Live, not the larger build environment.
chroot "$ROOT" apt-get -y --download-only --no-install-recommends \
  -o Dir::State::status=/tmp/astroall-baseline02.status \
  -o Dir::Cache::archives=/tmp/astroall-explorer-debs \
  install gvfs udisks2 libglib2.0-bin
echo EXPLORER_REPAIR_DOWNLOADED
