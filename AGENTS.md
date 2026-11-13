# NosArch

NosArch is an Arch Linux dotfile and system configuration repo. `docs/README.md` is the project overview.

## Documentation

Read before changing:

- `docs/internal/engine.md`: engine steps, dry-run behaviour, state, or anything that differs from decman.
- `docs/internal/hooks.md`: `on_change`, `on_enable`, `on_disable`, hook order, module names, or apply requests.
- `docs/internal/dotfiles.md`: how a file is declared and rendered.
- `docs/internal/packages.md`: pacman, AUR, Flatpak, Snap, Homebrew, or custom packages.
- `docs/internal/appimages.md`: AppImage install.
- `docs/internal/glossary.md`: the meaning of a term used in the docs.

`docs/operations/` holds maintainer setup, release, and debugging procedures.

Most code changes need no internal documentation change. Before adding to `docs/internal/`, ask what a maintainer would
get wrong without it; reading the code answers most questions.

- An internal page holds a reason that crosses files, or a trap the source does not show. A reason inside one function
  is a short comment beside it.
- Types and code record fields, control flow, and the lists of modules, paths, and commands. Link the source.
- When a documented decision changes, rewrite or remove the affected text. A new internal page needs a distinct,
  durable reason to exist.
- When the documentation and the code conflict, follow the code's conventions.

## Testing

- Definition code: `mise dryrun`.
- A real apply needs root; ask the user to run `mise apply`.
- Engine changes (`nosarch/engine/`): `mise run test-all`.
- More in `docs/operations/development.md`.

## Formatting

Run `mise format` before committing Python changes. `mise lint` only reports.

## Searching

Search the repo without `.worktrees/`, which holds worktrees checked out to other branches.
