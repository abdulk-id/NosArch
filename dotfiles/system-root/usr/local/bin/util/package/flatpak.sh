# Managed by NosArch
#
# Flatpak for nosarch-package.

register_preview '[flatpak]' 'flatpak info {3}'

flatpak_summary() {
    printf '%s\n' "Install Flatpak packages"
}

# The module enables this library and installs the runtime in the same run, so the runtime can still be absent here on
# the run that enables Flatpak, or after it is removed by hand.
flatpak_available() {
    command -v flatpak >/dev/null 2>&1
}

flatpak_install() {
    if ! flatpak_available; then
        report_error "Flatpak is not available on this system."
        return 1
    fi

    for cmd in gum fzf; do
        _ensure_command "$cmd"
    done

    # APP_ID<TAB>NAME<TAB>DESCRIPTION
    candidates=$(
        flatpak remote-ls --app --columns=application,name,description |
            awk -F "$TAB_CHAR" '
                !seen[$1]++ {
                    printf "%s\t%s  (%s)\t%s\n", $1, $2, $1, $3
                }
            ' |
            sort -t "$TAB_CHAR" -k2,2f
    )

    pkg_selection=$(
        fzf_select "$candidates" 'printf "%s\n" "{}" | cut -f3' \
            --delimiter="$TAB_CHAR" \
            --with-nth=2 \
            --color 'pointer:green,marker:green'
    ) || return 0

    if [ -n "$pkg_selection" ]; then
        pkg_ids=$(printf '%s\n' "$pkg_selection" | cut -f1 | tr '\n' ' ')

        gum style --foreground 10 "▸ Installing Flatpak packages..."

        # shellcheck disable=SC2086
        if flatpak install --assumeyes $pkg_ids; then
            gum style --foreground 10 "✓ Installation complete!"
        else
            gum style --foreground 9 "x Installation failed."
            return 1
        fi
    fi
}

# Flatpak does not require sudo.
flatpak_update() {
    flatpak_available || return 0

    gum style --foreground 10 "▸ Updating Flatpak packages..."

    if flatpak update --assumeyes; then
        gum style --foreground 10 "✓ Flatpak packages updated!"
    else
        gum style --foreground 9 "x Flatpak package update failed."
        return 1
    fi
}

flatpak_entries() {
    flatpak_available || return 0

    flatpak list --app --columns=application | awk '{print "[flatpak]\tflatpak\t" $0}'
}

# Removes the selected rows, whose package names are in column 3.
flatpak_remove() {
    flatpak_available || return 0

    flatpak_pkgs=$(printf '%s\n' "$1" | cut -f 3 | tr '\n' ' ')

    gum style --foreground 10 "▸ Removing Flatpak packages..."

    # shellcheck disable=SC2086
    if flatpak uninstall --assumeyes $flatpak_pkgs; then
        gum style --foreground 10 "✓ Flatpak packages removed!"
    else
        gum style --foreground 9 "x Flatpak removal failed."
        return 1
    fi
}

flatpak_remove_unused() {
    flatpak_available || return 0

    gum style --foreground 10 "▸ Removing unused Flatpak packages..."

    success=true

    if flatpak uninstall --system --unused --assumeyes; then
        gum style --foreground 10 "✓ Unused Flatpak packages removed!"
    else
        gum style --foreground 9 "x Removing unused Flatpak packages failed."
        success=false
    fi

    if flatpak uninstall --user --unused --assumeyes; then
        gum style --foreground 10 "✓ Unused Flatpak user packages removed!"
    else
        gum style --foreground 9 "x Removing unused Flatpak user packages failed."
        success=false
    fi

    $success
}
