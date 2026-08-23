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
    - Optional profiles live under `nosarch/modules/usage_profiles/`.
- Reusable helpers are in `nosarch/utils/`.
- Theme data and wallpapers are under `nosarch/themes/`.
- Managed files live under `dotfiles/`, with a separate mirrored root per module (e.g. `dotfiles/system-root/`, `dotfiles/desktop-root/`, `dotfiles/dev-root/`, `dotfiles/gaming-root/`, `dotfiles/setup-full-root/`); inside each, `etc/`, `usr/`, and `home/username/` map to `/etc/`, `/usr/`, and `/home/<user>/`.
    - `dotfiles/unused-config/` is not deployed.

## Testing Guidelines

There is no dedicated test suite.

Performing a decman dry-run requires root access.

Validate changes by asking the user to dry-run decman and report back any errors.
