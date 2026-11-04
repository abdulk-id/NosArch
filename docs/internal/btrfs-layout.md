# Btrfs layout

NosArch expects the target system's Btrfs filesystem to have six subvolumes, mounted like this:

| Subvolume    | Mounted at              |
| ------------ | ----------------------- |
| `@`          | `/`                     |
| `@home`      | `/home`                 |
| `@log`       | `/var/log`              |
| `@pkg`       | `/var/cache/pacman/pkg` |
| `@swap`      | `/swap`                 |
| `@snapshots` | `/.snapshots`           |

The installer creates them and NosArch does not. `SystemModule.before_update` checks them with
`utils.btrfs_layout.verify` and stops the run when one is missing, rather than creating a substitute. This does not
apply to a root that is not Btrfs.

## Why `@swap` and `@snapshots` are not directories or nested in `@`

- **Snapshots:** Rolling `@` back replaces it with an older snapshot. A `.snapshots` subvolume nested in `@` would be
  replaced with it, and the snapshots would be gone when they are needed.
- **Swapfile:** A subvolume holding an active swapfile cannot be snapshotted. A subvolume of its own keeps `@`
  snapshottable.

## The snapshot directory is `/.snapshots`

Snapper hardcodes `.snapshots` as the directory it keeps a subvolume's snapshots in, so `@snapshots` is mounted at
`/.snapshots`. A mount at `/snapshots` would not be found.
