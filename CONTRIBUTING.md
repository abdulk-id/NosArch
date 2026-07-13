# Contributing to NosArch

Currently not accepting contributions.

You can still apen an issue or a PR.

---

## Code Style Guidelines

### Shell Script style

All shell scripts must be strictly POSIX-compliant.

NosArch shell script example:

```sh
#!/bin/sh

set -eu

. "some-script"

show_help() {
    cat <<EOF
Usage:
    nosarch-script-name <command> [actions]

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

    case "${1:-}" in
        ...
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
