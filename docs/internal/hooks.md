# Hooks

## Applying a change

Request the apply from `on_change`. Log out and reboot through the request too: the engine offers them after the hooks
return, from [`nosarch/engine/session.py`](../../nosarch/engine/session.py), and doing either inside the hook ends the
run.

The call is once per module, for anything that module declared, so check which path changed. The body has to be safe
to run again: a later change in the same module calls it, and a run that stops inside the hook hands the same change
to the next one. The change is dropped when the hook returns, so a failed apply command is not requested again.

The systemd step's `daemon-reload` rereads unit files and does not restart a running service. Request that restart, or
the unit's own reload, from `on_change`.

Session commands go through [`nosarch/utils/session.py`](../../nosarch/utils/session.py). A real run is root, and root
has no Wayland session.

[`nosarch/utils/apply.py`](../../nosarch/utils/apply.py) runs requests in a fixed order, not the order modules
registered them. `daemon-reload` is before anything that restarts a unit. Session commands follow the root ones.
Initramfs runs once, after those, because `limine-mkinitcpio` takes about half a minute and twice that with the LTS
kernel. A command that fails is reported, and the later commands still run.

## Tracking changes

`on_change` hears which packages and units a module added or removed since that module's own declarations on the last
run of the step for that kind. A package another module also declares, or one the user installed by hand, still counts
as added for the module that starts declaring it. `flatpak_user` and `systemd_user` are recorded as `"<user>:<name>"`.
A module enabled for the first time sees everything it declares as added.

A kind is diffed on the run whose step for it ran. A package change made under `--only files` shows up on the next
full run.

## Module names and hook order

`module.name` is the key for that module in the state: the files it applied, its declarations from the last run, and
changes `on_change` has not seen. Renaming it is handled as the old module disappearing and a new one appearing. The
old name is not registered, so `on_disable` does not run and the run warns that the module no longer exists.
Declarations and unseen changes stored under the old name are dropped. The new name has nothing on record, so
`on_enable` runs and `on_change` sees every package and unit as newly added. Files are matched by path, so the same
paths stay in place and the rename is not reported as a file change.

Hooks in a phase run in the order modules were added. `on_disable` follows `state.enabled_modules`, the order each
module was first enabled.

`ApplyModule` stays last in `source.py`. Its `after_update` runs the commands other modules queued from `on_change`,
and `after_update` follows add order, so a module registered after it would run its own `after_update` after those
commands.
