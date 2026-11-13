# Engine

NosArch applies itself with its own engine in `nosarch/engine/`. [Hooks](hooks.md) covers `on_change` and hook order;
[packages](packages.md#foreign-packages) covers the foreign package build.

The engine needs Python, pacman, and git. Chroot builds also need devtools.

## Dry runs must stay unprivileged

A dry run runs the same steps as a real run, with every write and every hook skipped. That only works while nothing on
the dry path needs root, so new code keeps it that way:

- **Declaring is read-only and needs no root.** Modules are asked for their declarations before any step runs, on dry
  runs too. Something that needs root, like fetching custom PKGBUILDs into their root-owned cache, happens in a step,
  and only on a real run.
- **Owners are resolved at the files step, not when a file is declared.** On a first run the account a file belongs to
  is created by the users step, after declarations are gathered.
- **The state is world-readable** (`/var/lib/nosarch/state.json`), so a dry run can read it without root. It holds
  paths, package and unit names, the accounts the engine created, and the last reviewed AUR commit for each package
  base. That review map is kept only here: the build directory is removed at the end of the run. It holds no secrets.
- **Run commands through `nosarch.engine.run(..., user=...)`.** As root it switches user. Without root it runs the
  command as the current user when that is the user asked for, which is how a dry run checks Flatpak and Homebrew for
  the configured user.

`makepkg --printsrcinfo` refuses to run unless its build directories are writable, even though it only prints. The
custom PKGBUILD cache is root-owned, so it is pointed at a scratch directory.

## Where it differs from decman on purpose

The engine descends from [decman](glossary.md), and definition code written for decman reads the same. These behave
differently, each by decision:

- **No change is lost.** A change is saved before the hooks run and carried until `on_change` has seen it, so a failed
  run, `--no-hooks`, or a removal does not swallow it. Mode and owner drift on a regular file count as changes, since
  a hook that reloads a service has to hear about a file that was put back. A symlink is compared by its target only,
  so an owner change on a link is left as it is and is not reported.
- **`on_disable` needs the module registered with `enabled=False`.** decman ran a script it saved at enable time, so it
  worked after the class was deleted. A module gone from the code is forgotten with a warning, and adding it back
  later fires `on_enable` again.
- **A step name that does not exist is an error**, for `--only`, `--skip` and the setup, not a silent no-op.
- **Files are replaced through a temporary file and a rename.** A hard link keeps the old content, and a file declared
  on a symlink replaces the link. A dry run reads the source files, so a missing one shows before a real run.
- **A command's stdout either streams or is captured.** Capturing returns stdout only, so definition code that parses
  a command's output does not get stderr mixed in.
- **Hooks get no store, and there are no standalone groups or uids.** Users are declared with their groups, and only
  accounts the engine created are deleted.
- **Only units this engine enabled are disabled.** The systemd step diffs against the units it recorded, so a unit
  enabled by hand, or by a package preset, stays. See
  [`systemd.py`](../../nosarch/engine/steps/systemd.py).
- **Two modules declaring one path is an error**, where decman flapped between the two contents.

## Testing

The `box` fixture replaces `nosarch.engine.command.run` with a recorder. That holds only while a step calls it at call
time. A step that calls `subprocess` directly, or binds `run` at import, runs the real command inside a test.
