# AppImages

NosArch installs AppImages with `nosarch-package`, the same script that installs Arch,
AUR, Flatpak and Homebrew packages. It replaced GearLever, which needed Flatpak on
every machine.

## Layout

AppImages are per-user. Installing one needs no sudo, and no install can reach another
user's copy.

| Path | What |
| --- | --- |
| `~/.local/share/appimages/<id>.AppImage` | The binary, mode `0755` |
| `~/.local/share/applications/nosarch-appimage-<id>.desktop` | The launcher entry |
| `~/.local/share/icons/hicolor/<size>/apps/nosarch-appimage-<id>.<ext>` | The icon |
| `~/.local/bin/<id>` | Symlink, for launching from a terminal |
| `~/.local/share/nosarch/appimages.list` | The registry |

`id` is a slug of the app's display name, lowercased with anything outside
`[a-z0-9._-]` replaced by a dash. Every path above is built from it, which is what lets
a removal delete exactly what the install created.

The registry is one tab-separated record per app:

```
id, display name, AppImage path, .desktop file, icon file
```

`tools/check_paths.py` does not cover any of this. None of these paths are declared by
a module, so there is nothing for that check to compare them against.

## Commands

```sh
nosarch-package install appimage [path...]      # no path -> asks for files
nosarch-package install appimage --confirm ...  # asks before each install
nosarch-package list                             # name, path, and whether the file is there
nosarch-package remove                           # AppImages appear in the normal list
```

`remove` mixes AppImages in with packages, tagged `[appimage]`. The preview shows the
`Name`, `Exec` and `Icon` lines of the generated entry rather than running the app.

There is deliberately **no update command**. An AppImage carries no version metadata
worth comparing, so there is no way to tell a new build from the current one. Move to a
newer version by installing the new file and removing the old entry.

## Installing

`nosarch-package install appimage` with no arguments opens a file dialog, which is also
what the `Install AppImage` entry in the packages menu runs. Passing paths skips it.

`--confirm` asks about each file first and installs only the ones that are confirmed, so
a declined file is skipped rather than treated as an error. It is a flag rather than a
separate command because the confirmation belongs to the install, and because the
desktop entry below needs it without any shell quoting of its own.

The install reads the app's own metadata rather than guessing from the filename:

1. `--appimage-extract` is run with glob patterns for `*.desktop` and the icon
   directories. A bare extraction would write the whole bundle, often hundreds of
   megabytes, into a tmpfs.
2. `Name`, `Icon` and `Categories` are read from the bundled `.desktop` file, and the
   icon it names is installed into hicolor under its real pixel size.
3. The bundled `.desktop` file is **adapted, not replaced**. It is the app's own entry and
   knows things nothing else can supply, so all of it is kept: `StartupWMClass` (without
   which no `app-windows/*.lua` rule can match the app), `MimeType`, `StartupNotify`, the
   `%U`/`%F` field codes, localized `Name[xx]`, `Keywords`, and any `[Desktop Action ...]`
   groups.

Four keys cannot survive being copied out, because each names something that exists only
while the AppImage is mounted:

| Key | Why | What happens |
| --- | --- | --- |
| `Exec` | Points at `AppRun` inside the bundle | Command token swapped for the stored path; arguments and field codes kept |
| `TryExec` | Same, and a launcher that cannot find it hides the entry | Dropped |
| `DBusActivatable` | `true` makes a launcher ignore `Exec` and D-Bus activate a service that is not there | Forced to `false` |
| `Icon` | The bundled name resolves only inside the mount | Rewritten to the name the icon was installed under |

Only the command token of `Exec` is replaced, so `Exec=AppRun %U` and
`Exec=AppRun --new-window` both keep their arguments, in the main group and in
`[Desktop Action ...]` groups alike.

A Type 1 AppImage, or a bundle whose entry does not pass `desktop-file-validate`, still
installs: the entry is generated from the filename instead, with no icon. The install
never fails just because metadata is missing. `desktop-file-utils` is not a package
NosArch requires, so without it a malformed bundled entry is used unchecked.

Re-installing the same app reuses its `id`, so the new binary replaces the old one
rather than piling up copies. An upstream that **renames** the app between releases gets
a new `id`, and its predecessor is then a separate entry to remove.

## The desktop entry

`nosarch-appimage-installer.desktop` is the default handler for `application/x-appimage`
and `application/x-iso9660-appimage` (see `utils/dotfile/mimeapps_list.py`), so
double-clicking an AppImage in a file manager offers to install it.

Its `Exec` is a single absolute path with `%F`, and nothing else:

```
Exec=/usr/local/bin/nosarch/nosarch-package install appimage --confirm %F
```

Both details are deliberate. The path is absolute because a relative one would depend
on the invoking program's working directory, which a file manager does not control. And
there is no `sh -c` wrapper: the desktop entry spec requires reserved characters and `$`
to be escaped inside `Exec`, and a shell one-liner long enough to confirm and install
each file needs all of them. Keeping the logic in the script keeps the entry to a
command that `desktop-file-validate` accepts.

## Reporting without a terminal

Installing is the one flow that can run with no terminal attached, because a desktop
entry or a menu can launch it detached, where `gum`'s output goes nowhere. Results fall
back to a `zenity` dialog when stdout is not a TTY, and are dropped when there is no
`zenity` either. Every other flow is terminal-only and keeps printing through `gum`.

## Trust

An AppImage is an unsigned executable. `--appimage-extract` runs it, so installing one
is a decision to run that code, and there is no signature for NosArch to check first.
This is inherent to the format rather than a property of this implementation.

## State outside the filesystem

Installed AppImages are not declared by any module, so decman does not converge them.
This is the same category as Flatpak installations and `yay`'s package database: state
that exists because a user acted, not because a module says so. Uninstalling means
`nosarch-package remove`, not a change to the repo.
