# Managed by NosArch
#
# Leftover-data cleanup for nosarch-package. Sourced by nosarch-package, never run.
#
# Shipped by SystemModule rather than by a packaging module, because this has to stay
# available after the module is gone. Each module's on_disable offers to delete its data
# on the run that disables it, and declining leaves it behind with no way back to the
# offer. This is that way back.
#
# A method shows up here only while its library file is absent, since a missing library is
# what says its module is disabled. While the module is enabled the data is in use, so
# nothing is ever offered for it.
#
# The paths below mirror each module's on_disable. Keep the two in step.

# The user the leftover data belongs to. Running under sudo makes $HOME root's, and these
# paths are per-user for a reason.
CLEANUP_USER=${SUDO_USER:-$(id -un)}
CLEANUP_HOME=/home/$CLEANUP_USER

# System paths first, so they read as the thing being cleaned before the home directories.
_flatpak_leftovers() {
    printf '%s\n' \
        /var/lib/flatpak \
        "$CLEANUP_HOME/.local/share/flatpak" \
        "$CLEANUP_HOME/.var/app"
}

# No base-snap exception here: once snapd is gone the base snaps are just data, and every
# snap's settings are inside them.
_snap_leftovers() {
    printf '%s\n' \
        /var/lib/snapd \
        /snap \
        "$CLEANUP_HOME/snap"
}

_homebrew_leftovers() {
    printf '%s\n' \
        /home/linuxbrew \
        "$CLEANUP_HOME/.cache/Homebrew" \
        "$CLEANUP_HOME/.config/homebrew" \
        "$CLEANUP_HOME/.homebrew"
}

# The one command that has to run before the prefix goes. A cask can install files outside
# the prefix, so deleting the prefix leaves them behind with brew then holding no record
# they were ever installed. `brew uninstall` has no --all: list the installed casks and
# uninstall those, as the user, since brew refuses to run as root. Not the reason for
# cleanup existing, just the reason it does not leave the machine half-cleaned.
_homebrew_uninstall_casks() {
    brew_bin=/home/linuxbrew/.linuxbrew/bin/brew

    if [ ! -x "$brew_bin" ]; then
        return 0
    fi

    casks=$(
        sudo -u "$CLEANUP_USER" env HOMEBREW_NO_ENV_HINTS=1 "$brew_bin" list --cask -1 2>/dev/null |
            grep -E '^[A-Za-z0-9][A-Za-z0-9+_.@-]*$' || true
    )

    if [ -z "$casks" ]; then
        return 0
    fi

    # shellcheck disable=SC2086
    sudo -u "$CLEANUP_USER" env HOMEBREW_NO_ENV_HINTS=1 "$brew_bin" uninstall --cask $casks >/dev/null 2>&1 || true
}

# Flatpak apps register themselves by symlinking into the exports directories, so deleting
# the data leaves broken links in the user's applications menu. Gathered before the uninstall
# and removed after, because whether a link resolves is only settled once the data is gone.
_flatpak_dangling_entries() {
    apps_dir="$CLEANUP_HOME/.local/share/applications"

    [ -d "$apps_dir" ] || return 0

    for entry in "$apps_dir"/*; do
        [ -L "$entry" ] || continue

        case $(readlink -- "$entry") in
            /var/lib/flatpak/exports/*|"$CLEANUP_HOME"/.local/share/flatpak/exports/*)
                printf '%s\n' "$entry"
                ;;
        esac
    done
}

# What each disabled method left behind, as "method<TAB>path" rows. Nothing prints for a
# method whose module is still enabled, so the caller reads an empty list as "nothing to do".
cleanup_candidates() {
    for method in flatpak snap homebrew; do
        # A library file that is still here means the module is enabled, so its data is in use.
        [ -f "$PACKAGE_LIB_DIR/$method.sh" ] && continue

        case "$method" in
            flatpak) _flatpak_leftovers ;;
            snap) _snap_leftovers ;;
            homebrew) _homebrew_leftovers ;;
        esac |
            while IFS= read -r path; do
                if [ -e "$path" ] || [ -L "$path" ]; then
                    printf '%s\t%s\n' "$method" "$path"
                fi
            done
    done
}

# Deletes one method's leftovers, which arrive one path per line from the same
# `_<method>_leftovers` helper that listed them, so a path added to one is deleted by the
# other. One `sudo rm` per path, which the keepalive makes cheap.
_cleanup_remove_paths() {
    status=0

    while IFS= read -r path; do
        [ -n "$path" ] || continue

        if ! sudo rm -rf --force -- "$path"; then
            status=1
        fi
    done

    return "$status"
}

cleanup_method() {
    method=$1

    case "$method" in
        snap)
            # snapd holds squashfs mounts of its own, so the daemon comes down before
            # anything underneath it does.
            systemctl stop snapd.socket >/dev/null 2>&1 || true

            _snap_leftovers | _cleanup_remove_paths
            ;;
        flatpak)
            # Read before the data goes and removed after, because whether a link resolves
            # is only settled once the paths it points into are gone.
            links=$(_flatpak_dangling_entries)

            _flatpak_leftovers | _cleanup_remove_paths

            if [ -n "$links" ]; then
                # shellcheck disable=SC2086
                sudo rm -rf --force -- $links
            fi
            ;;
        homebrew)
            _homebrew_uninstall_casks

            _homebrew_leftovers | _cleanup_remove_paths
            ;;
    esac
}

# Deletes the leftovers of every method in the newline-or-space separated list. One
# authentication for the whole run, rather than one per method.
cleanup_each() {
    for method in $1; do
        gum style --foreground 10 "▸ Removing $method data..."

        if ! cleanup_method "$method"; then
            gum style --foreground 9 "x Removing $method data failed."
            return 1
        fi
    done
}

cleanup() {
    _ensure_command gum

    candidates=$(cleanup_candidates)

    if [ -z "$candidates" ]; then
        gum style --foreground 10 "✓ No leftover package data found."
        return 0
    fi

    gum style --foreground 10 "These packaging methods are disabled, but left data behind:"
    printf '%s\n' "$candidates" | awk -F '\t' '{ printf "    %-10s %s\n", $1, $2 }'

    gum style --foreground 9 "x Deleting them also deletes every app's settings and data. This cannot be undone."

    if ! gum confirm "Delete all of it?"; then
        gum style --foreground 10 "Nothing was deleted."
        return 0
    fi

    methods=$(printf '%s\n' "$candidates" | cut -f 1 | sort -u)

    if with_sudo cleanup_each "$methods"; then
        gum style --foreground 10 "✓ Package data removed."
    else
        return 1
    fi
}
