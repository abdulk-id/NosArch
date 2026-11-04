# Test VM

`vm/vm` runs NosArch in a QEMU virtual machine, so definition code can be applied and tested without touching real
hardware. Every command works headless and needs no root on the host, so agents can drive it themselves. Inside the VM
they have root.

The VM is built to match what the definition code expects of a target system: UEFI, one LUKS container, a Btrfs
filesystem with the six [subvolumes](../internal/btrfs-layout.md), and Limine with the entries `limine-entry-tool`
generates. Why it is built that way, and what traps that avoids, is in [Test VM internals](../internal/vm.md).

## Requirements

On the host: `qemu-full` (or `qemu-system-x86` with `edk2-ovmf`), `socat`, `openssh`, `curl`, `libarchive`
(`bsdtar`), `e2fsprogs`, `git`. The user needs access to `/dev/kvm` and `/dev/vhost-vsock`.

## Setup

```sh
vm/vm create
```

This installs the base system onto a virtual disk from the Arch ISO, builds decman and the Limine tooling inside it, and
boots the result once to check it. It takes about 9 minutes, and it is only done once.

The ISO is kept in `vm/`, which git ignores apart from the scripts. If `vm/` has no `archlinux-*-x86_64.iso`, `create`
downloads the latest one and verifies its checksum. An ISO that is already there is used as it is, even when a newer
one exists. Delete it to get the latest. Every checkout has its own `vm/`, so a new worktree downloads the ISO again
when it runs `create`.

The base image lives in `~/.local/share/nosarch-vm/` (override with `NOSARCH_VM_HOME`), shared by every checkout.
`vm/vm create --force` rebuilds it, and deletes every instance.

## Using it

```sh
vm/vm start              # boot the instance, creating it from the base image if needed
vm/vm apply --dry-run    # copy this checkout into the VM and dry-run decman there
vm/vm apply              # the same, for real
vm/vm ssh                # root shell. `vm/vm ssh COMMAND` runs one command, `--user` runs it as nosarch
vm/vm screenshot         # PNG of the screen, prints the path
vm/vm reset              # throw the instance away and start a fresh one
```

`vm/vm help` lists everything. A few things worth knowing:

- **The instance is a clone of the base image.** Starting one costs almost no disk, and `reset` is a second's work.
- **`apply` syncs first.** It copies the checkout, including uncommitted changes and untracked files that are not
  ignored, to `/home/nosarch/NosArch`, replacing what was there. Then it runs `tools/apply` as the `nosarch` user.
- **The config is `/home/nosarch/.nosarch_config.json`.** The default sets only the user. Change settings with
  `vm/vm ssh --user`.
- **Take a checkpoint before something risky.** `vm/vm checkpoint NAME` saves the disk, and `vm/vm restore NAME`
  brings it back. Both stop the instance, and `vm/vm start` boots it again.
- **A first apply takes about half an hour,** most of it downloading and building the desktop's packages.
- **Several VMs can run at once** with `--name NAME` (or `NOSARCH_VM_NAME`). Give each agent its own, since instances
  share nothing but the base image. Each uses 6 GiB of memory by default (`NOSARCH_VM_MEMORY`, in MiB).
- **Changes that need a reboot, or a login, do not take effect on their own.** `vm/vm reboot` reboots and waits for
  the VM to accept SSH again. The firewall and the display manager, for example, only start then.
- **The screen is reachable without a window.** `screenshot` saves it, `type` and `key` drive the keyboard, and
  `vm/vm login` logs the `nosarch` user in at the display manager once an apply and a reboot have brought it up.
  `vm/vm start --gui` opens a window instead.

## What the VM does not cover

- Real hardware: GPU drivers, firmware vendors, laptop and battery paths (the VM reports a desktop chassis), Secure
  Boot, and hibernating to the swapfile.
- Anything that depends on how your actual machine was installed. The base image is a plain Arch install made the way
  `vm/` does it, which may differ from your machine's.
- Software rendering only: a screenshot shows what the VM draws, which is not how it looks on a GPU.

## When something goes wrong

- **`vm start` never gets SSH.** `vm/vm screenshot` and `vm/vm console` show where boot stopped. A firmware crash
  is reported as one.
- **`vm create` fails.** The installer's output is in `~/.local/share/nosarch-vm/base-build/serial.log`. A failure while
  provisioning leaves the instance `create-provision` for you to look at. Delete it with
  `vm/vm --name create-provision destroy`.
- **The instance is in a bad state.** `vm/vm reset`.
