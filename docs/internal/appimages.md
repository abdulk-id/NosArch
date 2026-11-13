# AppImages

## Identity

There is no updater. The id is a slug of the display name, and the installed paths are built from it, so a newer file
of the same name replaces that install. An upstream rename gets a new id and leaves the previous install in place. A
name that slugs to nothing is stored as `appimage`, so those installs share one slot. See
[`appimage.sh`](../../nosarch/dotfiles/system-root/usr/local/bin/util/package/appimage.sh).

## Desktop entries

A bundle with no usable desktop entry still installs, from a generated entry. `desktop-file-validate` is best-effort:
`desktop-file-utils` is not a required package, so without it a malformed bundled entry is used unchecked.

When the bundle's entry has an `Icon=` line and no icon file was installed, the adapted entry still names
`nosarch-appimage-<id>`. The generated entry leaves `Icon` out.

## MIME handler

[`nosarch-appimage-installer.desktop`](../../nosarch/dotfiles/desktop-root/home/username/dot_local/share/applications/nosarch-appimage-installer.desktop)
handles `application/x-appimage` and `application/x-iso9660-appimage`. Its `Exec` is an absolute path with no shell.
A file manager does not control the working directory a relative path would use, and a `sh -c` wrapper would have to
escape the characters the desktop entry spec reserves.
