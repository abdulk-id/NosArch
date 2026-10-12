# Managed by NosArch
#
# Snap for nosarch-package. See docs/internal/snap.md.
#
# No snap_update: snapd.timer refreshes on its own schedule, so updating from here would duplicate that work.

register_preview '[snap]' 'snap info {3}'

snap_summary() {
    printf '%s\n' "Install Snap packages"
}

# The module enables this library and installs snapd from the AUR in the same run, so the client can still be absent
# here on the run that enables Snap, or after snapd is removed by hand.
snap_available() {
    command -v snap >/dev/null 2>&1
}

# snapd holds squashfs mounts and refuses a refresh while one is in progress, which happens on a machine that has run
# an install or remove recently.
_snap_busy() {
    snap changes | awk 'NR > 1 && ($4 ~ /Doing|Undoing/) { print $1 }'
}

# snapd's socket has to be accepting before any snap command works, and the service being active says nothing about
# that, since snapd exits on its own when idle.
_snap_check_daemon() {
    if ! systemctl is-active --quiet snapd.socket; then
        report_error "snapd.socket is not running. Start it with: sudo systemctl start snapd.socket"
        return 1
    fi
}

# Base snaps are what every other snap is built on, so they are never offered for removal and never counted as
# leftovers. Both checks stand alone, so neither depends on the wording of one column.
snap_is_base() {
    snap_name=$1
    snap_notes=$2

    case "$snap_notes" in
        *base*)
            return 0
            ;;
    esac

    case "$snap_name" in
        bare|snapd|core|core[0-9]*|kernel-*)
            return 0
            ;;
    esac

    return 1
}

# Installed snaps, one per line, as name and Notes column.
_snap_installed() {
    snap list 2>/dev/null | awk 'NR > 1 && NF >= 5 { print $1 "\t" $5 }'
}

snap_install() {
    _ensure_command gum

    if ! snap_available; then
        report_error "Snap is not available on this system."
        return 1
    fi

    _ensure_command fzf
    _snap_check_daemon || return 1

    if busy=$(_snap_busy) && [ -n "$busy" ]; then
        report_error "Snap has work in progress (change $busy). Try again once it finishes."
        return 1
    fi

    candidates=$(snap find 2>/dev/null | awk 'NR > 1 && NF { print $1 }' | sort -u)

    selection=$(
        fzf_select "$candidates" 'snap info {1}' \
            --color 'pointer:green,marker:green'
    ) || return 0

    [ -n "$selection" ] || return 0

    gum style --foreground 10 "▸ Installing Snap packages..."

    success=true

    for snap_name in $selection; do
        # No --channel: the store's default track is what a search result resolves to, and
        # a classic snap has to be declared in the config rather than guessed at here.
        if snap install "$snap_name"; then
            gum style --foreground 10 "✓ Installed $snap_name"
        else
            gum style --foreground 9 "x Installing $snap_name failed."
            success=false
        fi
    done

    $success
}

# Base snaps are filtered out of the picker as well as the removal, so a user can't remove them.
snap_entries() {
    snap_available || return 0

    _snap_installed | while IFS="$TAB_CHAR" read -r snap_name snap_notes; do
        if snap_is_base "$snap_name" "$snap_notes"; then
            continue
        fi

        printf '[snap]\tsnap\t%s\n' "$snap_name"
    done
}

# Removes the selected rows, whose snap names are in column 3.
snap_remove() {
    snap_available || return 0

    snap_names=$(printf '%s\n' "$1" | cut -f 3 | tr '\n' ' ')

    gum style --foreground 10 "▸ Removing Snap packages..."

    # shellcheck disable=SC2086
    if snap remove $snap_names; then
        gum style --foreground 10 "✓ Snap packages removed!"
    else
        gum style --foreground 9 "x Snap removal failed."
        return 1
    fi
}

# A disabled snap is installed and running nothing, so it is what Snap has instead of a dependency graph. Removing one
# deletes its data, so the names are listed first.
snap_remove_unused() {
    snap_available || return 0
    _snap_check_daemon || return 1

    disabled=$(
        _snap_installed | while IFS="$TAB_CHAR" read -r snap_name snap_notes; do
            if snap_is_base "$snap_name" "$snap_notes"; then
                continue
            fi

            case "$snap_notes" in
                *disabled*)
                    printf '%s\n' "$snap_name"
                    ;;
            esac
        done
    )

    if [ -z "$disabled" ]; then
        gum style --foreground 10 "✓ No unused Snap packages found!"
        return 0
    fi

    gum style --foreground 10 "▸ Removing unused Snap packages..."
    # shellcheck disable=SC2086
    printf '  %s\n' $disabled

    # shellcheck disable=SC2086
    if snap remove $disabled; then
        gum style --foreground 10 "✓ Unused Snap packages removed!"
    else
        gum style --foreground 9 "x Removing unused Snap packages failed."
        return 1
    fi
}
