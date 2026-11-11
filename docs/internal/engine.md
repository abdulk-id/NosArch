# Engine

NosArch deploys itself with its own engine in `nosarch/engine/`, which replaced decman. The reasons were:

- **Dry runs without root.** decman needs root for a dry run too, so an agent could never check its own work.
- **Logout and reboot prompts.** A logout or reboot ends the process doing it, so decman needed a wrapper script that
  read its store after it exited. The engine offers them itself, after everything else has finished.
- **Change tracking.** decman's `on_change` did not say what changed. NosArch worked around that with a tracker that
  subclassed decman's file classes.
- **Fewer dependencies.** decman comes from the AUR and pulls in pyalpm and python-requests. The engine needs Python,
  pacman, and devtools for chroot builds.

The module API kept decman's shape (`files()`, `@pacman.packages`, the hook phases), so definition code reads the
same.

## Dry runs must stay unprivileged

A dry run runs the same code as a real run, with every write skipped. That only works while nothing on the dry path
needs root, so new code has to keep it that way:

- **Declaring must not write or need root.** Modules are asked for their declarations before any step runs, on dry
  runs too. Something that needs root, like fetching custom PKGBUILDs into their root-owned cache, happens in a step,
  and only on a real run.
- **Owners are resolved at the files step, not when a file is declared.** On a first run the account a file belongs to
  is created by the users step, after declarations are gathered.
- **The state is world-readable** (`/var/lib/nosarch/state.json`). It holds paths, package and unit names, and nothing
  that is not readable elsewhere on the system.
- **Run commands through `engine.run(..., user=...)`.** As root it switches user. Without root it runs the command as
  the current user when that is the user asked for, which is the user a dry run checks Flatpak and Homebrew for.

`makepkg --printsrcinfo` refuses to run unless its build directories are writable, even though it only prints. The
custom PKGBUILD cache is root-owned, so it is pointed at a scratch directory.

## Only what the engine did is undone

The engine disables only units it enabled itself, and deletes only accounts it created. A unit the user enabled by hand
or a package enabled through a preset stays, and a login account that existed before NosArch is never deleted, even if
the username in the config changes.

## Foreign packages

AUR and custom packages are built by `aurbuilduser` and installed by root with `pacman -U`.

By default each build runs in a fresh chroot (`advanced.build_aur_in_clean_chroot`), so nothing installed on the host
leaks into a build. A chroot starts empty, so an AUR dependency has to be handed to it as a package file even when it
is installed on the host. Built packages are kept in `/var/cache/nosarch/packages` for that reason: without the cache,
every AUR dependency would be rebuilt whenever something depending on it is.

With the chroot off, builds run on the host. A build's dependencies are installed as dependencies first and removed
once nothing needs them.

AUR PKGBUILDs are offered for review before they run: the diff since the last reviewed commit, or every file the first
time. Custom packages are not, since they come from NosArch's own repository.

## Where it differs from decman on purpose

Definition code written for decman reads the same, but these behave differently, each by decision:

- **No change is lost.** A change is saved before the hooks run and carried until `on_change` has seen it, so a failed
  run, `--no-hooks`, or a removal does not swallow it. Mode and owner drift count as changes, since a hook that
  reloads a service has to hear about a file that was put back.
- **`on_disable` needs the module registered with `enabled=False`.** decman ran a script it saved at enable time, so it
  worked after the class was deleted. A module gone from the code is forgotten with a warning, and adding it back
  later fires `on_enable` again.
- **A step name that does not exist is an error**, for `--only`, `--skip` and the setup, not a silent no-op.
- **Files are replaced through a temporary file and a rename.** A hard link keeps the old content, and a file declared
  on a symlink replaces the link. A dry run reads the source files, so a missing one shows before a real run.
- **A command either streams or is captured**, and a captured one returns stdout only: definition code that parses
  `loginctl` output must not get stderr mixed in. A command run as a user gets that user's `HOME`.
- **Hooks get no store, and there are no standalone groups or uids.** Users are declared with their groups, and only
  accounts the engine created are deleted.
- **Two modules declaring one path is an error**, where decman flapped between the two contents.

## Testing

`tests/engine/` is plain pytest, run in-process against a temporary directory. The `box` fixture replaces
`engine.command.run` with a recorder, so no test runs `systemctl`, `useradd` or `pacman`. That only works while steps
call `engine.command.run` at call time. A step that calls `subprocess` directly, or binds `run` at import, would run
the real command inside a test.
