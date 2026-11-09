# NosArch

NosArch is an Arch Linux dotfile and system configuration repo, deployed by its own engine. See `docs/README.md` for the
project overview and structure, `docs/operations/` for maintainer procedures, and `docs/internal/` for design
decisions and traps.

## Documentation

See `docs/README.md` for the project overview and structure.

- `docs/internal/` is for decisions and their reasons, constraints that span components, and traps that are hard to
  discover from the source. Before adding a paragraph, ask what a maintainer would get wrong without it. If reading
  the code answers the question, leave it out.
- `docs/operations/` holds maintainer setup, release, and debugging procedures.

Most code changes do not need an internal documentation change.

- When the documentation and existing code conflict, follow the code's conventions, and in your final reply, list all
  the inconsistencies you found.
- When a documented decision or constraint changes, rewrite or remove the affected text only.

## Testing

- Test definition code with `nosarch/apply.py --dry-run` (or `mise run dry-run-quick`). It needs no root, so run it
  yourself. A real apply needs root, so ask the user to run `nosarch/apply.py` when a change has to be applied.
- Run `mise run test-all` after changing the engine (`nosarch/engine/`).

## Formatting

- Run `mise format` before committing Python changes, or `mise lint` to only report.

## Searching

- Ignore `.drafts/` and `.worktrees/` when searching the repo. They contain stale copies of docs and code, not the
  current state.
