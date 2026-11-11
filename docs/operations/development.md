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
- Definition code: `python -m nosarch --dry-run` from the repository root (or `mise run dryrun`). It needs no root, so
  an agent can run it. With no state file yet, a dry run treats every module as newly enabled.
- Engine: `mise run test-engine` (pytest, `tests/engine/`) runs real, non-dry runs against a scratch directory,
  without root and without running any command. `mise run test-engine-root` runs the few tests that chown or switch
  user, in a user namespace that fakes root. Both need `python-pytest`, which NosArch Works installs.
- Config schema: `python tests/test_config_schema.py`. Settings are defined on the classes in
  `nosarch/definition/user_config.py`. After changing a setting, run `python utils/config_schema_generator.py` to refresh
  `config.schema.json`. The test fails if that file does not match the classes.
