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

## Switching from decman

`nosarch/apply.py --import-decman` turns decman's store into the engine's state. A real run does it by itself when
there is no state yet, but a dry run cannot read decman's root-only store, so import first.

Without the import, every module looks newly enabled and every hook fires, files decman deployed but nothing declares
any more are never removed, and units decman enabled are never disabled. decman kept one list of files for all modules,
so files that no module declares any more are removed without any module's hook hearing about it.

The first full run removes the `decman` package, since nothing declares it. `/var/lib/decman` and
`/var/cache/decman` are left behind and can be deleted.
