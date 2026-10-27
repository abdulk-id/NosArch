# Development

## Setting up workspace

- `mise install`.
- `mise run setup`.

### NosArch Works

NosArch Works sets up your machine to work on NosArch. It installs the packages used for NosArch development.

NosArch Works can be enabled by setting `advanced.enable_nosarch_works` to `true` in the config file
(`~/.nosarch_config.json`).

## Testing

- Shell scripts: `shellcheck`.
- Definition code: `nosarch/apply.py --dry-run` (or `mise run dry-run-quick`). It needs no root, so an agent can run it.
  Before NosArch has a state file of its own, run `nosarch/apply.py --import-decman` once (it asks for sudo), or the
  dry run sees every module as new.
- Engine: `python3 -B tests/test_engine.py` runs real, non-dry runs against a scratch directory, without root.
- Config schema: `python tests/test_config_schema.py`. Settings are defined on the classes in
  `nosarch/user_config.py`. After changing a setting, run `python utils/config_schema_generator.py` to refresh
  `config.schema.json`. The test fails if that file does not match the classes.
