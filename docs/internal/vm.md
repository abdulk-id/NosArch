# Test VM internals

How to use the VM is in [Test VM](../operations/vm.md). This records why `tools/vm` is built the way it is. Most of it
works around something NosArch itself does to the system it is applied to.

## SSH goes over vsock, not TCP

NosArch enables `ufw` with rules that allow no SSH, and the default policy drops incoming connections. In the VM `ufw`
stays inactive until something runs `ufw enable`, but whoever tests the firewall would lock themselves out of a TCP
connection, and nobody could get back in. SSH therefore goes over virtio-vsock, which is not IP traffic and so never
meets the firewall. The host connects with `socat` through `ssh`'s `ProxyCommand`, and systemd's SSH generator exposes
`sshd` on the vsock inside the guest.

## Stopping goes through SSH

NosArch sets `HandlePowerKey=ignore` in logind, so the ACPI shutdown QEMU sends is ignored after an apply. `vm stop`
runs `systemctl poweroff` over SSH, and only falls back to ending QEMU when that does not finish.

## The disk passphrase is not in the guest

The VM hands the LUKS passphrase to the initrd as a systemd credential, through SMBIOS. `sd-encrypt` picks it up, so
nobody types it. Putting a key file in the initramfs or the kernel command line instead would not survive an apply,
which rewrites both `/etc/mkinitcpio.conf` and the command line.

## The base image is built in two stages

The first stage installs the system from the live ISO, with a plain Limine entry. The second boots it and builds decman
and `limine-mkinitcpio-hook` from the AUR. They cannot be one stage: `limine-entry-tool`, which that package builds, is
a GraalVM native image, and the build fails inside the live ISO's environment.

The tool is installed in the base on purpose. NosArch sets `default_entry: 2` in `/boot/limine.conf`, which is the first
kernel entry only when the tool has generated the `/+Arch Linux` group above it. A hand-written `/Arch Linux` entry
shifts the numbering by one: entry 2 becomes "EFI fallback", which chainloads Limine from Limine, and that crashes the
firmware. The second stage writes `default_entry: 2` itself, because a base without it waits on the group header.

## Decman cannot be driven without a TTY

Decman refuses to run pacman without a terminal, and asks questions. `vm apply` therefore:

- Writes decman's store, so that it runs the synced source without asking "Proceed?". Decman asks every time `--source`
  is passed, and a dry run never saves the answer.
- Gives `ssh` a terminal and presses Enter once a second, which accepts every default. It must not be a flood of
  Enters: decman blocks writing them into pacman's input, stops reading pacman's output, and both hang.
- Puts a `less` that does nothing ahead of the real one, and sets `GIT_PAGER=true`. Decman pages through every AUR
  PKGBUILD it builds, with a default of "yes". The PKGBUILDs are therefore built without review, which is fine in a VM
  that is thrown away.

## Instances are copy-on-write clones of one base

Every instance is a qcow2 overlay with the base image as its backing file, and the base is read-only once built.
Rebuilding the base with `create --force` would leave the overlays pointing at a different disk, so it deletes them.
Checkpoints are qcow2 internal snapshots plus a copy of the firmware variables, which is why they need the instance
stopped.

## The greeter needs a last user

NosArch's SDDM theme logs in `userModel.lastUser`, with no username field. On a fresh instance nobody has logged in, so
it tries an empty name and fails. `vm login` writes SDDM's state file with the `nosarch` user and restarts the greeter
before typing the password.
