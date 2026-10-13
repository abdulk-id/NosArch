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
#
# `snap list` columns are Name, Version, Rev, Tracking, Publisher, Notes. Publisher is the
# fifth field. Notes is the sixth, and a snap with nothing in that column omits it.
_snap_installed() {
    snap list 2>/dev/null | awk 'NR > 1 && NF {
        notes = (NF >= 6 ? $6 : "")
        print $1 "\t" notes
    }'
}

# Public snap names from snapd's store catalog. snapd refreshes this file on a timer and replaces it atomically. The
# snap CLI uses it for tab completion too.
SNAP_STORE_NAMES=/var/cache/snapd/names

_snap_user_catalog() {
    printf '%s/nosarch/snap-store-names\n' "${XDG_CACHE_HOME:-$HOME/.cache}"
}

_snap_catalog_ready() {
    [ -r "$SNAP_STORE_NAMES" ] && [ -s "$SNAP_STORE_NAMES" ]
}

# Same endpoint and confinement filter snapd uses in catalog refresh; kept under the user's cache when snapd has not
# written its copy yet.
_snap_download_user_catalog() {
    _ensure_command curl
    _ensure_command python3
    _ensure_command mktemp

    cache=$(_snap_user_catalog)
    cache_dir=$(dirname -- "$cache")
    json_tmp=$(mktemp)
    names_tmp=$(mktemp)

    mkdir -p -- "$cache_dir"

    user_agent=$(snap version 2>/dev/null | awk '/^snap / { print "Snap/" $2; exit }')
    architecture=$(snap version 2>/dev/null | awk '/^architecture / { print $2; exit }')
    [ -n "$user_agent" ] || user_agent="Snap/unknown"
    [ -n "$architecture" ] || architecture="amd64"

    if ! curl -fsS \
        -H "Accept: application/hal+json" \
        -H "User-Agent: $user_agent" \
        -H "Snap-Device-Series: 16" \
        -H "Snap-Device-Architecture: $architecture" \
        -H "Snap-Classic: true" \
        -H "X-Ubuntu-Wire-Protocol: 1" \
        "https://api.snapcraft.io/api/v1/snaps/names?confinement=strict,classic" \
        -o "$json_tmp"
    then
        rm -f -- "$json_tmp" "$names_tmp"
        return 1
    fi

    if ! python3 - "$json_tmp" >"$names_tmp" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as catalog:
    payload = json.load(catalog)

for item in payload["_embedded"]["clickindex:package"]:
    name = item.get("package_name")
    if name:
        print(name)
PY
    then
        rm -f -- "$json_tmp" "$names_tmp"
        return 1
    fi

    rm -f -- "$json_tmp"
    mv -- "$names_tmp" "$cache"
}

_snap_store_names() {
    if _snap_catalog_ready; then
        cat -- "$SNAP_STORE_NAMES"
        return 0
    fi

    user_catalog=$(_snap_user_catalog)
    if [ -r "$user_catalog" ] && [ -s "$user_catalog" ]; then
        cat -- "$user_catalog"
        return 0
    fi

    gum style --foreground 10 "▸ Downloading snap store catalog..."
    if ! _snap_download_user_catalog; then
        return 1
    fi

    cat -- "$user_catalog"
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

    if ! candidates=$(_snap_store_names); then
        report_error "Could not load the snap store catalog. Check your network connection and try again."
        return 1
    fi

    if [ -z "$candidates" ]; then
        report_error "Snap store catalog is empty."
        return 1
    fi

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
