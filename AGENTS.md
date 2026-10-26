# NosArch

NosArch is an Arch Linux dotfile and system configuration repo managed by Decman.

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

- Testing the definition code requires a dry-run as root, which you cannot do yourself. Ask the user to dry-run and
  report back.

## Formatting

- Run `mise format` before committing Python changes, or `mise lint` to only report.

## Searching

- Ignore `.drafts/` and `.worktrees/` when searching the repo. They contain stale copies of docs and code, not the
  current state.
