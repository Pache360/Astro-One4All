#!/bin/bash
# Repair the already-tested local prototype root; never writes a physical disk.
set -euo pipefail
export LC_ALL=C DEBIAN_FRONTEND=noninteractive
cd /home/builder/live
test "$(pwd -P)" = /home/builder/live
test -f chroot/opt/astroall/qa-integration.json
mv SHA256SUMS SHA256SUMS.original
cp /home/builder/user-setup_1.107_all.deb chroot/tmp/astroall-user-setup.deb
chroot chroot /usr/bin/env DEBIAN_FRONTEND=noninteractive dpkg -i /tmp/astroall-user-setup.deb
rm chroot/tmp/astroall-user-setup.deb
test "$(chroot chroot dpkg-query -W -f='${db:Status-Status}' user-setup)" = installed
cp -a /home/builder/project/astroall/. chroot/opt/astroall/astroall/
cp -a /home/builder/project/docs/. chroot/opt/astroall/docs/
cp -a /home/builder/project/tests/. chroot/opt/astroall/tests/
cp /home/builder/project/system/0100-astroall.hook.chroot chroot/tmp/astroall-final-config.sh
chroot chroot /bin/bash /tmp/astroall-final-config.sh
rm chroot/tmp/astroall-final-config.sh
mkdir -p chroot/tmp/astroall-qa
cp /home/builder/qa-apod4.jpg chroot/tmp/astroall-qa/apod4.jpg
cp /home/builder/project/system/0990-qa.hook.chroot chroot/tmp/astroall-qa-check.sh
chroot chroot /bin/bash /tmp/astroall-qa-check.sh
rm chroot/tmp/astroall-qa-check.sh
mksquashfs chroot repaired-filesystem.squashfs -noappend -comp zstd -Xcompression-level 3 -processors 4
mv repaired-filesystem.squashfs binary/live/filesystem.squashfs
chroot chroot dpkg-query -W > binary/live/filesystem.packages
(cd binary && /bin/sh /home/builder/project/system/0500-astroall.hook.binary)
(cd binary && find . -type f ! -name sha256sum.txt -print0 | sort -z | xargs -0 sha256sum) > repaired-sha256sum.txt
xorriso -indev live-image-amd64.hybrid.iso -outdev repaired.iso -boot_image any replay \
    -map binary/live/filesystem.squashfs /live/filesystem.squashfs \
    -map binary/live/filesystem.packages /live/filesystem.packages \
    -map binary/isolinux/isolinux.cfg /isolinux/isolinux.cfg \
    -map binary/isolinux/menu.cfg /isolinux/menu.cfg \
    -map binary/isolinux/live.cfg /isolinux/live.cfg \
    -map binary/boot/grub/config.cfg /boot/grub/config.cfg \
    -map binary/boot/grub/grub.cfg /boot/grub/grub.cfg \
    -map repaired-sha256sum.txt /sha256sum.txt
mv repaired.iso live-image-amd64.hybrid.iso
sha256sum live-image-amd64.hybrid.iso > SHA256SUMS
echo ASTROALL_REPAIR_COMPLETE
