# Files

How NosArch declares the files it owns, where they live in the repo, and what has to happen
after one of them changes for the running system to notice.

## Every file is declared individually

decman offers `Directory()`, which deploys a whole source tree. NosArch does not use it.
Every managed file is named explicitly in a module's `files()`.

This is more verbose, and deliberately so:

- **A module is a manifest.** Reading `system.py` tells you every path NosArch writes to.
  With directories you would have to read the repo tree instead, and the two can drift.
- **Nothing deploys by accident.** A `Directory()` ships whatever is in the source tree, so
  an editor backup, a `.orig` from a merge, or a half-finished file lands on the system the
  moment it is saved. An undeclared file in `dotfiles/` is inert.
- **Settings are per file, not per tree.** `Directory` applies one `owner`, one
  `permissions` and one `bin_files` to everything it walks (`core/fs.py:429`). That cannot
  express a directory holding both templated text and binaries.

The plymouth theme is the concrete case for the third point. `bin_file=True` disables
variable substitution (`core/fs.py:163`), so a single directory declaration would have
forced a choice between corrupting the PNGs and leaving `%ACCENT%` unsubstituted in
`nosarch.script`. As two `tracked_files()` calls it is exact:

```python
files.update(
    self._dotfiles.tracked_files(
        self._tracker,
        "/usr/share/plymouth/themes/nosarch/bullet.png",
        # ... the rest of the images
        bin_file=True,
    )
)
files.update(
    self._dotfiles.tracked_files(
        self._tracker,
        "/usr/share/plymouth/themes/nosarch/nosarch.plymouth",
        "/usr/share/plymouth/themes/nosarch/nosarch.script",
    )
)
```

## Layout

Each module owns a mirrored root under `dotfiles/`: `system-root/`, `desktop-root/`,
`dev-root/`, `gaming-root/`, `setup-full-root/`. Inside one, `etc/` and `usr/` map onto `/etc`
and `/usr` directly, and `home/username/` maps onto the configured user's home.

`dotfiles/unused-config/` is not deployed by anything. It is a holding area, and
`tools/check_paths.py` skips it.

Hidden files and directories are stored with a `dot_` prefix — `dot_bashrc`,
`dot_config/hypr/`. Storing them as real dotfiles hides them from `ls`, from some editors'
file trees, and from shell globs, which makes the source tree harder to work with.
`utils/paths.py` translates the prefix back on deployment, so declarations name
the real path.

## Declaring

Use the helpers in `utils/paths.py` rather than constructing `File` by hand. They derive the
source path from the target path, which keeps the two in step and removes the commonest
source of typos.

```python
self._dotfiles: utils.paths.Dotfiles = utils.paths.Dotfiles("../dotfiles/system-root")
self._userhome_dotfiles: utils.paths.UserhomeDotfiles = utils.paths.UserhomeDotfiles(
    "../dotfiles/system-root", _username
)
```

`Dotfiles` takes absolute system paths. `UserhomeDotfiles` takes paths relative to the user's
home, applies the `dot_` translation, and sets the owner to that user:

```python
files.update(
    self._dotfiles.tracked_files(
        self._tracker,
        "/etc/sysctl.d/99-memory-parameters.conf",
        "/etc/mkinitcpio.conf",
    )
)

files.update(
    self._userhome_dotfiles.tracked_files(
        self._tracker, "/.bashrc", "/.config/yay/config.json"
    )
)
```

Keyword arguments apply to every path in the call, so group by what they share:
`permissions=0o755` for executables, `bin_file=True` for anything not UTF-8 text.

### When to declare by hand

Construct `File` directly when there is no source file to point at — content generated at
run time:

```python
wireless_regdom: str | None = utils.dotfile.wireless_regdom.get_wireless_regdom_contents()
if wireless_regdom:
    files.update(
        {
            "/etc/conf.d/wireless-regdom": File(
                content="# Wireless regulatory domain configuration\n\n" + wireless_regdom,
                owner="root",
            )
        }
    )
```

These are invisible to `tools/check_paths.py`, which reads `dotfiles/`. Keep them rare.

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

Substitution is skipped for `bin_file=True`, and for files declared with `content=`.

## Removal is automatic

Deleting a declaration deletes the file. decman keeps every path it has written in
`store["all_files"]`, and on each run removes those that no longer appear in any module
(`core/file_manager.py:113`). There is no uninstall step to write, and no cleanup migration
to schedule.

The corollary is that a file NosArch never declared is a file NosArch will never remove.
Anything created by hand outside a module stays forever, and decman will not report it.

## Tracking changes

`File` alone says what should be on disk, not whether it was just written. `on_change` hooks
need the latter, so declarations go through `utils/change_tracker.py`, which subclasses
decman's `File`, `Directory` and `Symlink` to record every path actually written:

```python
self._tracker: utils.change_tracker.ChangeTracker = utils.change_tracker.ChangeTracker()
```

Then `tracked_files()` instead of `files()`. Each module carries its own tracker and sees
only its own files.

Nothing is recorded during `--dry-run`.

## Applying changes

Writing a file is rarely enough. `systemd-sysctl` read `/etc/sysctl.d/` once at boot; udev
loaded its rules at boot; systemd parsed its units at boot. Deploying a replacement changes
none of that until something reloads.

This fails quietly. The file is correct, decman reports success, and the machine keeps the
old behaviour. NosArch shipped the whole of `99-memory-parameters.conf` inert this way — the
file was on disk and every value in it was at the kernel default.

### What each path needs

| Changed under                                                                                                          | Command                                                     |
| ---------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| `/etc/sysctl.d/`                                                                                                       | `sysctl --system`                                           |
| `/etc/udev/rules.d/`                                                                                                   | `udevadm control --reload`, then a scoped `udevadm trigger` |
| `/etc/tmpfiles.d/`                                                                                                     | `systemd-tmpfiles --create --clean`                         |
| `/etc/mkinitcpio.conf`, `/etc/mkinitcpio.conf.d/`, `/etc/modprobe.d/`, `/etc/plymouth/`, `/usr/share/plymouth/themes/` | `limine-mkinitcpio`                                         |
| `/usr/lib/systemd/`, `/etc/systemd/system/`                                                                            | `systemctl daemon-reload`                                   |
| `/etc/systemd/system.conf.d/`, `/etc/systemd/user.conf.d/`                                                             | `systemctl daemon-reexec`                                   |
| `/etc/systemd/journald.conf.d/`                                                                                        | `systemctl restart systemd-journald`                        |
| `/etc/NetworkManager/`                                                                                                 | `systemctl reload NetworkManager`                           |
| `/etc/ufw/`                                                                                                            | `systemctl restart ufw`                                     |
| `/usr/share/glib-2.0/schemas/`                                                                                         | `glib-compile-schemas /usr/share/glib-2.0/schemas`          |

Needing nothing: `/usr/local/bin/`, `/etc/pacman.conf`, `/etc/pacman.d/hooks/`,
`/etc/snapper/configs/`, `/etc/default/limine`, `/etc/greetd/`, and everything under a user's
home.

### Matching paths

Test with `os.path.commonpath`, not `str.startswith`, so path boundaries are respected —
`/etc/systemd/system` must not match `/etc/systemd/system.conf.d/`:

```python
def changed_files_in(*target_dirs: str) -> bool:
    for target_dir in target_dirs:
        target_path: str = os.path.abspath(target_dir)

        if any(os.path.commonpath([p, target_path]) == target_path for p in changed_files):
            return True
    return False
```

### Ordering

1. **`systemctl daemon-reload` first.** Everything below it reloads or restarts a unit, and
   those act on the manager's loaded state rather than on what is now on disk.
2. **`systemctl daemon-reexec` next**, for manager-level defaults.
3. Everything cheap and independent, in any order.
4. **`limine-mkinitcpio` last but one.** It is the slowest step by a wide margin — roughly 30
   seconds, doubled when the LTS kernel is enabled. Several triggers write into the same
   image, so gather them into one guarded call rather than rebuilding per trigger.
5. **The reboot notice last**, once everything that could be applied live has been.

### Hooks must be idempotent

`on_change` fires whenever the module's content changed, with no memory of having fired
before. It is not a migration: it may run any number of times, including when the specific
file it reacts to did not change. Every command in the table above is safe to re-run.
Appending to a file, bumping a counter, or any one-way transform is not.

### Reboot-only changes

Some files have no safe live path. Collect them and report at the end:

- **zram** (`/etc/systemd/zram-generator.conf`, `/etc/modules-load.d/zram.conf`) — applying
  live means `swapoff` on an active device holding compressed pages, which can OOM the
  machine under memory pressure.
- **logind** (`/etc/systemd/logind.conf.d/`) — `systemd-logind` has no `ExecReload`, and
  restarting it disturbs active sessions.

Prompt with `decman.core.output.prompt_confirm`, guarded on `sys.stdin.isatty()` so a
scripted install does not hang on a prompt nobody can see. `on_change` is skipped under
`--dry-run` (`app.py:343`), so hooks need no dry-run handling of their own.

## Checking

`tools/check_paths.py` reads every file under `dotfiles/` and verifies that NosArch-owned
paths referenced inside them — in unit files, udev rules, shell scripts — resolve to
something a module actually deploys. It catches the case where a script moves but a reference
to its old path survives, which decman cannot see on its own. `source.py` runs it on every
invocation and aborts on failure.

Its scope is `/usr/local/bin` and `/usr/lib/nosarch` in full, not just the subdirectories
currently in use. A narrower prefix is matched against the _referenced_ string, so a typo
corrupting the subdirectory itself (`/usr/local/bin/uti/` for `/usr/local/bin/util/`) would
stop matching the prefix and drop silently out of scope.

## Gotchas

- **decman's own `daemon-reload` is not enough.** It runs only when the _set_ of enabled units
  changes (`plugins/systemd.py:176`). Editing the body of a unit without changing which units
  are enabled reloads nothing.
- **`udevadm control --reload` only loads rules, it does not run them.** Rules execute on device
  events, and devices present since boot do not fire one, so a reload alone leaves new rules
  dormant. Pair it with `udevadm trigger --subsystem-match=power_supply --action=change`. Keep
  it scoped: a bare `udevadm trigger` replays events for every device on the system, which can
  rebind drivers and re-probe storage.
- **`systemd-tmpfiles --remove` is not scoped to your files.** It deletes every path marked
  `r`/`R` across all tmpfiles configs on the system. `--create --clean` is what NosArch needs.
