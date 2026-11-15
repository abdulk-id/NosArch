# Manual Installation

NosArch can be installed manually using the arch linux ISO and archinstall.

## Installing Vanilla Arch Linux

1. Download the Arch Linux ISO, put it on a USB stick and boot off the stick (remember to turn off Secure Boot).
2. If you're on wifi, start by running `iwctl`, then type `station wlan0 scan`, then `station wlan0 connect <tab>`,
   pick your network, and enter the password. If you're on ethernet, you don't need this.
3. Run archinstall and pick these options (leave anything not mentioned as-is):

| Section                        | Option                                                                           |
| :----------------------------- | :------------------------------------------------------------------------------- |
| Disk configuration             | Partitioning > Default partitioning layout > Select disk (with space + return)   |
| Disk > File system             | `btrfs` (default structure: yes + add `@swap` and `@snapshots`; use compression) |
| Disk > Disk Encryption         | Encryption type: LUKS + Encryption password + Partitions (select the one)        |
| Hostname                       | Give the computer a name                                                         |
| Bootloader                     | Limine                                                                           |
| Authentication > Root password | Set yours                                                                        |
| Authentication > User account  | Add a user > Superuser: Yes > Confirm and exit                                   |
| Applications > Audio           | pipewire                                                                         |
| Network configuration          | Use Network Manager (default backend)                                            |
| Timezone                       | Set yours                                                                        |

In Disk > File system, ensure that there are six btrfs subvolumes configured:

- `@` mounted to `/`
- `@home` mounted to `/home`
- `@log` mounted to `/var/log`
- `@pkg` mounted to `/var/cache/pacman/pkg`
- `@swap` mounted to `/swap` (not added by default structure)
- `@snapshots` mounted to `/.snapshots` (not added by default structure)

## Installing NosArch on top of Arch Linux

After Arch Linux has been installed, reboot and log in as the user you set up. Install `curl` if the machine does
not have it, then install the latest release:

```sh
curl -fsSL https://github.com/abdulk-id/NosArch/releases/latest/download/install.sh | sh
```

This installs the `nosarch` package and writes `~/.nosarch_config.json` with your username, the only setting NosArch
requires. An existing config is kept. It does not apply NosArch. To choose what NosArch sets up, add
settings to the config first (see [`config.schema.json`](../../config.schema.json)), then apply:

```sh
nosarch-apply --dry-run  # only shows what would be applied
nosarch-apply            # applies NosArch setup
```

Installing or upgrading the package never applies it. After an upgrade, run `nosarch-apply` again.

NosArch is alpha. Every version is `0.x`, and an upgrade can need changes to `~/.nosarch_config.json` or to what
NosArch manages. To install a dev build or one exact version instead, see
[releasing](../operations/release.md#installing).
