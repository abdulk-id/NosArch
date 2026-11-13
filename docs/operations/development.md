# Development

`mise setup` sets up the workspace. `mise tasks` lists the lint, format, and test tasks.

## NosArch Works

Set `advanced.enable_nosarch_works` to `true` in `~/.nosarch_config.json` to install the tools for working on NosArch
(`shellcheck`, `python-pytest`, `namcap`, `lynis`, and others; see
[`system.py`](../../nosarch/definition/modules/system.py)).

## Testing

- Shell scripts: `shellcheck`.
- Definition code: `mise dryrun`. Without a state file, a dry run treats every module as newly enabled.
- Engine: `mise test-engine` runs against a scratch directory without root. Most tests are real runs, some are dry
  runs, and the `box` fixture records commands instead of running them. `mise test-engine-root` runs the tests that
  chown or switch user, in a user namespace that fakes root.
- Config schema: settings are defined on the classes in `nosarch/definition/user_config.py`. After changing one, run
  `mise config-schema` to refresh `config.schema.json`; `mise test-config` fails when the file is stale.
- Everything: `mise test-all`.
