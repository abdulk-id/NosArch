# Managed by NosArch
#
# Shared helpers for the nosarch-package method libraries. Sourced, never run.

# shellcheck disable=SC2034  # Read by the libraries and by nosarch-package that source this file.
TAB_CHAR=$(printf '\t')

# The fzf preview arms the method libraries register, collected while they are sourced. fzf runs --preview in a shell
# of its own, where no function from this script exists, so an arm is text rather than a call.
PREVIEW_CASES=""

register_preview() {
    PREVIEW_CASES="${PREVIEW_CASES}    \"$1\")
        $2
        ;;
"
}

# Runs fzf over "$1" with the bindings every NosArch picker shares. Anything left over is passed to fzf, so a caller
# adds its own delimiter and colour.
#
# The candidates arrive as an argument rather than on stdin because the flags have to live somewhere. POSIX sh has no
# arrays, so handing them out through a variable would mean eval at every call site.
fzf_select() {
    candidates=$1
    preview=$2
    shift 2

    if [ -z "$candidates" ]; then
        return 0
    fi

    printf '%s\n' "$candidates" | fzf \
        --multi \
        --preview "$preview" \
        --preview-label 'alt-p: toggle description, alt-j/k: scroll description, tab: multi-select' \
        --preview-label-pos 'bottom' \
        --preview-window 'down:55%:wrap' \
        --bind 'alt-p:toggle-preview' \
        --bind 'alt-d:preview-half-page-down,alt-u:preview-half-page-up' \
        --bind 'alt-k:preview-up,alt-j:preview-down' \
        "$@"
}

_ensure_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Error: $1 is required but not found."
        exit 1
    fi
}

update_db() {
    if command -v updatedb >/dev/null 2>&1; then
        sudo updatedb
    fi
}

# Report a result to the user.
#
# Installing can run with no terminal attached. A .desktop entry or a menu can launch it detached, and gum's output
# then goes nowhere. Fall back to a dialog in that case, and stay quiet when there is no dialog to show.
_notify_dialog() {
    kind=$1
    message=$2

    if [ -t 1 ]; then
        return 0
    fi

    if ! command -v zenity >/dev/null 2>&1; then
        return 0
    fi

    zenity --"$kind" \
        --title="NosArch packages" \
        --text="$message" \
        --width=400 \
        >/dev/null 2>&1 || true
}

report_ok() {
    gum style --foreground 10 "✓ $1"
    _notify_dialog "info" "$1"
}

report_error() {
    gum style --foreground 9 "x $1"
    _notify_dialog "error" "$1"
}

# Runs "$@" with the sudo credential held open, so a command that calls sudo more than once asks for the password
# once. The trap covers the caller exiting early, which is why it is set here and not inside the command.
with_sudo() {
    gum style --foreground 10 "▸ Authenticating..."

    if ! start_sudo_keepalive; then
        report_error "Authentication failed."
        return 1
    fi

    trap 'stop_sudo_keepalive' 0
    echo

    # set -e would exit before the keepalive is stopped.
    status=0
    "$@" || status=$?

    stop_sudo_keepalive
    trap - 0

    return "$status"
}
