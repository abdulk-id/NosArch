# Packages

NosArch is responsible for managing packages on the system. The kinds of packages include:

- Arch and AUR,
- Homebrew (via NosArch's own `plugins/homebrew.py`, if enabled by user),
- Flatpak (system and per-user, if enabled by user),
- Snap (via NosArch's own `plugins/snap.py`, if enabled by user. See [Snap](snap.md)),
- Custom pacman packages ([Custom Packages](custom-packages.md)), built from
  [NosArch-Packages](https://github.com/abdulk-id/NosArch-Packages).

## Declaring

Each plugin exposes decorators. A module method annotated with one returns the set (or dict, for user-scoped kinds and
for kinds that carry per-package detail) of packages that module wants:

```python
from decman.plugins import aur, flatpak, pacman
from plugins import homebrew, snap

@pacman.packages
def arch_pkgs(self) -> set[str]:
    return set(self._user_config.get_str_list("user_packages.arch"))

@aur.packages
def aur_pkgs(self) -> set[str]:
    return set(self._user_config.get_str_list("user_packages.aur"))

@flatpak.packages
def flatpak_pkgs(self) -> set[str]:
    return set(self._user_config.get_str_list("user_packages.flatpak"))

@flatpak.user_packages
def flatpak_user_pkgs(self) -> dict[str, set[str]]:
    return {self._username: set(self._user_config.get_str_list("user_packages.flatpak_user"))}

@homebrew.formulae
def brew_formulae(self) -> set[str]:
    return set(self._user_config.get_str_list("user_packages.homebrew_formulae"))

@snap.snaps
def snap_pkgs(self) -> dict[str, str]:
    return self._user_config.get_str_dict("user_packages.snap")
```

A gated packaging method's declarations return nothing while its key is false, so a config listing packages for a
disabled method is inert rather than an error.

## Tracking package changes

Decman gives each `on_change` hook the `Store`, but the store only holds the current run's entries per plugin, and a
hook still has to know each plugin's store key and per-user shape to make sense of it.

`ChangeTracker` (`utils/change_tracker.py`) does that work: it snapshots every plugin's entries in `before_update`,
diffs them after, and records which packages were added or removed across every plugin (pacman, AUR, custom,
flatpak, homebrew), normalizing user-scoped kinds into a flat set of names. Hooks just call `package_changed(...)`.

```python
self._tracker: utils.change_tracker.ChangeTracker = utils.change_tracker.ChangeTracker()
```

> - A module only needs one `ChangeTracker`, tracking both [files](files.md#tracking-file-changes) and package changes.
> - Each module should carry its own tracker so it sees only its own packages.

Then snapshot the store in `before_update` and diff in `on_change`:

```python
@override
def before_update(self, store: Store) -> None:
    self._tracker.snapshot_packages(store, self.name)

@override
def on_change(self, store: Store) -> None:
    self._tracker.diff_packages(store, self.name)

    if self._tracker.package_changed("mise", kinds=("pacman",)):
        ...

    if self._tracker.package_changed("visual-studio-code", kinds=("brew_cask",)):
        ...

    if self._tracker.package_changed(f"{self._username}:org.mozilla.firefox", kinds=("flatpak_user",)):
        ...
```

`self._tracker.added_pkgs` and `self._tracker.removed_pkgs` map each kind (`"pacman"`, `"aur"`, `"custom"`,
`"flatpak"`, `"flatpak_user"`, `"brew_formula"`, `"brew_cask"`, `"brew_tap"`, `"snap"`, `"snap_classic"`) to a set of
names. User-scoped kinds are
recorded as `"<user>:<pkg>"`. A module enabled for the first time sees everything as added.

`ChangeTracker` can also track `"systemd"` and `"systemd_user"` units.
