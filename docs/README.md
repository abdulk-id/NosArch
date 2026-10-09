# NosArch Docs

## Using NosArch

User manual is being worked on.

## Working on NosArch

It is recommended to work on NosArch from a machine running NosArch so changes can be tested live easily.

### How it works

`nosarch/source.py` configures decman: it registers the modules in `nosarch/modules/`, which declare which dotfiles,
packages, and systemd units each one deploys. On a run, decman installs what modules declare and removes what no
module declares anymore. Custom packages are regular pacman packages built from PKGBUILDs in
[NosArch-Packages](https://github.com/abdulk-id/NosArch-Packages) so decman manages them the same way.

### Project structure

- Entrypoint: `nosarch/source.py`, which configures decman behavior.
- Definition code: `nosarch/modules/`.
- Themes: `nosarch/themes/`.
- Custom decman plugins: `nosarch/plugins/`.
- Helpers used by the decman source: `nosarch/utils/`.
- Dotfiles deployed by decman: `dotfiles/`, with a separate mirrored root per module.
- JSON schema for the NosArch config: `config.schema.json`.
- Repo maintenance and test scripts: `tools/`.

### Internal docs

`docs/internal/` records code decisions, their reasons, and implementation traps that are hard to discover from the
source. Most code changes do not need an internal documentation update. The rules for when to add or change one are
in [AGENTS.md](../AGENTS.md#documentation).

- [Glossary](internal/glossary.md) — shared vocabulary (target system, definition code, deploying).
- [Modules](internal/modules.md) — the module table and what registers what.
- [Files](internal/files.md) — how dotfiles are declared, tracked, and how changes are applied.
- [Packages](internal/packages.md) — declaring and tracking package changes.
- [Custom packages](internal/custom-packages.md) — where the PKGBUILDs live, and how a module declares one.
- [AppImages](internal/appimages.md) — how nosarch-package installs and removes AppImages.

### Operations

Maintainer procedures: setup, testing, releases, debugging.

- [Development](operations/development.md) — NosArch Works, testing.
