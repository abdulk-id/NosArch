#!/bin/sh
#
# The in-chroot half of `install.sh`. It configures the freshly installed system with a plain Limine entry, just enough
# to boot it. `provision.sh` finishes the job once the system is running.
#
# Expects VM_HOSTNAME, VM_USERNAME, VM_PASSWORD and LUKS_UUID in the environment.

set -eu

## === Utilities ===
_log() {
    printf '\n==> %s\n' "$*"
}

## === Features ===
_configure_system() {
    _log "Configuring locale, clock and hostname"
    ln --symbolic --force /usr/share/zoneinfo/UTC /etc/localtime
    sed --in-place 's/^#en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen
    locale-gen
    printf 'LANG=en_US.UTF-8\n' >/etc/locale.conf
    printf 'KEYMAP=us\n' >/etc/vconsole.conf
    printf '%s\n' "$VM_HOSTNAME" >/etc/hostname
}

_configure_initramfs() {
    _log "Configuring the initramfs"
    # The hooks NosArch's own mkinitcpio.conf uses, minus plymouth, which NosArch installs itself.
    sed --in-place 's/^HOOKS=.*/HOOKS=(base systemd autodetect microcode modconf kms keyboard sd-vconsole block sd-encrypt filesystems fsck)/' \
        /etc/mkinitcpio.conf
}

_configure_users() {
    _log "Creating users"
    useradd --create-home --groups wheel --shell /bin/bash "$VM_USERNAME"
    printf 'root:%s\n%s:%s\n' "$VM_PASSWORD" "$VM_USERNAME" "$VM_PASSWORD" | chpasswd

    # An agent drives the VM without anyone to type a password.
    printf '%%wheel ALL=(ALL:ALL) NOPASSWD: ALL\n' >/etc/sudoers.d/10-nosarch-vm
    chmod 0440 /etc/sudoers.d/10-nosarch-vm

    for account_home in /root "/home/${VM_USERNAME}"; do
        install --directory --mode 0700 "${account_home}/.ssh"
        install --mode 0600 /root/.ssh/authorized_keys.seed "${account_home}/.ssh/authorized_keys"
    done
    chown --recursive "${VM_USERNAME}:${VM_USERNAME}" "/home/${VM_USERNAME}/.ssh"

    cat >"/home/${VM_USERNAME}/.nosarch_config.json" <<EOF
{
  "user": {
    "username": "${VM_USERNAME}",
    "fullname": "NosArch Tester"
  }
}
EOF
    chown "${VM_USERNAME}:${VM_USERNAME}" "/home/${VM_USERNAME}/.nosarch_config.json"
}

_configure_ssh() {
    _log "Configuring SSH"
    printf 'PermitRootLogin prohibit-password\nPasswordAuthentication no\n' >/etc/ssh/sshd_config.d/10-nosarch-vm.conf
    systemctl enable sshd.service NetworkManager.service
}

_install_bootloader() {
    _log "Installing Limine"
    mkinitcpio --allpresets

    # The ESP is mounted at /boot, so the kernel and initramfs sit on the volume Limine's config is read from. The
    # fallback path is what UEFI firmware loads when it has no boot entry for the disk, which a fresh VM never has.
    install -D --mode 0644 /usr/share/limine/BOOTX64.EFI /boot/EFI/BOOT/BOOTX64.EFI

    cat >/boot/limine.conf <<EOF
timeout: 3

/Arch Linux
    protocol: linux
    path: boot():/vmlinuz-linux
    module_path: boot():/initramfs-linux.img
    cmdline: rd.luks.name=${LUKS_UUID}=cryptroot root=/dev/mapper/cryptroot rootflags=subvol=@ rw
EOF
}

## ===
main() {
    _configure_system
    _configure_initramfs
    _configure_users
    _configure_ssh
    _install_bootloader
}

main "$@"
