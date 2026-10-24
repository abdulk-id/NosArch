# Development

## Setting up workspace

- `mise install`.
- `mise run setup`.

### NosArch Works

NosArch Works sets up your machine to work on NosArch. It installs the packages used for NosArch development, and
enables prechecks that are run on every invocation of decman.

NosArch Works can be enabled by setting `advanced.enable_nosarch_works` to `true` in the config file
(`/etc/nosarch/config.json`).

## Testing

- Shell scripts: `shellcheck`.
- Definition code: dry-run decman. It requires root access.
- Config schema: `python tests/test_config_schema.py`. Settings are defined on the classes in
  `nosarch/user_config.py`. After changing a setting, run `python utils/config_schema_generator.py` to refresh
  `config.schema.json`. The test fails if that file does not match the classes.
