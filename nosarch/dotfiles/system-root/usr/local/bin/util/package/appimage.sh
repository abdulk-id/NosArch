# Managed by NosArch
#
# AppImages for nosarch-package. See docs/internal/appimages.md.

register_preview '[appimage]' 'grep -E "^(Name|Exec|Icon)=" {5}'

appimage_summary() {
    printf '%s\n' "Install AppImages from files, or ask for files when given none"
}

# Where installed AppImages live, and the registry that tracks them. AppImages are
# per-user: installing one needs no sudo, and no install can touch another user's copy.
APPIMAGE_STORE="$HOME/.local/share/appimages"
APPIMAGE_REGISTRY="$HOME/.local/share/nosarch/appimages.list"
APPIMAGE_APPLICATIONS="$HOME/.local/share/applications"
APPIMAGE_ICONS="$HOME/.local/share/icons/hicolor"
APPIMAGE_BIN="$HOME/.local/bin"

# One TSV record per installed AppImage:
#   id, display name, AppImage path, .desktop file, icon file
#
# The id is the slug every path is built from, which is what lets a removal delete
# exactly what the install created.
_appimage_records() {
    if [ -f "$APPIMAGE_REGISTRY" ]; then
        cat -- "$APPIMAGE_REGISTRY"
    fi
}

# Replace the registry with whatever arrives on stdin, so an interrupted run can never
# leave a half-written registry behind.
_appimage_registry_replace() {
    _ensure_command mktemp

    mkdir -p -- "$(dirname -- "$APPIMAGE_REGISTRY")"

    registry_tmp=$(mktemp)
    cat > "$registry_tmp"
    mv -- "$registry_tmp" "$APPIMAGE_REGISTRY"
}

_appimage_record_register() {
    record_id=$1
    record=$2

    {
        _appimage_records | awk -F "$TAB_CHAR" -v id="$record_id" '$1 != id'
        printf '%s\n' "$record"
    } | _appimage_registry_replace
}

_appimage_record_forget() {
    _appimage_records | awk -F "$TAB_CHAR" -v id="$1" '$1 != id' | _appimage_registry_replace
}

# A slug that is safe to build a filename and a desktop entry filename from.
_appimage_slug() {
    printf '%s' "$1" |
        tr '[:upper:]' '[:lower:]' |
        tr -c 'a-z0-9._-' '-' |
        sed 's/-\{2,\}-/-/g; s/^-//; s/-$//'
}

# A .desktop Name is one line of plain text and the registry is tab-separated, so drop
# what would break either.
_appimage_display_name() {
    printf '%s' "$1" |
        tr '\t\n\r' '   ' |
        tr -d "\"\\'" |
        sed 's/  */ /g; s/^ //; s/ $//'
}

# Pull the bundle's .desktop file and candidate icons out of an AppImage.
#
# Pattern extraction keeps this cheap: a bare `--appimage-extract` writes the whole
# bundle, often hundreds of megabytes, into a tmpfs. Type 1 AppImages and anything
# non-conforming fail here, which is what the generated-entry fallback is for.
_appimage_extract() {
    appimage=$1
    workdir=$2

    (
        cd -- "$workdir" &&
            "$appimage" --appimage-extract \
                '*.desktop' '*.png' '*.svg' '*.xpm' 'usr/share/icons/*' >/dev/null 2>&1
    )
}

# The bundle's .desktop file, shallowest match first: the AppImage spec puts one at the
# root, most toolchains ship it under usr/share/applications.
_appimage_find_desktop_file() {
    find "$1" -type f -name '*.desktop' 2>/dev/null |
        awk -F '/' '{ print NF "\t" $0 }' |
        sort -k 1,1n -k 2 |
        head -n 1 |
        cut -f 2-
}

# Value of a key in a .desktop file, first match only. Prints nothing when given no file,
# which is the normal case for an AppImage that ships no entry. The keys are literals
# chosen by this script rather than input, so interpolating one into the pattern is safe.
_desktop_field() {
    if [ -z "$1" ]; then
        return 0
    fi

    sed -n "s/^$2=//p" "$1" 2>/dev/null | head -n 1 | sed 's/[[:space:]]*$//'
}

# The icon the bundle's .desktop file names, else the first image at the root of the bundle.
_appimage_find_icon() {
    squashfs_root=$1
    icon_name=$2

    if [ -n "$icon_name" ]; then
        icon_file=$(
            find "$squashfs_root" -type f \
                \( -name "$icon_name.png" -o -name "$icon_name.svg" -o -name "$icon_name.xpm" \) 2>/dev/null |
                sort |
                head -n 1
        )

        if [ -n "$icon_file" ]; then
            printf '%s' "$icon_file"
            return 0
        fi
    fi

    find "$squashfs_root" -maxdepth 1 -type f \
        \( -name '*.png' -o -name '*.svg' -o -name '*.xpm' \) 2>/dev/null |
        sort |
        head -n 1
}

# hicolor indexes icons by their real pixel size. `file` is not part of any package
# NosArch requires, so fall back to the size most AppImages ship.
_appimage_icon_dir() {
    icon=$1

    case "$icon" in
        *.svg)
            printf 'scalable'
            return 0
            ;;
    esac

    if command -v file >/dev/null 2>&1; then
        size=$(file --brief -- "$icon" 2>/dev/null | sed -n 's/.*[ ,]\([0-9]\{1,4\}\) x \([0-9]\{1,4\}\).*/\1x\2/p')

        if [ -n "$size" ]; then
            printf '%s' "$size"
            return 0
        fi
    fi

    printf '512x512'
}

# The icon name for an app's id, whether or not an icon was found for it. Shared with
# hicolor, where the file has to be named after it.
_appimage_icon_name() {
    printf 'nosarch-appimage-%s' "$1"
}

# Rewrite the four keys in a bundled entry that name something inside the AppImage, and
# pass everything else through. Only the command is swapped out: the arguments and any
# field codes belong to the app, so %U still passes files and a [Desktop Action] keeps its
# own flags. The command is the first whitespace-delimited token after `Exec=`.
_appimage_adapt_desktop_file() {
    awk -v exec_path="$2" -v icon_name="$3" '
        /^Exec=/ {
            sub(/^Exec=[^[:space:]]*/, "Exec=" exec_path)
            print
            next
        }
        /^TryExec=/ { next }
        /^DBusActivatable=/ { print "DBusActivatable=false"; next }
        # The bundled name resolves only inside the mounted bundle. Naming no icon is
        # honest here: a menu shows a generic icon rather than a broken one.
        /^Icon=/ {
            if (icon_name != "") print "Icon=" icon_name
            next
        }
        { print }
    ' "$1"
}

# The launcher entry for an installed AppImage, adapted from the one in the bundle.
#
# The bundle's entry is the app's own and carries what only the app knows: StartupWMClass
# (without which no window rule can match it), MimeType, StartupNotify, the %U/%F field
# codes, localized names, and any [Desktop Action ...] groups. All of that is kept, so
# this is a rewrite of four keys rather than a new file:
#   Exec                 points at AppRun inside the bundle
#   TryExec              likewise, and a launcher that cannot find it hides the entry
#   DBusActivatable=true tells the launcher to ignore Exec and D-Bus activate a service
#                        that only exists while the AppImage is mounted
#   Icon                 the bundled name resolves only inside the mount
#
# A bundle with no usable entry still gets one, generated rather than adapted. Prints the
# path written.
_appimage_write_desktop_file() {
    id=$1
    name=$2
    appimage_path=$3
    icon_path=$4
    desktop_source=$5
    desktop_file="$APPIMAGE_APPLICATIONS/nosarch-appimage-$id.desktop"

    mkdir -p -- "$APPIMAGE_APPLICATIONS"

    if [ -n "$desktop_source" ]; then
        _appimage_adapt_desktop_file "$desktop_source" "$appimage_path" "$(_appimage_icon_name "$id")" \
            > "$desktop_file"

        # A bundle can ship a malformed entry, and passing it through verbatim would leave
        # an entry no menu can read. desktop-file-utils is not a package NosArch requires,
        # so this is best-effort: without it, the adapted entry is used unchecked.
        if ! command -v desktop-file-validate >/dev/null 2>&1 ||
            desktop-file-validate "$desktop_file" >/dev/null 2>&1; then
            printf '%s' "$desktop_file"
            return 0
        fi
    fi

    # No bundled entry, or one that does not validate. Deliberately minimal: every key here
    # is one whose absence the desktop entry spec allows.
    {
        printf '[Desktop Entry]\n'
        printf 'Type=Application\n'
        printf 'Name=%s\n' "$name"
        printf 'Exec=%s\n' "$appimage_path"

        if [ -n "$icon_path" ]; then
            printf 'Icon=%s\n' "$(_appimage_icon_name "$id")"
        fi

        printf 'Terminal=false\n'
        printf 'DBusActivatable=false\n'
        printf '\n'
    } > "$desktop_file"

    printf '%s' "$desktop_file"
}

# Install an app's icon into hicolor, and print where it landed. Prints nothing when the
# bundle ships no icon, which is not an error: the entry is simply written without one.
_appimage_install_icon() {
    icon_source=$1
    id=$2

    if [ -z "$icon_source" ]; then
        return 0
    fi

    # hicolor is keyed on the file extension, and a bundled icon can have none.
    extension=${icon_source##*.}
    extension=${extension##*.}

    case "$extension" in
        png|svg|xpm)
            extension=".$extension"
            ;;
        *)
            extension=".png"
            ;;
    esac

    icon_path="$APPIMAGE_ICONS/$(_appimage_icon_dir "$icon_source")/apps/$(_appimage_icon_name "$id")$extension"

    mkdir -p -- "$(dirname -- "$icon_path")"
    cp -- "$icon_source" "$icon_path"

    printf '%s' "$icon_path"
}

# Keep the desktop and icon caches in step with what was just written.
_appimage_refresh_caches() {
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$APPIMAGE_APPLICATIONS" >/dev/null 2>&1 || true
    fi

    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache --force --quiet "$APPIMAGE_ICONS" >/dev/null 2>&1 || true
    fi
}

# What the app calls itself: the Name from its own .desktop file, else the filename with
# the AppImage suffix dropped. A Type 1 AppImage cannot be extracted at all, and this is the
# path that keeps it installable.
_appimage_resolve_name() {
    desktop_source=$1
    source_file=$2

    name=""

    if [ -n "$desktop_source" ]; then
        name=$(_desktop_field "$desktop_source" Name)
    fi

    if [ -z "$name" ]; then
        name=$(basename -- "$source_file")
        name=${name%.AppImage}
        name=${name%.appimage}
    fi

    _appimage_display_name "$name"
}

# Install one AppImage: store the binary, integrate it with the desktop, record it.
_install_appimage() (
    # A subshell, so the work directory is cleaned up on every exit path.
    source_file=$1

    if [ ! -f "$source_file" ]; then
        report_error "Not a file: $source_file"
        return 1
    fi

    workdir=$(mktemp --directory)
    trap 'rm -rf -- "$workdir"' 0

    # Extracted from a copy, so a bundle that misbehaves on --appimage-extract cannot
    # touch the file the user still has.
    bundle="$workdir/$(basename -- "$source_file")"
    cp -- "$source_file" "$bundle"
    chmod 0755 -- "$bundle"

    squashfs_root=""
    desktop_source=""

    if _appimage_extract "$bundle" "$workdir"; then
        squashfs_root="$workdir/squashfs-root"
        desktop_source=$(_appimage_find_desktop_file "$squashfs_root")
    fi

    name=$(_appimage_resolve_name "$desktop_source" "$source_file")
    id=$(_appimage_slug "$name")

    if [ -z "$id" ]; then
        id="appimage"
    fi

    # Re-installing an app reuses its id, so the new binary replaces the old one. An upstream that renames the app
    # between releases gets a new id, and its predecessor is then a separate entry to remove.
    appimage_path="$APPIMAGE_STORE/$id.AppImage"

    mkdir -p -- "$APPIMAGE_STORE" "$APPIMAGE_APPLICATIONS" "$APPIMAGE_BIN"
    mv -- "$bundle" "$appimage_path"

    icon_source=""
    icon_name=""

    if [ -n "$squashfs_root" ]; then
        icon_name=$(_desktop_field "$desktop_source" Icon)
        icon_source=$(_appimage_find_icon "$squashfs_root" "$icon_name")
    fi

    icon_path=$(_appimage_install_icon "$icon_source" "$id")
    desktop_file=$(_appimage_write_desktop_file \
        "$id" "$name" "$appimage_path" "$icon_path" "$desktop_source")

    ln -sfn -- "$appimage_path" "$APPIMAGE_BIN/$id"

    _appimage_record_register "$id" \
        "$id$TAB_CHAR$name$TAB_CHAR$appimage_path$TAB_CHAR$desktop_file$TAB_CHAR$icon_path"

    _appimage_refresh_caches

    report_ok "Installed $name"
)

# The files to install, when the user has not named any. Exits non-zero when the dialog
# is cancelled, which the caller reads as "install nothing".
#
# The zenity check lives in the caller: a command substitution runs in a subshell, so an
# exit from in here would be swallowed by the caller's `|| return 0` and the user would get
# silence instead of the reason.
_pick_appimages() {
    separator='
'
    # GTK's own complaints go with it: with no display there is no dialog to show.
    zenity --file-selection \
        --multiple \
        --separator="$separator" \
        --title="Install AppImage" \
        --file-filter="*.AppImage *.appimage" \
        --file-filter="* | All files" 2>/dev/null
}

# Ask before installing one file. Returns non-zero when the user declines.
_confirm_appimage() {
    zenity --question \
        --title="Install AppImage" \
        --text="Install $(basename -- "$1")?" \
        --width=400 \
        --ok-label="Install" \
        --cancel-label="Cancel" \
        >/dev/null 2>&1
}

appimage_install() {
    _ensure_command gum

    confirm=false

    # Option first, so the file list can be empty and the dialog can ask for it.
    if [ "${1:-}" = "--confirm" ]; then
        confirm=true
        shift
    fi

    if [ "$#" -eq 0 ]; then
        _ensure_command zenity

        selection=$(_pick_appimages) || return 0

        if [ -z "$selection" ]; then
            return 0
        fi

        # One path per line becomes one argument per path. This has to be inline rather than a helper: `set --` inside
        # a function would replace that function's own parameters, which are restored on return, and the file list
        # would be lost.
        old_ifs=$IFS
        IFS='
'
        set -f

        # shellcheck disable=SC2086
        set -- $selection

        IFS=$old_ifs
        set +f
    fi

    if $confirm; then
        _ensure_command zenity
    fi

    success=true

    for source_file in "$@"; do
        if $confirm; then
            # A declined file is skipped, not an error: declining is a valid answer.
            _confirm_appimage "$source_file" || continue
        fi

        _install_appimage "$source_file" || success=false
        echo
    done

    $success
}

appimage_list() {
    _ensure_command gum

    records=$(_appimage_records)

    if [ -z "$records" ]; then
        gum style --foreground 10 "No AppImages installed."
        return 0
    fi

    # A registry record per row, plus whether the file it points at is still there.
    rows=$(
        printf '%s\n' "$records" |
            while IFS="$TAB_CHAR" read -r id name appimage_path desktop_file icon_path; do
                if [ -f "$appimage_path" ]; then
                    status="installed"
                else
                    status="missing"
                fi

                printf '%s\t%s\t%s\n' "$name" "$appimage_path" "$status"
            done
    )

    printf '%s\n' "$rows" | gum table --print --separator "$TAB_CHAR" --columns "Name,Path,Status"
}

# Rows for the remove picker.
#
# Two trailing fields, not one: the id for the removal, and the entry's own path for the
# preview. Carrying the path beats having the preview rebuild it, because the naming
# belongs to _appimage_write_desktop_file and a preview that spells it out again is a
# second place to get it wrong.
appimage_entries() {
    _appimage_records |
        awk -F "$TAB_CHAR" -v OFS="$TAB_CHAR" '{ print "[appimage]\tappimage\t" $2 "\t" $1 "\t" $4 }'
}

# Delete a file an install created. Only paths the registry still points at are removed,
# so a file the user has since moved elsewhere is left alone rather than deleted from its
# new location. Returns non-zero when there was a file to delete and it would not go.
_appimage_delete() {
    if [ -z "$1" ] || [ ! -f "$1" ]; then
        return 0
    fi

    rm --force -- "$1"
}

# Removes the selected rows, which carry the registry id in column 4.
appimage_remove() {
    gum style --foreground 10 "▸ Removing AppImages..."

    success=true

    # Ids are slugs, so splitting on whitespace cannot cut one in half.
    for id in $(printf '%s\n' "$1" | cut -f 4); do
        record=$(_appimage_records | awk -F "$TAB_CHAR" -v id="$id" '$1 == id')

        if [ -z "$record" ]; then
            continue
        fi

        name=$(printf '%s' "$record" | cut -f 2)

        _appimage_delete "$(printf '%s' "$record" | cut -f 3)" || success=false
        _appimage_delete "$(printf '%s' "$record" | cut -f 4)" || success=false
        _appimage_delete "$(printf '%s' "$record" | cut -f 5)" || success=false

        if [ -L "$APPIMAGE_BIN/$id" ]; then
            rm --force -- "$APPIMAGE_BIN/$id" || success=false
        fi

        _appimage_record_forget "$id"

        gum style --foreground 10 "✓ Removed $name"
    done

    _appimage_refresh_caches

    if $success; then
        gum style --foreground 10 "✓ AppImages removed!"
    else
        gum style --foreground 9 "x AppImage removal failed."
    fi

    $success
}
