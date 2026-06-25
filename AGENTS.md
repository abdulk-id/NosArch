# NosArch — Agent Instructions

Arch Linux dotfile repo managed by [decman](https://github.com/kiviktnm/decman). Declaratively defines packages, files, services, and user config via Python.

## Apply / test

```sh
sudo decman                 # apply
sudo decman --dry-run       # preview
```

Must run as root. `--source` defaults to `~/NosArch/nosarch/source.py`.

## Setup before first run

- `nosarch/config.py` is **gitignored**. Copy from `nosarch/config.example.py`.
- `decman` itself is installed via AUR (listed in `source.py`).

## Config profiles (`nosarch/config.py`)

Conditional flags control which modules load in `source.py`:

| Flag                 | Module            | What it adds                            |
| -------------------- | ----------------- | --------------------------------------- |
| `%FULL_SETUP%`       | `FullSetupModule` | Office, media, virtualization apps      |
| `%CREATIVE_PROFILE%` | `CreativeModule`  | Placeholder — empty class               |
| `%DEV_PROFILE%`      | `DevModule`       | Dev tools, git/ideavimrc, Codespace dir |
| `%GAMING_PROFILE%`   | `GamingModule`    | Steam, Lutris, Gamescope, ntsync        |

Set to `"true"` to enable. Default `"false"`.

## Module ownership (under `nosarch/`)

| Path                                 | Module            | What it owns                                                                   |
| ------------------------------------ | ----------------- | ------------------------------------------------------------------------------ |
| `source.py`                          | —                 | Entrypoint, execution order, user/group, conditional module registration       |
| `modules/system.py`                  | `SystemModule`    | System packages, systemd services, `/etc/`, `/usr/local/bin/`, `~/.gitconfig`  |
| `modules/desktop.py`                 | `DesktopModule`   | Hyprland/Wayland, desktop apps, user systemd units, `~/.config/`               |
| `modules/theme.py`                   | `ThemingModule`   | Theme variables, wallpaper deployment, `~/.local/share/nosarch/current-theme/` |
| `modules/setup.py`                   | `SetupModule`     | Minimal personal apps (browsers, basic tools) and user setup                   |
| `modules/setup_full.py`              | `FullSetupModule` | LibreOffice, Obsidian, OBS, virt-manager, QEMU, Spotify                        |
| `modules/usage_profiles/creative.py` | `CreativeModule`  | Empty placeholder                                                              |
| `modules/usage_profiles/dev.py`      | `DevModule`       | Dev packages, `~/.ideavimrc`, `~/Codespace/`                                   |
| `modules/usage_profiles/gaming.py`   | `GamingModule`    | Steam/Lutris, Gamescope, ntsync, `dotfiles/gaming-root/`                       |

## Variable substitution

Config files interpolate `%VARIABLE%` from two merged sources:

- **`nosarch/config.py`** (gitignored): `%USER%`, `%FULLNAME%`, `%GIT_EMAIL%`, profile flags
- **Theme dict** (e.g. `themes/nosarch_blue_dark/nosarch_blue_dark.py`): colors, `%FILENAME%`, fonts
- **Dynamic**: `%LUKS_UUID%` from `utils/luks_uuid.py` (system module).
- **Switch theme** by changing the import in `modules/theme.py` line 6.
- Merging: `modules/system.py` uses `CONFIG | system_variables`, `modules/desktop.py` uses `CONFIG | get_current_theme()`, profile modules use `CONFIG` directly.

## File layout

`dotfiles/root/` mirrors the target filesystem. Paths relative from `nosarch/`:

| Source                         | Target            | Owner |
| ------------------------------ | ----------------- | ----- |
| `dotfiles/root/etc/`           | `/etc/`           | root  |
| `dotfiles/root/usr/local/bin/` | `/usr/local/bin/` | root  |
| `dotfiles/root/home/username/` | `/home/<user>/`   | user  |

`dotfiles/gaming-root/` — same mirror pattern, deployed by `GamingModule`.

`Directory()` recursively deploys, `File()` handles single files. `bin_files=False` enables variable substitution.

## Decman conventions

- **Use `|=` to add to sets**, never `=` (reassignment wipes prior operations).
- **Always `import decman` then `decman.pacman`** — `from decman import pacman` may not work with global plugin instances.
- Decorators from `decman.plugins`: `@pacman.packages`, `@aur.packages`, `@flatpak.packages`, `@flatpak.user_packages`, `@systemd.units`, `@systemd.user_units`.
- Plugin execution order (set in `source.py`): `files → pacman → flatpak → systemd`.
    - AUR is **commented out** of execution order. `@aur.packages` methods still exist but are never executed.
    - AUR is **commented out** because of the 2026 "Atomic-Arch" AUR attacks from the npm supply chain compromise.
- **Ignored packages**: `kernel-modules-hook` (pacman), `icon-library` (pacman), `dconf-editor` (pacman), `yay` (AUR).
- Single-user only.

## Additional directories

- `customization/fonts/` — custom font assets (not deployed by decman, manual)
- `dotfiles/unused-config/` — leftover configs for Elephant and Walker launchers (replaced by Vicinae)
- `docs/` — reference documentation

## No CI/CD, tests, or linting

No test runner, CI, or linters (except `.editorconfig`). Verify with `sudo decman --dry-run`.

## OpenCode permissions (`opencode.jsonc`)

- `AGENTS.md` edits: auto-allowed
- `sudo decman --dry-run`: auto-allowed
- Other `sudo` commands: **denied**
- Edits to `*`: require `ask` permission

## Reference

- Decman docs: https://github.com/kiviktnm/decman/blob/main/docs/README.md
- Source repo: https://github.com/abdulk-id/NosArch
