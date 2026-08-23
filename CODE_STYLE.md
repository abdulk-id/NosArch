# Code Style Guidelines

- Include code attribution and a source link when copying or adapting code from elsewhere.
- Keep changes consistent with the surrounding code.

## Python style

NosArch follows PEP 8.

### General Python

- Use two blank lines between top-level declarations.
- Prefer double-quoted strings.
- Group imports into standard library, third-party, and local imports. Avoid wildcard imports.
- Prefer module-qualified local imports so call sites show where names come from:

    ```python
    import utils.chassis_type

    if utils.chassis_type.is_laptop():
        ...
    ```

- Use strict typing for NosArch code. Annotate function parameters, return values, and variables.
    - External integration code, such as Nautilus extensions, is exempt when host API types are unavailable.
- Use `PascalCase` for classes, `snake_case` for functions and variables, and `UPPER_SNAKE_CASE` for constants.

### NosArch and Decman

- Import Decman as `import decman` and use its namespaces explicitly, such as `decman.Module`.
- Decman modules should subclass `decman.Module` and expose resources through the appropriate hook.
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
