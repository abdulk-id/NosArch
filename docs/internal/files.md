# Files

NosArch is responsible for deploying dotfiles to the system. The dotfiles all live under `/dotfiles`, with each
[module](modules.md) keeping a separate mirrored-root. For example: files managed by the desktop module are stored in
`/dotfiles/desktop-root/...`, and dev module's files in `/dotfiles/dev-root/...`.

Hidden files and directories are stored with a `dot_` prefix (For example: `dot_bashrc`, `dot_config/hypr/`)

`dotfiles/unused-config/` holds currently unused config stored for if needed later. For example: NosArch is still
exploring options for launchers. Vicinae was tried before and its config lives there. When the launcher has been
finalised, unused launchers' config will be removed completely.

## Every file is declared individually

Decman offers `Directory()`, which deploys a whole source tree. NosArch does not use it. Every managed file is named
explicitly.

This is more verbose, and this is deliberate:

- **A module is a manifest**: Reading a module tells you every path that module deploys to. With directories you would
  have to read the repo tree instead, and the two can drift.
- **Nothing deploys by accident:** A `Directory()` ships whatever is in the source tree, so an editor backup, a `.orig`
  from a merge, or a half-finished file lands on the system the moment it is saved. An undeclared file in `dotfiles/`
  is inert.
- **Settings are per file, not per tree:** `Directory` applies one `owner`, one `permissions` and one `bin_files` to
  everything it walks (`core/fs.py:429`). That cannot express a directory holding both templated text and binaries.
    - The plymouth theme (system module) is the concrete case for this. `bin_file=True` disables variable substitution
      (`core/fs.py:163`), so a single directory declaration would have forced a choice between corrupting the PNGs and
      leaving `%ACCENT%` unsubstituted in `nosarch.script`

The only exception is the wallpapers directory in `ThemingModule`, because each theme can have a different number of
wallpapers, and they don't have fixed names.

## Declaring

Use the helpers in `utils/paths.py` rather than constructing `File` by hand. They derive the source path from the
target path, which keeps the two in step and removes common typos.

```python
self._dotfiles: utils.paths.Dotfiles = utils.paths.Dotfiles("../dotfiles/system-root")
self._userhome_dotfiles: utils.paths.UserhomeDotfiles = utils.paths.UserhomeDotfiles(
    "../dotfiles/system-root", _username
)
```

`Dotfiles` takes absolute system paths. `UserhomeDotfiles` takes paths relative to the user's home, applies the `dot_`
translation, and sets the owner to that user:

```python
files.update(
    self._dotfiles.files(
        "/etc/sysctl.d/99-memory-parameters.conf",
        "/etc/mkinitcpio.conf",
    )
)

files.update(
    self._userhome_dotfiles.files(
        "/.bashrc", "/.config/yay/config.json"
    )
)
```

Keyword arguments (such as `permissions`, `bin_file`) apply to every path in the call, so group by what they share.

### Manually declaring files

Construct `File` directly when there is no source file to point at (such as when content is generated at run time).
(For example: `/etc/conf.d/wireless-regdom` in system module)

Only use when strictly necessary.

### Variables

`file_variables()` returns substitutions applied to every text file in the module:

```python
@override
def file_variables(self) -> dict[str, str]:
    return {
        "%LUKS_UUID%": utils.dotfile.luks_uuid.get_luks_uuid(),
        "%USER%": _username,
    }
```

Substitution applies to any text file, whether it is declared with `source_file=` or `content=`. Setting `bin_file=`
to true skips it (`core/fs.py:45`).

## Removal is automatic

Deleting a declaration deletes the file from the target system. decman keeps every path it has written to in
`store["all_files"]`, and on each run removes those that no longer appear in any module (`core/file_manager.py:113`).
Therefore, there is no uninstall step or cleanup migration.

## Tracking file changes

Decman does not provide a way to track which files were just updated on a run. To track this for applying changes to
the system later ([Applying changes](#applying-changes)), declarations should go through `utils/change_tracker.py`,
which subclasses decman's `File`, `Directory` and `Symlink` to record every path actually written:

```python
self._tracker: utils.change_tracker.ChangeTracker = utils.change_tracker.ChangeTracker()
```

> - A module only needs one `ChangeTracker`, tracking both files and [package](packages.md#tracking-package-changes) changes.
> - Each module should carry its own tracker so it sees only its own files.

Then `tracked_files()` instead of `files()` (from `/nosarch/utils/paths.py`):

```python
files.update(
    self._dotfiles.tracked_files(
        self._tracker,
        "/etc/sysctl.d/99-memory-parameters.conf",
        #...
    )
)
```

Nothing is recorded during `--dry-run`.

The same tracker also records package and unit changes; see
[Tracking packages](packages.md#tracking-packages).

## Applying changes

Sometimes updating a file requires running a command to apply the changes to the system.

For example: `systemd-sysctl` read `/etc/sysctl.d/` once at boot. Changes can be applied live by running
`sysctl --system`.

To apply changes, check which files were changed ([Tracking file changes](#tracking-file-changes)) and take action accordingly
in `on_change` hooks.

### Ordering

1. **`systemctl daemon-reload` first**: Everything below it reloads or restarts a unit, and those act on the manager's
   loaded state rather than on what is now on disk.
2. **`systemctl daemon-reexec` next**:, for manager-level defaults.
3. Everything cheap and independent, in any order.
4. **`limine-mkinitcpio` second last:** It is a slow step (~30 seconds, doubled when the LTS kernel is enabled). If
   there are several triggers calling this, gather them rather than rebuilding per trigger.
5. **The reboot notice last**: For everything that can not be applied live.

### Hooks must be idempotent

`on_change` fires once per module when **anything** in that module changed, not once per file. Being invoked is
therefore not proof that the particular file a hook cares about is what changed. The hook must check which files
changed itself ([Matching paths](#matching-paths)).

`on_change` also has no memory of having fired before, so a hook must tolerate running again on a later, unrelated
change. It is **not** a one-time migration.

#### Matching paths

Test with `os.path.commonpath`, not `str.startswith`, so path boundaries are respected.
For example: `/etc/systemd/system` must not match `/etc/systemd/system.conf.d/`.

```python
def changed_files_in(*target_dirs: str) -> bool:
    for target_dir in target_dirs:
        target_path: str = os.path.abspath(target_dir)

        if any(os.path.commonpath([p, target_path]) == target_path for p in changed_files):
            return True
    return False
```

### Reboot-only changes

Some files have no safe live path. For example: applying **zram** config changes means `swapoff` on an active device
holding compressed pages, which can OOM the machine under memory pressure.

Prompt with `decman.core.output.prompt_confirm`, guarded on `sys.stdin.isatty()` so a scripted install does not hang.

`on_change` is skipped under `--dry-run` (`app.py:343`), so hooks need no dry-run handling of their own.

## Gotchas

- **decman's own `daemon-reload` is not enough**: It runs only when the _set_ of enabled units changes
  (`plugins/systemd.py:176`). Editing the body of a unit without changing which units are enabled reloads nothing.
- **`udevadm control --reload` only loads rules, it does not run them**: Rules execute on device events, and devices
  present since boot do not fire one, so a reload alone leaves new rules dormant. Pair it with
  `udevadm trigger --subsystem-match=power_supply --action=change`.
    - Keep `udevadm trigger` scoped to the subsystems that NosArch has udev rules for (For example: `power_supply`).
      A bare `udevadm trigger` replays events for every device, which can rebind drivers and re-probe storage.
- **`systemd-tmpfiles --remove` is not scoped to managed files**: It deletes every path marked `r`/`R` across all
  tmpfiles configs on the system. `--clean` should be used.
