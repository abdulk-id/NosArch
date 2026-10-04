# NosArch

NosArch is an Arch Linux dotfile and system configuration repo managed by Decman. See `docs/README.md` for the
project overview and structure, `docs/operations/` for maintainer procedures, and `docs/internal/` for design
decisions and traps.

## Documentation

Most code changes do not need an internal documentation change. Agents can read the code.

- `docs/internal/` is for decisions and their reasons, constraints that span components, and traps that are hard to
  discover from the source. Before adding a paragraph, ask what a maintainer would get wrong without it. If reading
  the code answers the question, leave it out.
- Do not document every feature, enumerate fields, narrate control flow, or maintain file catalogs. Types, tests, and
  code already record the implementation.
- When a documented decision or constraint changes, rewrite or remove the affected text. Do not append another
  account of the new behavior. A new internal page needs a distinct, durable reason to exist.
- `docs/operations/` holds maintainer setup, release, and debugging procedures.

## Testing

- Testing the definition code requires a decman dry-run as root, which you cannot do yourself. Ask the user to run
  it and report back any errors rather than attempting it.

## Formatting

- Run `mise run format` before committing Python changes, or `mise run lint` to only report. Both are Ruff, the same
  formatter Zed runs on save, so an unformatted file never turns into a reformat-only commit.

