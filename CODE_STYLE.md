# Code Style Guidelines

## Python style

TODO

## Shell Script style

- All shell scripts must be strictly POSIX-compliant.
- Always use longer forms of flags when possible (e.g., `--option` instead of `-o`).

### Example NosArch shell script:

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
