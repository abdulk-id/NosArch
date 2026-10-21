# Code Style Guidelines

- Include code attribution and a source link when copying or adapting code from elsewhere.
- Keep changes consistent with the surrounding code.

## Python style

- Ruff owns the mechanical style. Run `mise run format` before committing Python changes, and use `mise run lint` to
  check without changing anything. The pre-commit hook runs the same passes, so nothing reaches a commit unformatted.
- Prefer module-qualified local imports so call sites show where names come from:

    ```python
    import utils.chassis_type

    if utils.chassis_type.is_laptop():
        ...
    ```

- Use strict typing for NosArch code. Annotate function parameters, return values, and variables.
    - External integration code, such as Nautilus extensions, is exempt when host API types are unavailable.
- Import Decman as `import decman` and use its namespaces explicitly, such as `decman.Module`.
- Place Decman decorators such as `@pacman.packages` directly above the hook they register.
- Extend Decman-managed collections with `|=` or `+=`. Do not reassign existing Decman collections.

---

## Shell Script style

- Shell scripts must be strictly POSIX-compliant.
- Shell scripts must use `set -eu` for reliable error handling.
- Always use longer forms of command options when possible, because they make intent clear in context
  (e.g., `jq --raw-output` instead of `jq -r`).
- Organize every user-facing shell script into these sections:
    - `Utilities`: shared helpers, command checks, and constants.
    - `Features`: script-specific functionality.
    - `main()`: global option parsing and command dispatch.
- The `main "$@"` call should be at the end of the script, along with any finalization.
- User-facing scripts should provide `help`, `-h`, and `--help` for the help message.
- A `nosarch-*` script is discovered by the `nosarch` CLI, which reads its leading comment block for
  `nosarch:summary=`, `nosarch:hidden=true`, and optionally `nosarch:name=` / `nosarch:group=` when the
  filename stem does not split into a group and a name. Without a `summary` the command still routes, but
  it is listed with an empty description.
