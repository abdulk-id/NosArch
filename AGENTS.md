# NosArch

NosArch is an Arch Linux dotfile and system configuration repo managed by Decman.

## Glossary

- **Target system** refers to the arch linux system decman is going to apply all changes to.
- **Definition code** means the code defining how and where to deploy dotfiles, which packages to install, and
  managing systemd units.
- **Deploying** means applying the results of the definition code to the target system.

## Project Structure

- The entrypoint is `nosarch/source.py`, which configures decman behavior.
- Definition code lives in `nosarch/modules/`.
- Themes for the system live in `nosarch/themes`.
- Custom Decman plugins live in `nosarch/plugins`.
- Helpers used by Decman's source live in `nosarch/utils`.
- PKGBUILDs of custom packages live in `nosarch/packages`.
- Dotfiles to be deployed by Decman live in `dotfiles/`, with separate mirrored root per module.
- JSON schema for NosArch's config is in `config.schema.json`.
- Repo maintenence and test scripts live in `tools/`.
- `tools/apply` is the entrypoint for deploying. It runs decman, then offers to log out or reboot for the changes that
  need a new login. Decman on its own applies everything it can live, but cannot offer that action.

## Documentation

- `docs/internal/` is for code decisions and their reasons, and implementation traps that are hard to discover from the source.

Most code changes do not need an internal documentation update.

## Testing

- To test shell scripts, use shellcheck.
- To test PKGBUILDs of custom packages: `python3 tools/check_custom_packages.py` (pass `--build` to audit `depends`
  of PKGBUILDs).
- The definition code can be tested by dry-running decman, through `tools/apply --dry-run` or `mise run dry-run-quick`.
  It requires root access so ask the user to do so and report back any errors.
