# NosArch

NosArch is an Arch Linux dotfile and system configuration repo managed by Decman.

## Glossary

- **Target system** refers to the arch linux system decman is going to apply all changes to.
- **Deploying dotfiles** means installing files from `dotfiles` to the target system.
- **Definition code** means the code defining how and where to deploy dotfiles, which packages to install, and
  managing systemd units.

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

## Documentation

- `docs/internal/` is for code decisions and their reasons, and implementation traps that are hard to discover from the source.

Most code changes do not need an internal documentation update.

## Testing

- To test shell scripts, use shellcheck.
- To test PKGBUILDs of custom packages: `python3 tools/check_custom_packages.py` (pass `--build` to audit `depends`
  of PKGBUILDs).
- The definition code can be tested by dry-running decman. It requires root access so ask the user to do so and report
  back any errors.
