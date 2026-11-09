#!/bin/bash
# Recipe only: build on a Debian 13 amd64 host. Does not write to a USB device.
set -euo pipefail
export LC_ALL=C
export DEBIAN_FRONTEND=noninteractive
source /etc/os-release
if [[ "${ID:-}" != debian || "${VERSION_CODENAME:-}" != trixie || "$(dpkg --print-architecture)" != amd64 ]]; then
    echo 'Build host must be Debian 13 (trixie), amd64.' >&2
    exit 1
fi
if [[ "$EUID" != 0 ]]; then
    echo 'Run with sudo bash system/build-live.sh [empty-build-directory].' >&2
    exit 1
fi
PROJECT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
BUILD=${1:-"$PROJECT/build/live"}
mkdir -p -- "$BUILD"
BUILD=$(cd -- "$BUILD" && pwd)
if [[ -n "$(find "$BUILD" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    echo 'Build directory must be empty. Use a new directory; existing data is never deleted.' >&2
    exit 1
fi
apt-get update
apt-get install -y --no-install-recommends live-build debootstrap xorriso \
    grub-pc-bin grub-efi-amd64-bin mtools dosfstools squashfs-tools curl ca-certificates
cd -- "$BUILD"
lb config --distribution trixie --architectures amd64 --binary-image iso-hybrid \
    --archive-areas 'main contrib non-free-firmware' --debian-installer none \
    --apt-recommends false --firmware-chroot false --firmware-binary false --bootloaders 'syslinux,grub-efi' \
    --chroot-squashfs-compression-type zstd --chroot-squashfs-compression-level 3 \
    --iso-volume ASTROALL_03 --iso-application 'Astro One4All 0.3' --checksums sha256 \
    --bootappend-live 'boot=live components persistence username=astro hostname=astroall locales=es_MX.UTF-8 keyboard-layouts=latam timezone=America/Mexico_City console=tty0 console=ttyS0,115200n8'
mkdir -p config/package-lists config/hooks/normal config/includes.chroot/opt/astroall \
    config/includes.chroot/usr/local/src
cp -- "$PROJECT/system/packages.list" config/package-lists/astroall.list.chroot
if [[ "${ASTROALL_INCLUDE_EKOS:-0}" == 1 ]]; then
    printf '%s\n' kstars >> config/package-lists/astroall.list.chroot
fi
cp -- "$PROJECT/system/0100-astroall.hook.chroot" config/hooks/normal/
cp -- "$PROJECT/system/0200-phd2.hook.chroot" config/hooks/normal/
cp -- "$PROJECT/system/0990-qa.hook.chroot" config/hooks/normal/
cp -- "$PROJECT/system/0500-astroall.hook.binary" config/hooks/normal/
chmod +x config/hooks/normal/0100-astroall.hook.chroot
chmod +x config/hooks/normal/0200-phd2.hook.chroot
chmod +x config/hooks/normal/0990-qa.hook.chroot
chmod +x config/hooks/normal/0500-astroall.hook.binary
cp -a -- "$PROJECT/astroall" config/includes.chroot/opt/astroall/
cp -a -- "$PROJECT/system" config/includes.chroot/opt/astroall/
cp -a -- "$PROJECT/docs" config/includes.chroot/opt/astroall/
cp -a -- "$PROJECT/tests" config/includes.chroot/opt/astroall/
cp -- "$PROJECT/README.md" config/includes.chroot/opt/astroall/
cp -- "$PROJECT/LICENSE" "$PROJECT/CONTRIBUTING.md" "$PROJECT/pyproject.toml" config/includes.chroot/opt/astroall/
# Canon R50 was added in 2.5.32; Debian's stock 2.5.31 isn't sufficient.
# Digest from the publisher's GitHub release asset metadata, inspected 2026-11-02.
SOURCE=config/includes.chroot/usr/local/src/libgphoto2-2.5.33.tar.xz
curl --fail --location --proto '=https' --tlsv1.2 \
    'https://github.com/gphoto/libgphoto2/releases/download/v2.5.33/libgphoto2-2.5.33.tar.xz' -o "$SOURCE"
printf '%s  %s\n' '28825f767a85544cb58f6e15028f8e53a5bb37a62148b3f1708b524781c3bef2' "$SOURCE" | sha256sum --check -
PHD_SOURCE=config/includes.chroot/usr/local/src/phd2-2.6.13.tar.gz
curl --fail --location --proto '=https' --tlsv1.2 \
    'https://codeload.github.com/OpenPHDGuiding/phd2/tar.gz/refs/tags/v2.6.13' -o "$PHD_SOURCE"
printf '%s  %s\n' 619993ce5a8baf1c62ba5dcb3ae485b4b82e0d8ce247d6b565b1db6a7de274cf "$PHD_SOURCE" | sha256sum --check -
lb build 2>&1 | tee build.log
sha256sum live-image-amd64.hybrid.iso > SHA256SUMS
echo "Image created in: $BUILD/live-image-amd64.hybrid.iso"
echo 'Boot and hardware tests are still required. No USB device has been modified.'
