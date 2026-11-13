# Packages

## Foreign packages

AUR and custom packages are built by `aurbuilduser` and installed by root with `pacman -U`.

By default each build runs in a fresh chroot (`advanced.build_aur_in_clean_chroot`), so nothing installed on the host
leaks into a build. A chroot starts empty, so an AUR dependency has to be handed to it as a package file even when it
is installed on the host. Built packages are kept in `/var/cache/nosarch/packages` for that reason: without the cache,
every AUR dependency would be rebuilt whenever something depending on it is.

With the chroot off, builds run on the host. A build's dependencies are installed as dependencies first and removed
once nothing needs them.

AUR PKGBUILDs are offered for review before they run: the diff since the last reviewed commit, or every file the first
time. Custom packages are not, since they come from NosArch's own repository.

## Homebrew

- The homebrew step never untaps `homebrew/core` or `homebrew/cask`.
- Formula removal uses `brew leaves --installed-on-request`, so a formula that is present only as a dependency stays.

## Flatpak

- Enabling Flatpak adds the Flathub remote. `before_update` runs before pacman, so the run that first installs
  `flatpak` cannot add it. The pacman hook shipped by
  [`FlatpakModule`](../../nosarch/definition/modules/packaging/flatpak.py) covers that run.
- `on_disable` runs `flatpak uninstall --all` for the system and the user before it asks. Declining the prompt leaves
  the data directories, and the apps are already gone.

## Snap

- Removing a base snap breaks every other snap.
  [`snap.py`](../../nosarch/engine/steps/snap.py) and `snap_is_base` in
  [`snap.sh`](../../nosarch/dotfiles/system-root/usr/local/bin/util/package/snap.sh) each keep them, and the two checks
  differ, so a change to one leaves the other.
- Every snap entry states a channel. There is no default. The step compares names only, so a channel change, or a move
  between `@snap.snaps` and `@snap.classic_snaps`, keeps the snap that is already installed. Remove it and the next
  run installs the declared one, or run `snap refresh --channel` to move an installed snap. `snapd.timer` keeps
  refreshing the channel the snap already tracks.
- The snap step starts `snapd.socket` and `snapd.apparmor.service` before listing snaps. The systemd step only enables
  units, and no hook runs after snapd is installed and before the snap step. `snapd.apparmor.service` loads profiles
  once, so leaving it until the next boot leaves snaps unconfined until then. `snapd.service` dropping to inactive is
  the daemon's idle standby.

## Custom packages

- A custom package name ends in `-nosarch`. AUR helpers key off the name, so `cursor-cli` is taken to be the AUR
  package and replaced by it.
- `nosarch-package update` runs `paru -Syu`. Foreign packages stay as they are, so a version bump in NosArch-Packages
  reaches the system on the next apply run.

Declining a packaging module's `on_disable` leaves its data. `nosarch-package cleanup` offers those paths later, and
only while that method's library is absent.
[`cleanup.sh`](../../nosarch/dotfiles/system-root/usr/local/bin/util/package/cleanup.sh) and each module's `on_disable`
list the same paths.
