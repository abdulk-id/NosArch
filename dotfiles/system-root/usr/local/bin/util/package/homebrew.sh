# Managed by NosArch
#
# Homebrew for nosarch-package. brew cannot run as root, so nothing here uses sudo.

# Walker and other menu hosts often run with a minimal PATH, so `command -v brew` misses the
# NosArch prefix even when Homebrew is installed. The search order matches plugins/homebrew.py.
_HOMEBREW_BREW=

_homebrew_resolve_brew() {
    if [ -n "$_HOMEBREW_BREW" ]; then
        return 0
    fi

    if command -v brew >/dev/null 2>&1; then
        _HOMEBREW_BREW=$(command -v brew)
        return 0
    fi

    for candidate in \
        /home/linuxbrew/.linuxbrew/bin/brew \
        /opt/homebrew/bin/brew \
        /usr/local/bin/brew
    do
        if [ -x "$candidate" ]; then
            _HOMEBREW_BREW=$candidate
            return 0
        fi
    done

    if [ -n "${HOME:-}" ] && [ -x "$HOME/.linuxbrew/bin/brew" ]; then
        _HOMEBREW_BREW="$HOME/.linuxbrew/bin/brew"
        return 0
    fi

    return 1
}

_homebrew_preview_brew=brew

if _homebrew_resolve_brew; then
    _homebrew_preview_brew=$_HOMEBREW_BREW
fi

register_preview '[homebrew]' "case {2} in
    formula)
        $_homebrew_preview_brew info --formula {3}
        ;;
    cask)
        $_homebrew_preview_brew info --cask {3}
        ;;
esac"

homebrew_summary() {
    printf '%s\n' "Install Homebrew formulae and casks"
}

# The module enables this library and bootstraps the prefix in the same run, so brew can still be absent here on the
# run that enables Homebrew, or after the prefix is removed by hand.
homebrew_available() {
    _homebrew_resolve_brew
}

# brew search lists names only, so the summary comes from the preview. Formulae come first because that is what
# installs cleanly on Linux. A cask is a macOS application, and brew refuses most of them here.
homebrew_install() {
    _ensure_command gum

    if ! _homebrew_resolve_brew; then
        report_error "Homebrew is not available on this system."
        return 1
    fi

    brew=$_HOMEBREW_BREW

    _ensure_command fzf

    candidates=$(
        {
            "$brew" search --formula 2>/dev/null |
                awk 'NF { print "formula\t" $1 }'
            "$brew" search --cask 2>/dev/null |
                awk 'NF { print "cask\t" $1 }'
        } | sort -u
    )

    selection=$(
        fzf_select "$candidates" "case {1} in
            formula)
                $brew info --formula {2}
                ;;
            cask)
                $brew info --cask {2}
                ;;
        esac" \
            --delimiter="$TAB_CHAR" \
            --with-nth=2 \
            --color 'pointer:green,marker:green'
    ) || return 0

    [ -n "$selection" ] || return 0

    formulae=$(
        printf '%s\n' "$selection" |
            awk -F "$TAB_CHAR" '$1 == "formula" { print $2 }' |
            tr '\n' ' '
    )

    casks=$(
        printf '%s\n' "$selection" |
            awk -F "$TAB_CHAR" '$1 == "cask" { print $2 }' |
            tr '\n' ' '
    )

    success=true

    if [ -n "$formulae" ]; then
        gum style --foreground 10 "▸ Installing Homebrew formulae..."

        # shellcheck disable=SC2086
        if HOMEBREW_NO_ENV_HINTS=1 "$brew" install --formula $formulae; then
            gum style --foreground 10 "✓ Homebrew formulae installed!"
        else
            gum style --foreground 9 "x Homebrew formula installation failed."
            success=false
        fi
    fi

    if [ -n "$casks" ]; then
        gum style --foreground 10 "▸ Installing Homebrew casks..."

        # shellcheck disable=SC2086
        if HOMEBREW_NO_ENV_HINTS=1 "$brew" install --cask $casks; then
            gum style --foreground 10 "✓ Homebrew casks installed!"
        else
            gum style --foreground 9 "x Homebrew cask installation failed."
            success=false
        fi
    fi

    $success
}

homebrew_update() {
    _homebrew_resolve_brew || return 0

    brew=$_HOMEBREW_BREW

    # Homebrew does not require sudo
    gum style --foreground 10 "▸ Updating Homebrew packages..."

    if HOMEBREW_NO_ENV_HINTS=1 "$brew" upgrade --greedy --yes --quiet; then
        gum style --foreground 10 "✓ Homebrew packages updated!"
    else
        gum style --foreground 9 "x Homebrew package update failed."
        return 1
    fi
}

homebrew_entries() {
    _homebrew_resolve_brew || return 0

    brew=$_HOMEBREW_BREW

    {
        "$brew" list --formula --installed-on-request | awk '{print "[homebrew]\tformula\t" $0}'
        "$brew" list --cask | awk '{print "[homebrew]\tcask\t" $0}'
    }
}

# Removes the selected rows. Column 2 says which list a name came from, since brew
# uninstalls a formula and a cask through different flags.
homebrew_remove() {
    _homebrew_resolve_brew || return 0

    brew=$_HOMEBREW_BREW

    formulae=$(
        printf '%s\n' "$1" |
            awk -F "$TAB_CHAR" '$2 == "formula" { print $3 }' |
            tr '\n' ' '
    )

    casks=$(
        printf '%s\n' "$1" |
            awk -F "$TAB_CHAR" '$2 == "cask" { print $3 }' |
            tr '\n' ' '
    )

    success=true

    if [ -n "$formulae" ]; then
        gum style --foreground 10 "▸ Removing Homebrew formulae..."

        # shellcheck disable=SC2086
        if "$brew" uninstall --formula $formulae; then
            gum style --foreground 10 "✓ Homebrew formulae removed!"
        else
            gum style --foreground 9 "x Homebrew formula removal failed."
            success=false
        fi

        echo
    fi

    if [ -n "$casks" ]; then
        gum style --foreground 10 "▸ Removing Homebrew casks..."

        # shellcheck disable=SC2086
        if "$brew" uninstall --cask $casks; then
            gum style --foreground 10 "✓ Homebrew casks removed!"
        else
            gum style --foreground 9 "x Homebrew cask removal failed."
            success=false
        fi
    fi

    $success
}

homebrew_remove_unused() {
    _homebrew_resolve_brew || return 0

    brew=$_HOMEBREW_BREW

    gum style --foreground 10 "▸ Removing unused Homebrew packages..."

    if "$brew" cleanup; then
        gum style --foreground 10 "✓ Unused Homebrew packages removed!"
    else
        gum style --foreground 9 "x Removing unused Homebrew packages failed."
        return 1
    fi
}
