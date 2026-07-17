# Contributing to NosArch

NosArch is still a work in progress. Currently not accepting contributions.

The project is in the early stages and its conventions are still evolving.

There is no guarantee of acceptance, but you can still open an issue or a PR to report bugs and suggest features or improvements.

## Commit Messages

Write commit messages using the following format:

```
Area: Action summary
```

Some examples:

- `Scripts: Make all shell scripts POSIX-compliant`
- `System: Add vendor-based CPU and GPU setup`
- `Hyprland: Fix opening windows in wrong workspaces`

Common areas include:

- `Decman`: Decman-specific changes (which do not affect the system)
- `Dev`: Dev-related changes (made in the Dev module)
- `Repo`: Repository changes such as codebase documentation, repo config files (`.gitignore`, `.editorconfig` etc.), `opencode.jsonc` etc.
- `Scripts`: All user-facing shell scripts
- `System`: TODO: Broad category, needs better explanation

Message style:

- Use an imperative verb ("Add", "Fix", "Update", "Remove") rather than past tense ("Added", "Fixed").
- Keep the subject concise.
