# Files

NosArch is responsible for deploying dotfiles to the system. The dotfiles all live under `/dotfiles`, with each
[module](modules.md) keeping a separate mirrored-root. For example: files managed by the desktop module are stored in
`/dotfiles/desktop-root/...`, and dev module's files in `/dotfiles/dev-setup-root/...`.

Hidden files and directories are stored with a `dot_` prefix (For example: `dot_bashrc`, `dot_config/hypr/`)

`dotfiles/unused-config/` holds currently unused config stored for if needed later. For example: NosArch is still
exploring options for launchers. Vicinae was tried before and its config lives there. When the launcher has been
finalised, unused launchers' config will be removed completely.

## Every file is declared individually

The engine offers `Directory()`, which deploys a whole source tree. NosArch does not use it. Every managed file is named
explicitly.

This is more verbose, and this is deliberate:

- **A module is a manifest**: Reading a module tells you every path that module deploys to. With directories you would
  have to read the repo tree instead, and the two can drift.
- **Nothing deploys by accident:** A `Directory()` ships whatever is in the source tree, so an editor backup, a `.orig`
  from a merge, or a half-finished file lands on the system the moment it is saved. An undeclared file in `dotfiles/`
  is inert.
- **Settings are per file, not per tree:** `Directory` applies one `owner`, `permissions` and `bin_files` to all files
  it walks. That cannot express a directory holding both templated text and binaries.
    - Example: The plymouth theme (system module). `bin_file=True` disables variable substitution so a single directory
      declaration would mean corrupting the PNGs or leaving `%ACCENT%` unsubstituted in `nosarch.script`

Exception: The wallpapers directory in `ThemingModule`, because each theme can have a different number of wallpapers,
and they don't have fixed names.

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
to true skips it. A module with no variables copies every file byte for byte, which is how the theme deploys its
wallpapers without marking them binary.

## Removal is automatic

Deleting a declaration deletes the file from the target system. The engine records every path each module deployed,
and on each run removes those no module declares any more. Therefore, there is no uninstall step or cleanup migration.

Two modules declaring the same path is an error rather than a silent override, so the dry run catches it.

## Applying changes

Sometimes updating a file requires running a command to apply the changes to the system.

For example: `systemd-sysctl` read `/etc/sysctl.d/` once at boot. Changes can be applied live by running
`sysctl --system`.

A module's `on_change(changes)` hook gets every path the run wrote or removed for that module, including a change of
mode or owner, and the packages and units it added or removed. Check what changed and request the apply:

```python
@override
def on_change(self, changes: engine.Changes) -> None:
    if changes.files_changed_in_dirs("/etc/sysctl.d"):
        utils.apply.apply_sysctl()
```

`files_changed_in_dirs` compares path components, not prefixes, so `/etc/systemd/system` does not match
`/etc/systemd/system.conf.d/`.

### Ordering

1. **`systemctl daemon-reload` first**: Everything below it reloads or restarts a unit, and those act on the manager's
   loaded state rather than on what is now on disk.
2. **`systemctl daemon-reexec` next**: for manager-level defaults.
3. Everything cheap and independent, in any order.
4. **`limine-mkinitcpio` second last:** It is a slow step (~30 seconds, doubled when the LTS kernel is enabled). Hooks
   request it with `utils.apply.rebuild_initramfs()`, and `ApplyModule` runs it once.
5. **The reboot notice last**: For everything that can not be applied live.

### Hooks must be idempotent

`on_change` runs once per module when **anything** in that module changed, not once per file. Being invoked is
therefore not proof that the particular file a hook cares about is what changed. The hook must check which files
changed itself.

A hook can also see a change twice. Changes are saved before the hooks run and cleared only once the module's hook
returns, so a run that stops partway hands them to the next run rather than losing them: by then the file is in place
and nothing else would notice it changed. A hook is therefore **not** a one-time migration, and must tolerate running
again.

### Reboot-only changes

Some files have no safe live path. For example: applying **zram** config changes means `swapoff` on an active device
holding compressed pages, which can OOM the machine under memory pressure.

No hook runs during a dry run, so hooks need no dry-run handling of their own.

### Prompting ends the run

Logging out or rebooting destroys the session the run is itself in, so a hook never acts on such a change. It requests
it:

```python
utils.apply.request_reboot("ZRAM configuration")
```

The engine lists those requests and offers the action as its very last step, once every hook has finished and the
state is saved. Declining is fine: the changes apply on the next login anyway.

Every requested command runs. A command that fails is reported, and the commands after it still run, including the
logout and reboot notice. The failed command is not tried again on the next run: the file that requested it is already
saved.

### Session-scoped changes

Applying a change to a running desktop often means running a command that only the graphical session can reach.
`hyprctl`, `waybar` and the rest need the session's Wayland socket, its Hyprland instance signature and its bus. A real
run is root, and root has none of those, so these applies go through `utils/session.py`.

It finds the active graphical session with `loginctl`, reads that session's environment out of
`systemctl --user -M <user>@ show-environment`, and runs the command as the session's owner. Reading the environment
back is exact because Hyprland's autostart runs `systemctl --user import-environment`; reconstructing
`WAYLAND_DISPLAY` or the instance signature would be a guess, so `run_in_session()` skips the action instead of
acting on one. Report skipped actions to the user rather than dropping them, since they still apply on next login.

Session applies are best-effort by nature: pass `check=False`, so a failed reload warns instead of failing the run.
`utils/session.py` does this for every command it runs, and returns `False` when there is nothing to run in.

## Gotchas

- **The systemd step only reloads a user manager when that user's enabled units change**: It reloads the system
  manager on every run, but editing the body of a user unit reloads nothing. Request `reload_user_systemd` for that.
- **`udevadm control --reload` only loads rules, it does not run them**: Rules execute on device events, and devices
  present since boot do not fire one, so a reload alone leaves new rules dormant. Pair it with
  `udevadm trigger --subsystem-match=power_supply --action=change`.
    - Keep `udevadm trigger` scoped to the subsystems that NosArch has udev rules for (For example: `power_supply`).
      A bare `udevadm trigger` replays events for every device, which can rebind drivers and re-probe storage.
- **`systemd-tmpfiles --remove` is not scoped to managed files**: It deletes every path marked `r`/`R` across all
  tmpfiles configs on the system. `--clean` should be used.
- **systemd output parsed in a hook needs `capture=True`**: On a terminal, systemd colorizes `loginctl` and `systemctl`
  output, and the escape codes land inside the fields being parsed. Captured output is not a terminal.
- **`systemctl --user -M <user>@` fails when the user manager is not running**: For example when applying from a TTY
  or during a fresh install. Pass `check=False` rather than guarding every call site.
- **Restart a unit the user may have turned off with `try-restart`**: `restart` would start a timer the user had
  disabled (`nosarch-eyesight-reminder.timer` is enabled by default, but a hook cannot assume that stays true).
- **Desktop daemons mostly have no reload request**: `swaync-client --reload-config`/`--reload-css` and waybar's
  `SIGUSR2` are the exceptions. `hyprpaper`, `hyprsunset`, `hypridle`, and swayosd read their config once, at start,
  and `hyprctl` has no request for them either, so restart the user service. A leftover uwsm app scope has to be
  stopped in the same command, or the scope keeps running beside the service. Walker is still started from Hyprland's
  autostart and does not exit, so relaunch it in a new session (`setsid -f`) and drop its output, or the run waits on
  the process and never reaches the logout and reboot offer.
- **`hyprctl reload` re-applies monitors**: Pass `config-only` when only the config changed. `hyprmoncfgd` owns the
  monitor layout, and a full reload fights it.
- **waybar's stylesheet needs no reload**: `reload_style_on_change` is set in its config. Its `config.jsonc` does.
- **Ghostty has no `+reload-config` action**: A new window picks the config up, so there is nothing to apply.
- **`hyprlock`'s config needs no apply at all**: `nosarch-lock-helper.sh` spawns a fresh hyprlock for every lock.
- **`pkill` exits non-zero when the process is not running**: A session daemon is often absent (install time, a TTY,
  the user closed it). Let the kill fail and let the relaunch decide the exit code, or every such run warns.
