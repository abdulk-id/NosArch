# Repository Guidelines

## Project Structure & Module Organization

NosArch is an Arch Linux dotfile and system configuration repo managed by Decman. The entrypoint is `nosarch/source.py`, which registers users, execution order, and modules. Core modules live in `nosarch/modules/`: `system.py` manages system packages, services, and root-owned files; `desktop.py` manages Hyprland and user config; `theme.py` deploys wallpapers; `setup.py` and `setup_full.py` install common and full-profile apps. Optional profiles live under `nosarch/modules/usage_profiles/`.

Reusable helpers are in `nosarch/utils/`. Theme data and wallpapers are under `nosarch/themes/`. Managed files mirror target paths under `dotfiles/root/`, for example `dotfiles/root/etc/` maps to `/etc/` and `dotfiles/root/home/username/` maps to `/home/<user>/`.

## Build, Test, and Development Commands

```sh
cp config.example.py nosarch/config.py
sudo decman --source ~/NosArch/nosarch/source.py --dry-run
sudo decman --source ~/NosArch/nosarch/source.py
```

Use `config.example.py` as the local template; `nosarch/config.py` is gitignored. Run the dry run before applying changes to preview package, file, Flatpak, and systemd operations.

Reference Decman syntax and behavior in the official docs: https://github.com/kiviktnm/decman/blob/main/docs/README.md

## Coding Style & Naming Conventions

Python modules use PEP 8 style with 4-space indentation and descriptive names. Keep module ownership clear: add system-level changes to `system.py`, desktop/user config to `desktop.py`, and profile-specific behavior to the matching usage profile.

When adding to Decman collections, use `|=` to extend sets; do not reassign existing package or file sets. Import Decman as `import decman` and then access plugin namespaces such as `decman.pacman`.

Shell scripts in `dotfiles/root/**/bin/` must be POSIX `sh`, start with `#!/bin/sh`, use `set -eu`, and follow the help/function layout shown in `CONTRIBUTING.md`.

## Testing Guidelines

There is no dedicated test suite. Validate changes with:

```sh
sudo decman --source ~/NosArch/nosarch/source.py --dry-run
```

For utility changes, run targeted commands when possible, such as invoking a script with `help` or testing a Python helper in isolation. Avoid applying system changes until the dry run is clean.

## Commit & Pull Request Guidelines

Recent commits use scoped, imperative subjects such as `Scripts: Make all shell scripts POSIX-compliant` and `System: Add vendor-based CPU and GPU setup`. Keep that pattern: `Area: Action summary`.

Pull requests should describe the affected module or dotfile path, list validation performed, and call out package, service, or root-owned file changes. Screenshots are useful for visible desktop or theme changes.

## Configuration & Safety Notes

This repo targets a single-user Arch Linux setup. Profile flags in `CONFIG` control optional modules, including full setup, creative, development, and gaming profiles. AUR execution is currently disabled in `nosarch/source.py`, even though AUR package decorators may appear in modules.
