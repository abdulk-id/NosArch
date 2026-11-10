# NosArch Docs

## Using NosArch

User manual is being worked on.

## Working on NosArch

It is recommended to work on NosArch from a machine running NosArch so changes can be tested live easily.

### How it works

`nosarch/apply.py` runs NosArch's own deployment engine (`nosarch/engine/`). `nosarch/source.py` builds its `Setup`: the
modules in `nosarch/modules/`, which declare which dotfiles, packages, and systemd units each one deploys. On a run,
the engine installs what modules declare and removes what no module declares anymore. Custom packages are regular
pacman packages built from PKGBUILDs in [NosArch-Packages](https://github.com/abdulk-id/NosArch-Packages) so the engine
manages them the same way.

A dry run (`nosarch/apply.py --dry-run`) needs no root. A real run asks for it with sudo.

### Project structure

- Entrypoint: `nosarch/apply.py`.
- Configuration of a run: `nosarch/source.py`.
- The engine: `nosarch/engine/`, with one step per kind of declaration in `nosarch/engine/steps/`.
- Definition code: `nosarch/modules/`.
- Themes: `nosarch/themes/`.
- Helpers used by the definition code: `nosarch/utils/`.
- Dotfiles: `dotfiles/`, with a separate mirrored root per module.
- JSON schema for the NosArch config: `config.schema.json`, generated from the classes in `nosarch/user_config.py`
  by `utils/config_schema_generator.py`.
- Tests: `tests/`.

### Internal docs

`docs/internal/` records code decisions, their reasons, and implementation traps that are hard to discover from the
source. Most code changes do not need an internal documentation update. The rules for when to add or change one are
in [AGENTS.md](../AGENTS.md#documentation).

- [Glossary](internal/glossary.md) — shared vocabulary (target system, definition code, deploying).
- [Engine](internal/engine.md) — why NosArch has its own, and the decisions behind how it runs.
- [Modules](internal/modules.md) — the module table and what registers what.
- [Files](internal/files.md) — how dotfiles are declared, tracked, and how changes are applied.
- [Packages](internal/packages.md) — declaring and tracking package changes.
- [Custom packages](internal/custom-packages.md) — where the PKGBUILDs live, and how a module declares one.
- [AppImages](internal/appimages.md) — how nosarch-package installs and removes AppImages.

### Operations

Maintainer procedures: setup, testing, releases, debugging.

- [Development](operations/development.md) — NosArch Works, testing.
