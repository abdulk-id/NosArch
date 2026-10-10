# Snap

NosArch can install and manage Snap packages. It is gated behind `packaging.snap`.
Packages are declared per module or listed in `user_packages.snap` and `user_packages.classic_snap`.

## Base snaps must never be removed

`snap list` reports the snaps snapd needs for itself (`core22`, `bare`, `snapd`, and any `kernel-*`) with `base` in
its Notes column. Diffing installed against declared would treat them as unwanted and remove them, which breaks every
other snap. The plugin filters them by both the notes column and the name, so a removal decision does not rest on one
column's wording.

## Confinement is one decorator, channel is part of every entry

A snap is declared with `@snap.snaps` or `@snap.classic_snaps` depending on its confinement, and each entry maps the
snap name to the channel it tracks. Confinement cannot be expressed as a flag in the name, so no declaration can
smuggle in an option.

Channels are whatever the publisher defines, so there is no list to validate against and no default to fall back on:
every entry states one, and it is always passed as `--channel`. Only the shape is checked, since a channel has to be a
single word that cannot read as a flag.

A snap cannot be both confined and classic. The plugin rejects snaps defined as both.

Names are the unit of comparison against `snap list`, which reports names only. Moving a snap between the two
declarations does not reinstall it, since it is already installed either way; flip the snap's revision to force that
when it matters. The same goes for changing the channel of an installed snap, which only `snap refresh --channel`
acts on.

## Classic confinement needs /snap

Snaps with classic confinement resolve their files under `/snap`, which the snapd package does not ship. Without it,
every classic install fails. `SnapModule` declares it through `symlinks()`.

Do not move this into a hook. `SnapModule` has `before_update`, `after_update`, `on_enable`, and `on_change`, and none of
them sit between the systemd step and the snap step, so a hook cannot guarantee the link is in place before the install
that needs it. `after_update` runs after every plugin step, which is too late on the run that matters.

## Enabling a unit does not start it

Decman's systemd plugin does not start a unit, so a declared unit starts at next boot. Snap needs it sooner as
`snap list` connects to `/run/snapd.socket`, which only accepts once `snapd.socket` is started, so on the run that
installs snapd every snap command fails with `cannot communicate with server`.

The plugin therefore starts the socket itself before listing. `snapd.socket` is socket-activated, so starting it is
enough to bring up the daemon on first connection. `snapd.apparmor.service` is a oneshot that only loads profiles once,
so it is started in the same call rather than left for the next boot, where snaps would run unconfined until then.

`systemctl is-active snapd.service` is not a substitute. snapd exiting after a few seconds of idleness is normal
standby behaviour, not a failure, so the daemon being inactive says nothing about whether the socket will serve.

This one cannot move into a module either, for the same reason as the symlink: no hook runs after systemd and before the
snap step.

## Refreshing is snapd's job

`snapd.timer` refreshes on its own schedule, so the plugin's `upgrade` flag is off by default. Turning it on makes every
apply run `snap refresh`, which duplicates that work.

## Turning it off

Disabling `packaging.snap` drops `SnapModule`, which means decman stops declaring `/snap` and removes it, and the AUR
step removes snapd. What snapd leaves behind is `/var/lib/snapd` and per-user app data in `~/snap`, which hold settings
and saves that exist nowhere else.

`SnapModule.on_disable` offers to delete them, and runs before the AUR step so snapd is still installed. Decman lifts
that function's source into a standalone script rather than calling it, so it can only use builtins and names imported
inside its own body: no module-level constants, no calls to anything defined at module level, and no reference to
`utils.*`. Decman validates this and refuses to register the module if the function reaches for anything else.

It stops `snapd.socket` before deleting anything, since the daemon holds squashfs mounts of its own.

The prompt appears once, on the run that disables Snap. Declining leaves the data in place, on the assumption that
`nosarch-package cleanup` can offer again later.
