# NosArch

NosArch is an Arch Linux dotfile and system configuration repo managed by Decman.

## Project Structure

- The entrypoint is `nosarch/source.py`, which configures decman behavior.
- Core modules live in `nosarch/modules/`:
    - `system.py` manages system packages, services, and root-owned files;
    - `desktop.py` manages Hyprland and user config;
    - `setup.py` and `setup_full.py` install common and full-profile apps;
    - `theme.py` deploys wallpapers;
    - `homebrew.py` prepares the system to use homebrew;
    - `user_defined.py` manages packages manually listed by users in their JSON config;
    - Optional profiles live under `nosarch/modules/usage_profiles/`.
- Reusable helpers are in `nosarch/utils/`.
- Theme data and wallpapers are under `nosarch/themes/`.
- Managed files live under `dotfiles/`, with a separate mirrored root per module (e.g. `dotfiles/system-root/`, `dotfiles/desktop-root/`, `dotfiles/dev-root/`, `dotfiles/gaming-root/`, `dotfiles/setup-full-root/`); inside each, `etc/`, `usr/`, and `home/username/` map to `/etc/`, `/usr/`, and `/home/<user>/`.
    - `dotfiles/unused-config/` is not deployed.
- User config reader is in `nosarch/user_config/config_reader.py`
- Repo-maintenance scripts live in `tools/`.
    - `tools/check_paths.py` checks that NosArch-owned paths referenced anywhere in `dotfiles/`
      (unit files, udev rules, shell scripts) resolve against what the modules actually deploy.
      `decman --source` runs it and aborts if the script finds a dangling reference.

## Testing Guidelines

There is no dedicated test suite.

Performing a decman dry-run requires root access.

Validate changes by asking the user to dry-run decman and report back any errors.
