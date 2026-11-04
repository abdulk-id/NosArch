#!/bin/sh
#
# The second stage of building the test VM's base image. `tools/vm create` runs it as root inside the freshly
# installed system, once that has booted: the first stage cannot, because the Limine entry tooling is built with a GraalVM
# native image, and that build does not fit in the live ISO's environment.
#
# It installs what the NosArch README lists before the first apply, decman, and the Limine tooling a stock setup has. The
# tooling matters because NosArch assumes the boot entries it generates: `default_entry: 2` is only right when
# limine-entry-tool has made the `/+Arch Linux` group, so a hand-written entry would make it pick the wrong one.

set -eu

VM_USER=nosarch
AUR_URL=https://aur.archlinux.org

## === Utilities ===
_log() {
    printf '\n==> %s\n' "$*"
}

# Builds and installs an AUR package as the unprivileged user, since makepkg refuses to run as root.
_aur_install() {
    _log "Building ${1} from the AUR"
    build_dir=$(mktemp --directory --tmpdir="/home/${VM_USER}")
    chown "$VM_USER" "$build_dir"
    su - "$VM_USER" --command "git clone --depth 1 ${AUR_URL}/${1}.git ${build_dir}/${1}"
    su - "$VM_USER" --command "cd ${build_dir}/${1} && makepkg --syncdeps --install --noconfirm"
    rm --recursive --force "$build_dir"
}

## === Features ===
_install_decman() {
    _aur_install decman
}

_install_limine_tooling() {
    _aur_install limine-mkinitcpio-hook

    _log "Generating the Limine boot entries"
    luks_uuid=$(lsblk --raw --noheadings --output UUID,FSTYPE | awk '$2 == "crypto_LUKS" { print $1 }')
    [ -n "$luks_uuid" ] || {
        echo "No LUKS container found." >&2
        exit 1
    }

    cat >/etc/default/limine <<EOF
TARGET_OS_NAME="Arch Linux"
ESP_PATH="/boot"
KERNEL_CMDLINE[default]+="rd.luks.name=${luks_uuid}=cryptroot root=/dev/mapper/cryptroot rootflags=subvol=@ rw"
ENABLE_UKI=yes
ENABLE_LIMINE_FALLBACK=yes
CUSTOM_UKI_NAME="arch"
EOF

    # Drop the hand-written entry from the first stage, so the tool alone owns the entries. The tool adds the group
    # `/+Arch Linux`, whose first child is entry 2. Without a default Limine waits on the group header, which cannot
    # boot, so this sets the value NosArch sets as well.
    printf 'default_entry: 2\ntimeout: 3\n' >/boot/limine.conf
    limine-update
}

## ===
main() {
    _install_decman
    _install_limine_tooling

    _log "Resulting /boot/limine.conf"
    cat /boot/limine.conf
}

main "$@"
