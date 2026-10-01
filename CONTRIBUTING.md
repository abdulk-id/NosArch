# Contributing to NosArch

NosArch is in the early stages and its conventions are still evolving.

There is no guarantee of acceptance, but you can still open an issue or a PR to report bugs and suggest features or improvements.

## Commit Messages

Write commit messages in the following format: `Area: Action summary`

Areas:

- `Decman`: Decman-specific changes (such as decman's configuration, the homebrew plugin for decman).
- `<Module-Name>`: Changes in the definition code of a module.
- `Repo`: Repository changes such as documentation, repo config files (`.gitignore` etc.), `opencode.jsonc` etc.
- `Scripts`: Changes targeting user-facing shell scripts in multiple modules.
- `Packages`: Adding, modifying or removing a custom package.
- `Packages(update)`: Updating a custom package's version.

Some examples:

- `Scripts: Make all shell scripts POSIX-compliant`
- `System: Add vendor-based CPU and GPU setup`
- `Desktop: Revert Firefox extension window rule`
