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
    return set(self._user_config.get_str_list("packaging.arch.install-packages"))

@aur.packages
def aur_pkgs(self) -> set[str]:
    return set(self._user_config.get_str_list("packaging.aur.install-packages"))

@flatpak.packages
def flatpak_pkgs(self) -> set[str]:
    return set(self._user_config.get_str_list("packaging.flatpak.install-packages"))

@flatpak.user_packages
def flatpak_user_pkgs(self) -> dict[str, set[str]]:
    return {self._username: set(self._user_config.get_str_list("packaging.flatpak.install-user-packages"))}

@homebrew.formulae
def brew_formulae(self) -> set[str]:
    return set(self._user_config.get_str_list("packaging.homebrew.install-formulae"))

@snap.snaps
def snap_pkgs(self) -> dict[str, str]:
    return self._user_config.get_str_dict("packaging.snap.install-snaps")
```

A gated packaging method's declarations return nothing while its key is false, so a config listing packages for a
disabled method is inert rather than an error.

## Flathub

Enabling Flatpak adds the system-wide Flathub remote. `flatpak install` and the flatpak plugin search configured
remotes, so a machine with the runtime and no remote has nothing to install.

`FlatpakModule.before_update` adds the remote when `flatpak` is already on `PATH`. `before_update` runs before
pacman, so the run that first installs the `flatpak` package cannot add the remote there. The module also ships
`/etc/pacman.d/hooks/10-flatpak-flathub.hook`, which runs the same `flatpak remote-add --if-not-exists` at the end of
that transaction, before the flatpak plugin installs apps. A remote the user already added under the name `flathub`
is left alone.

## The `nosarch-package` CLI

One script, `/usr/local/bin/nosarch/nosarch-package`, with a library per packaging method under
`/usr/local/bin/util/package/`. A library defines a set of functions named `<method>_<verb>`, and the script dispatches
by name rather than by a table, so a method decides for itself which verbs it has:

| Verb                     | Purpose                                           |
| ------------------------ | ------------------------------------------------- |
| `<method>_install`       | interactive install                               |
| `<method>_update`        | update                                            |
| `<method>_entries`       | one tab-separated row per removable item          |
| `<method>_remove`        | remove the selected items                         |
| `<method>_remove_unused` | clean up leftovers                                |
| `<method>_available`     | whether this machine can use the method right now |
| `<method>_summary`       | one line for the help output                      |

A method with nothing to do for a verb omits it. AppImages have no `_update`, because an AppImage carries no version
metadata. Snap has no `_update`, because `snapd.timer` owns refresh. A method that defines no `_available` is always
usable, which is why Arch and AUR do not.

The user-facing shape is:

```sh
nosarch-package install <method>   # install needs a method, so browsing stays inside one ecosystem
nosarch-package update             # runs every method's update, skipping methods without one
nosarch-package remove             # one list across every method
nosarch-package remove-unused      # runs every method's cleanup
nosarch-package cleanup            # deletes data a disabled method left behind
nosarch-package <method> <verb>    # commands only one method has, like `appimage list`
nosarch-package list-methods       # the install methods this machine can use, one per line
```

Arch and AUR are defined in the main script rather than in a library. They are the core of the system and are always
present, so there is nothing to gate them on.

`remove` is the one command that cannot be delegated, because it merges every method's rows into a single fzf picker and
then hands each method its own rows back. The fzf preview is built from `PREVIEW_CASES`, which each library appends to
while being sourced: fzf runs `--preview` in a shell of its own, where no sourced function is visible, so the case arms
are text rather than calls.

## `cleanup`, and why it is not a library

`cleanup` deletes data a disabled method left behind. Each module's `on_disable` offers to delete the same data on the
run that disables the method, and declining leaves it behind, so this is the way back to that offer. It is shipped by
`SystemModule` rather than by a packaging module because it has to stay available after the module is gone.

A method shows up only while its library file is absent, since a missing library is what says its module is disabled.
While the module is enabled the data is in use, so nothing is ever offered for it. The leftover paths are read from the
same `_<method>_leftovers` helper that lists them, so a path added to one is deleted by the other.

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
