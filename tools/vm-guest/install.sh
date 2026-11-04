#!/bin/sh
#
# Installs the base system the NosArch test VM starts from. It runs inside the Arch live ISO, started by `tools/vm
# create`, and installs onto /dev/vda with the layout NosArch's definition code expects: UEFI, one LUKS2 container
# mapped as `cryptroot`, the six Btrfs subvolumes NosArch expects, and Limine as the bootloader.
#
# The seed directory (mounted at SEED_DIR) holds `vm.env`, `authorized_keys` and `chroot.sh`.

set -eu

SEED_DIR=/run/nosarch-seed
TARGET=/mnt
DISK=/dev/vda
ESP="${DISK}1"
LUKS_PART="${DISK}2"

## === Utilities ===
_log() {
    printf '\n==> %s\n' "$*"
}

_fail() {
    printf '\nNOSARCH-VM: install failed: %s\n' "$*"
    exit 1
}

## === Features ===
_partition() {
    _log "Partitioning ${DISK}"
    sfdisk "$DISK" <<EOF
label: gpt
size=1GiB, type=U
type=L
EOF
    udevadm settle
    mkfs.fat -F 32 -n ESP "$ESP"
}

_encrypt_and_format() {
    _log "Creating the LUKS container and the Btrfs filesystem"
    # Few PBKDF2 iterations: the passphrase protects nothing, and every boot of the VM unlocks it.
    printf '%s' "$PASSPHRASE" | cryptsetup luksFormat --batch-mode --type luks2 --pbkdf pbkdf2 \
        --pbkdf-force-iterations 1000 --key-file - "$LUKS_PART"
    printf '%s' "$PASSPHRASE" | cryptsetup open --key-file - "$LUKS_PART" cryptroot

    mkfs.btrfs --force --label nosarch /dev/mapper/cryptroot

    mount /dev/mapper/cryptroot "$TARGET"
    for subvolume in @ @home @log @pkg @swap @snapshots; do
        btrfs subvolume create "${TARGET}/${subvolume}"
    done
    umount "$TARGET"

    # The layout NosArch expects, see docs/internal/btrfs-layout.md.
    options="noatime,compress=zstd"
    mount --options "${options},subvol=@" /dev/mapper/cryptroot "$TARGET"
    mkdir --parents "${TARGET}/boot" "${TARGET}/home" "${TARGET}/var/log" "${TARGET}/var/cache/pacman/pkg" \
        "${TARGET}/swap" "${TARGET}/.snapshots"
    mount --options "${options},subvol=@home" /dev/mapper/cryptroot "${TARGET}/home"
    mount --options "${options},subvol=@log" /dev/mapper/cryptroot "${TARGET}/var/log"
    mount --options "${options},subvol=@pkg" /dev/mapper/cryptroot "${TARGET}/var/cache/pacman/pkg"
    mount --options "noatime,subvol=@swap" /dev/mapper/cryptroot "${TARGET}/swap"
    mount --options "${options},subvol=@snapshots" /dev/mapper/cryptroot "${TARGET}/.snapshots"
    # Snapper refuses a snapshot directory other users can read.
    chmod 0750 "${TARGET}/.snapshots"
    mount "$ESP" "${TARGET}/boot"
}

_install_base() {
    _log "Installing the base system"
    # No linux-firmware: the machine is virtual, and NosArch installs firmware by detected hardware itself.
    pacstrap -K "$TARGET" base base-devel linux btrfs-progs cryptsetup dosfstools efibootmgr git limine \
        networkmanager openssh sudo nano
    genfstab -U "$TARGET" >"${TARGET}/etc/fstab"
}

_configure() {
    _log "Configuring the system"
    luks_uuid=$(blkid --match-tag UUID --output value "$LUKS_PART")

    install -D --mode 0644 "${SEED_DIR}/authorized_keys" "${TARGET}/root/.ssh/authorized_keys.seed"
    install --mode 0755 "${SEED_DIR}/chroot.sh" "${TARGET}/root/nosarch-vm-chroot.sh"

    arch-chroot "$TARGET" env \
        "VM_HOSTNAME=${VM_HOSTNAME}" "VM_USERNAME=${VM_USERNAME}" "VM_PASSWORD=${VM_PASSWORD}" \
        "LUKS_UUID=${luks_uuid}" /root/nosarch-vm-chroot.sh

    rm "${TARGET}/root/nosarch-vm-chroot.sh" "${TARGET}/root/.ssh/authorized_keys.seed"
}

## ===
main() {
    # shellcheck source=/dev/null
    . "${SEED_DIR}/vm.env"

    [ -d /sys/firmware/efi ] || _fail "the live system did not boot through UEFI"

    _partition
    _encrypt_and_format
    _install_base
    _configure

    _log "Unmounting"
    sync
    umount --recursive "$TARGET"
    cryptsetup close cryptroot

    printf '\nNOSARCH-VM: install complete\n'
}

main "$@"
