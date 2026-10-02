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

Only track what a hook reacts to. A declaration with no action to take on change (a config its owner reads once at
start, or a script run fresh on each use) should stay on `files()`, because an untracked declaration is one less
thing to keep in step, and a trigger nobody reads only invites false positives.

A tracker sees only its own module's files, so a directory trigger in one module can never fire for another module's
declarations. Ownership of a directory's trigger belongs to whichever module actually writes there.

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

### Prompting ends the run

Logging out or rebooting destroys the session decman is itself running in, so acting on a pending change from inside a
hook kills the run partway through. That is worse than it looks, because applies are **edge-triggered**: a file is
recorded only when it actually differed (`core/fs.py:124`), so an apply that never runs is not queued for later. It is
simply lost, and no later run will notice the change again.

It also takes the store down with it. `Store.save()` runs in `__exit__` (`core/store.py:49`), which is after every hook,
so a run that dies mid-prompt leaves no record of `enabled_modules`, `all_files` or the per-module package sets. The
next run then believes every package, unit and file is newly added.

So a hook never acts on the change. It records it:

```python
utils.session_changes.defer(store, "reboot", "ZRAM configuration")
```

`tools/apply` is what offers the action, after decman has exited. That is the only point where every `on_change` and
`after_update` has finished and the store is on disk, and it does not depend on where a module sits in the registration
order. `tools/apply` reads the store, prompts once, and acts.

### The notice belongs inside, the prompt belongs outside

`defer` records the change, and the hook **also prints its own notice**. That is deliberate: running `decman` directly
still informs the user, it just cannot offer the action. Moving the notice out to the wrapper would mean the information
exists only when the wrapper is used.

`utils.session_changes.reset()` runs from a `before_update` hook, so each run reports only what it deferred itself. Any
module can do this reset, because `before_update` precedes every `on_change` for every module (`app.py:199-200`). That
is the one thing that may rely on hook order, and it relies on the *phase*, not on a module's position.

### Session-scoped changes

Applying a change to a running desktop often means running a command that only the graphical session can reach.
`hyprctl`, `waybar` and the rest need the session's Wayland socket, its Hyprland instance signature and its bus.
decman runs as root, and root has none of those, so these applies go through `utils/session.py`.

It finds the active graphical session with `loginctl`, reads that session's environment out of
`systemctl --user -M <user>@ show-environment`, and runs the command as the session's owner. Reading the environment
back is exact because Hyprland's autostart runs `systemctl --user import-environment`; reconstructing
`WAYLAND_DISPLAY` or the instance signature would be a guess, so `run_in_session()` skips the action instead of
acting on one. Report skipped actions to the user rather than dropping them, since they still apply on next login.

Session applies are best-effort by nature: pass `check=False`, so a failed reload warns instead of failing the run.
`utils/session.py` does this for every command it runs, and returns `False` when there is nothing to run in.

## Path checking

Dotfiles can reference each other by path (For example: a unit file points at a script, a udev rule points at a helper
binary). Nothing keeps those references in sync with the modules that actually deploy the files, so a rename or a move
can leave a reference pointing at a path nothing deploys any more. `tools/check_paths.py` scans every dotfile for
paths under `/usr/local/bin` or `/usr/lib/nosarch`, and fails if any of them isn't a path some module actually
declares. This check is ran on every invocation of decman.

It checks the whole of `/usr/local/bin` and `/usr/lib/nosarch`, not just the subdirectories in current use, so a check
like this only helps if the referenced path is spelled correctly in the first place. For example, a reference to
`/usr/local/bin/uti/foo`, a typo for `/usr/local/bin/util/foo`, is a path under `/usr/local/bin` too, so the checker
still looks for it.

Manual `File` declarations ([Manually declaring files](#manually-declaring-files)) are not checked.

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
- **systemd output parsed in a hook needs `pty=False`**: On a terminal, systemd colorizes `loginctl` and `systemctl`
  output, and the escape codes land inside the fields being parsed.
- **`systemctl --user -M <user>@` fails when the user manager is not running**: For example when applying from a TTY
  or during a fresh install. Pass `check=False` rather than guarding every call site.
- **Restart a unit the user may have turned off with `try-restart`**: `restart` would start a timer the user had
  disabled (`nosarch-eyesight-reminder.timer` is enabled by default, but a hook cannot assume that stays true).
- **Desktop daemons mostly have no reload request**: `swaync-client --reload-config`/`--reload-css` and waybar's
  `SIGUSR2` are the exceptions. `hyprpaper`, `hyprsunset` and `hypridle` read their config once, at start, and
  `hyprctl` has no request for them either, so they have to be restarted. Relaunch each with the command Hyprland's
  autostart uses, or the session comes back with a different process layout than the user expects.
- **`hyprctl reload` re-applies monitors**: Pass `config-only` when only the config changed. `hyprmoncfgd` owns the
  monitor layout, and a full reload fights it.
- **waybar's stylesheet needs no reload**: `reload_style_on_change` is set in its config. Its `config.jsonc` does.
- **Ghostty has no `+reload-config` action**: A new window picks the config up, so there is nothing to apply.
- **`hyprlock`'s config needs no apply at all**: `nosarch-lock-helper.sh` spawns a fresh hyprlock for every lock.
- **`pkill` exits non-zero when the process is not running**: A session daemon is often absent (install time, a TTY,
  the user closed it). Let the kill fail and let the relaunch decide the exit code, or every such run warns.
