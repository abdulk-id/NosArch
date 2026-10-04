# Development

## Setting up workspace

- `mise install`.
- `mise run setup`.

### NosArch Works

NosArch Works sets up your machine to work on NosArch. It installs the packages used for NosArch development, and
enables prechecks that are run on every invocation of decman.

NosArch Works can be enabled by setting `advanced.enable_nosarch_works` to `true` in the config file
(`~/.nosarch_config.json`).

## Testing

- Shell scripts: `shellcheck`.
- Custom package PKGBUILDs: `python3 tools/manage_custom_packages.py validate` (pass `--build` to audit `depends`).
- Definition code: dry-run decman. It requires root access.
