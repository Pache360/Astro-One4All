#!/bin/bash
# New image from the isolated builder root. Never accesses a physical disk.
set -euo pipefail
export LC_ALL=C
cd /home/builder/live
test "$(pwd -P)" = /home/builder/live
ROOT=/home/builder/live/chroot
test -x "$ROOT/usr/local/bin/phd2"
grep -q '^OK$' /home/builder/qa03-unit.log
grep -q '"result": "passed"' /home/builder/qa03-oat.json
for mount in "$ROOT/proc" "$ROOT/dev/pts" "$ROOT/dev"; do
    if mountpoint -q "$mount"; then umount "$mount"; fi
done
if findmnt -R "$ROOT" >/dev/null 2>&1; then echo 'Unexpected active mount in image root' >&2; exit 1; fi
mkdir -p "$ROOT/opt/astroall/system" "$ROOT/usr/local/src"
cp -a /home/builder/project/astroall/. "$ROOT/opt/astroall/astroall/"
cp -a /home/builder/project/tests/. "$ROOT/opt/astroall/tests/"
cp -a /home/builder/project/docs/. "$ROOT/opt/astroall/docs/"
cp -a /home/builder/project/system/. "$ROOT/opt/astroall/system/"
cp /home/builder/project/README.md /home/builder/project/LICENSE /home/builder/project/CONTRIBUTING.md /home/builder/project/pyproject.toml "$ROOT/opt/astroall/"
cp /home/builder/phd2-2.6.13.tar.gz "$ROOT/usr/local/src/"
install -m 755 /home/builder/project/system/indi_astroall_oat "$ROOT/usr/local/bin/indi_astroall_oat"
chroot "$ROOT" bash /opt/astroall/system/0100-astroall.hook.chroot
# Exact, verified build-only path; preserve the original corresponding source archive.
test "$(realpath "$ROOT/tmp/astroall-phd2")" = /home/builder/live/chroot/tmp/astroall-phd2
rm -rf -- "$ROOT/tmp/astroall-phd2"
cp /home/builder/qa03-unit.log "$ROOT/opt/astroall/qa03-unit.log"
cp /home/builder/qa03-oat.json "$ROOT/opt/astroall/qa03-oat.json"
find "$ROOT/opt/astroall" -type d -name __pycache__ -exec rm -rf -- {} +
(cd "$ROOT/opt/astroall" && find astroall -type f -print0 | sort -z | xargs -0 sha256sum) > "$ROOT/opt/astroall/source-sha256.txt"
chroot "$ROOT" dpkg-query -W > /home/builder/03-filesystem.packages
mksquashfs "$ROOT" /home/builder/03-filesystem.squashfs -noappend -comp zstd -Xcompression-level 3 -processors 4
mkdir -p /home/builder/binary03
cp -a binary/. /home/builder/binary03/
cp /home/builder/03-filesystem.squashfs /home/builder/binary03/live/filesystem.squashfs
cp /home/builder/03-filesystem.packages /home/builder/binary03/live/filesystem.packages
sed -i 's/Astro One4All (amd64)/Astro One4All 0.3 (amd64)/g' /home/builder/binary03/isolinux/live.cfg /home/builder/binary03/boot/grub/grub.cfg
(cd /home/builder/binary03 && find . -type f ! -name sha256sum.txt -print0 | sort -z | xargs -0 sha256sum) > /home/builder/03-sha256sum.txt
if test -e /home/builder/Astro-One4All-0.3-prueba-amd64.iso; then rm -- /home/builder/Astro-One4All-0.3-prueba-amd64.iso; fi
xorriso -indev live-image-amd64.hybrid.iso -outdev /home/builder/Astro-One4All-0.3-prueba-amd64.iso -boot_image any replay -volid ASTROALL_03 \
  -map /home/builder/03-filesystem.squashfs /live/filesystem.squashfs \
  -map /home/builder/03-filesystem.packages /live/filesystem.packages \
  -map /home/builder/binary03/isolinux/live.cfg /isolinux/live.cfg \
  -map /home/builder/binary03/boot/grub/grub.cfg /boot/grub/grub.cfg \
  -map /home/builder/03-sha256sum.txt /sha256sum.txt
sha256sum /home/builder/Astro-One4All-0.3-prueba-amd64.iso > /home/builder/SHA256SUMS03
echo ASTROALL_IMAGE03_READY
