# Packages

NosArch is responsible for managing packages on the system. The kinds of packages include:

- Arch and AUR,
- Homebrew (via NosArch's own `plugins/homebrew.py`, if enabled by user),
- Flatpak (system and per-user),
- and custom pacman packages ([Custom Packages](#custom-packages)).

## Declaring

Each plugin exposes decorators. A module method annotated with one returns the set (or dict, for user-scoped kinds) of
packages that module wants:

```python
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
```

## Tracking package changes

Decman provides the `Store` in `on_change` hooks from which package changes can be tracked. But the store only holds
the current run's entries per plugin, and a hook still has to know each plugin's store key and per-user shape to make
sense of it.

`utils/change_tracker.py`'s `ChangeTracker` makes tracking package changes easy. It snapshots every plugin's entries
in `before_update`, diffs them against what's there after, records which packages were added or removed on a run,
across every plugin (pacman, AUR, custom, flatpak, homebrew). It normalizes user-scoped kinds into a flat set of
names. `on_change` hooks only need `package_changed(...)` instead of reaching into the store itself.

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
`"flatpak"`, `"flatpak_user"`, `"brew_formula"`, `"brew_cask"`, `"brew_tap"`) to a set of names. User-scoped kinds are
recorded as `"<user>:<pkg>"`. A module enabled for the first time sees everything as added.

`ChangeTracker` can also track `"systemd"` and `"systemd_user"` units.

## Custom packages

Documentation on custom packages lives at `docs/internal/custom-packages.md`.
