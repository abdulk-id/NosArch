# Code Style Guidelines

- Include code attribution and a source link when copying or adapting code from elsewhere.

## Python style

NosArch follows PEP 8. Keep changes consistent with the surrounding code.

### General Python

- Use four spaces for indentation and two blank lines between top-level declarations.
- Prefer double-quoted strings.
- Group imports into standard library, third-party, and local imports. Avoid wildcard imports.
- Prefer module-qualified local imports so call sites show where names come
  from:

    ```python
    import utils.chassis_type

    if utils.chassis_type.is_laptop():
        ...
    ```

- Use strict typing for NosArch code. Annotate function parameters, return values, and meaningful variables with
  modern syntax such as `list[str]` and `X | None`.
    - External integration code, such as Nautilus extensions, is exempt when host API types are unavailable.
- Use `PascalCase` for classes, `snake_case` for functions and variables, and `UPPER_SNAKE_CASE` for constants.

### NosArch and Decman

- Keep ownership aligned with the repository structure: system changes in `system.py`, desktop changes in `desktop.py`,
  themes in `theme.py`, profile changes in the matching setup or usage-profile module,
  and reusable logic in `nosarch/utils/`.
- Import Decman as `import decman` and use its namespaces explicitly, such as `decman.Module`.
- Decman modules should subclass `decman.Module`, initialize it with a stable name, and expose resources through
  the appropriate hook.
- Place Decman decorators such as `@pacman.packages` directly above the hook they register.
- Preserve hook return types: sets for packages and services, dictionaries for files, directories, symlinks, and
  per-user resources.
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
- Comment system-specific behavior, workarounds, and adapted code.
- Use `shellcheck` to lint shell scripts.
- Keep shell scripts consistent with existing code.

### User-facing Shell Script Template:

```sh
#!/bin/sh

set -eu

. "some-script"

show_help() {
    cat <<EOF
Usage:
    nosarch-script-name [options] <command> [actions]

Options:
    -g, --global-option         A global option

Commands:
    simple-cmd                  Simple command
    actions-cmd <action>        Command with required actions
    opt-actions-cmd [action]    Command with optional actions (default: default-value)
    help                        Show this help message

actions-cmd actions:
    action1                     Action 1
    action2                     Action 2

opt-actions-cmd actions:
    action1                     Action 1
    action2                     Action 2
EOF
}

## === Utilities ===
# Example function
# _ensure_command() {
#     if ! command -v "$1" >/dev/null 2>&1; then
#         echo "Error: $1 is required but not found."
#         exit 1
#     fi
# }

## === Features ===


## ===
main() {
    if [ "$#" -eq 0 ]; then
        show_help
        return
    fi

    # Global options
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --global-option|-g)
                # Do something
                shift
                ;;
            --)
                shift
                break
                ;;
            -*)
                echo "Unknown option: $1" >&2
                exit 1
                ;;
            *)
                break
                ;;
        esac
    done

    # Commands and actions
    case "${1:-}" in
        simple-cmd)
            # Do something
            ;;
        actions-cmd)
            case "${2:-}" in
                action1)
                    # Do something
                    ;;
                action2)
                    # Do something
                    ;;
                *)
                    echo "Unknown action: $2"
                    show_help
                    exit 1
                    ;;
            esac
            ;;
        opt-actions-cmd)
            case "${2:-}" in
                action1)
                    # Do something
                    ;;
                action2)
                    # Do something
                    ;;
                "")
                    if [ "$#" -ne 1 ]; then
                        echo "Unknown trailing arguments" >&2
                        show_help
                        exit 1
                    fi
                    # Do default action
                    ;;
                *)
                    echo "Unknown action: $2"
                    show_help
                    exit 1
                    ;;
            esac
            ;;
        help|-h|--help)
            show_help
            ;;
        *)
            echo "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
```
