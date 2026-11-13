# NosArch Docs

- [`user/`](user/manual-install.md): installing NosArch.
- `internal/`: decisions, their reasons, and traps the source does not show. Rules for adding to it are in
  [AGENTS.md](../AGENTS.md#documentation).
- [`operations/`](operations/development.md): maintainer setup and testing.

Work on NosArch from a machine running NosArch, so changes can be tested live.

`python -m nosarch` runs the engine. `nosarch/definition/source.py` builds its `Setup` from the modules in
`nosarch/definition/modules/`. Custom packages are built from PKGBUILDs in
[NosArch-Packages](https://github.com/abdulk-id/NosArch-Packages).
