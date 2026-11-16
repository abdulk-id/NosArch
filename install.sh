#!/bin/sh
# Installs the NosArch pacman package from a GitHub release, and writes the smallest ~/.nosarch_config.json NosArch
# accepts if there is none. It does not apply NosArch: run `nosarch-apply` after.
#
# This is the only installer. It lives on master and installs the latest stable release, the newest dev build with
# --dev, or one tag:
#
#   curl -fsSL https://raw.githubusercontent.com/abdulk-id/NosArch/master/install.sh | sh
#   curl -fsSL https://raw.githubusercontent.com/abdulk-id/NosArch/master/install.sh | sh -s -- --dev
#   curl -fsSL https://raw.githubusercontent.com/abdulk-id/NosArch/master/install.sh | sh -s -- v0.1.0
set -eu

# Utilities

repo="abdulk-id/NosArch"
package="nosarch-source.pkg.tar.zst"

fail() {
    printf 'nosarch install: %s\n' "$1" >&2
    exit 1
}

show_help() {
    cat <<EOF
Usage: install.sh [--dev | TAG]

Installs the NosArch pacman package, and writes ~/.nosarch_config.json with your
username if you have no config yet. An existing config is kept.
It does not apply NosArch.

With no argument, installs the latest stable release.

  --dev   the newest dev build, a GitHub prerelease. dev means the same
  TAG     one exact release, such as v0.1.0
EOF
}

need() {
    command -v "$1" > /dev/null 2>&1 || fail "$2"
}

# Features

# The newest release that is a prerelease. Only dev builds are prereleases. GitHub lists releases newest first, and
# indents a release's own fields four spaces, so a field of its author or assets does not match.
newest_dev_tag() {
    releases="$(curl --fail --silent --show-error --location --header 'Accept: application/vnd.github+json' \
        "https://api.github.com/repos/${repo}/releases?per_page=30")" ||
        fail "could not list releases. GitHub allows 60 anonymous requests an hour per address."
    printf '%s\n' "$releases" |
        awk '/^    "tag_name":/ { tag = $2; gsub(/[",]/, "", tag) } /^    "prerelease": true/ { print tag; exit }'
}

# GitHub sends /releases/latest to /releases/tag/<tag> for the newest release that is not a prerelease, and to the
# release list when there is none. Resolving that tag, then downloading from it, keeps the package and SHA256SUMS
# on the same release when another one is published during the download. This is a page request, not an API call.
latest_stable_tag() {
    url="$(curl --fail --silent --show-error --location --output /dev/null \
        --write-out '%{url_effective}' "https://github.com/${repo}/releases/latest")" ||
        fail "could not find the latest release."
    url="${url%%\?*}"
    url="${url%/}"
    prefix="https://github.com/${repo}/releases/tag/"
    case "$url" in
        "$prefix"*)
            tag="${url#"$prefix"}"
            ;;
        *)
            tag=""
            ;;
    esac
    [ -n "$tag" ] || fail "there is no stable release yet. Pass --dev for the newest dev build."
    printf '%s' "$tag"
}

# Prints the tag to install.
choose_tag() {
    mode=$1
    tag=$2
    if [ "$mode" = "dev" ]; then
        tag="$(newest_dev_tag)"
        [ -n "$tag" ] || fail "there is no dev build yet."
    elif [ "$mode" = "latest" ]; then
        tag="$(latest_stable_tag)"
    fi
    printf '%s' "$tag"
}

download() {
    tag=$1
    work_dir=$2
    base_url="https://github.com/${repo}/releases/download/${tag}"

    printf 'Downloading %s\n' "$tag" >&2
    curl --fail --silent --show-error --location --output "${work_dir}/${package}" "${base_url}/${package}" ||
        fail "could not download ${base_url}/${package}"
    curl --fail --silent --show-error --location --output "${work_dir}/SHA256SUMS" "${base_url}/SHA256SUMS" ||
        fail "could not download ${base_url}/SHA256SUMS"

    (cd -- "$work_dir" && sha256sum --check --quiet SHA256SUMS) || fail "the downloaded package does not match SHA256SUMS."
    chmod 644 "${work_dir}/${package}"
}

# --noconfirm: stdin is the script when this runs as `curl | sh`, so pacman could not ask.
# No --needed: installing the same version again is how a throwaway machine is reset.
install_package() {
    if [ "$(id -u)" -eq 0 ]; then
        pacman --upgrade --noconfirm "$1"
    else
        sudo pacman --upgrade --noconfirm "$1"
    fi
}

# The account that is installing NosArch: the user, or the user that ran this script with sudo. Nothing is written for
# a plain root login, since root is not the account NosArch is set up for.
config_user() {
    if [ "$(id -u)" -ne 0 ]; then
        id -un
    else
        printf '%s' "${SUDO_USER:-}"
    fi
}

# The smallest config NosArch accepts: the username. Everything else has a default. A username is letters, digits, `_`
# and `-`, so it needs no JSON escaping.
write_config() {
    user="$(config_user)"
    if [ -z "$user" ] || [ "$user" = "root" ]; then
        printf '\nNo config written: log in as the user NosArch is for, or run this with sudo from that user.\n' >&2
        return 0
    fi

    if [ "$(id -u)" -ne 0 ]; then
        home="$HOME"
    else
        home="$(getent passwd "$user" | cut --delimiter=: --fields=6)"
    fi
    config="${home}/.nosarch_config.json"
    if [ -e "$config" ]; then
        printf '\nKept your existing %s\n' "$config"
        return 0
    fi

    printf '{\n    "user": {\n        "username": "%s"\n    }\n}\n' "$user" > "$config"
    if [ "$(id -u)" -eq 0 ]; then
        chown "$user" "$config"
    fi
    printf '\nWrote %s with your username. Add settings to it to choose what NosArch sets up.\n' "$config"
}

# Sets mode to latest, dev, or tag, and tag when mode is tag. dev means the same as --dev.
parse_request() {
    mode="latest"
    tag=""
    for argument in "$@"; do
        case "$argument" in
            --dev | dev)
                if [ "$mode" != "latest" ]; then
                    fail "pass either --dev or one tag."
                fi
                mode="dev"
                ;;
            -*)
                show_help >&2
                exit 1
                ;;
            *)
                if [ "$mode" != "latest" ] || [ -n "$tag" ]; then
                    fail "pass either --dev or one tag."
                fi
                mode="tag"
                tag=$argument
                ;;
        esac
    done
}

main() {
    case "${1:-}" in
        help | -h | --help)
            if [ "$#" -ne 1 ]; then
                show_help >&2
                exit 1
            fi
            show_help
            exit 0
            ;;
    esac

    parse_request "$@"

    need pacman "NosArch installs on Arch Linux. pacman was not found."
    need curl "curl is required. Install it with: sudo pacman -S curl"
    [ "$(id -u)" -eq 0 ] || need sudo "sudo is required to run pacman."

    tag="$(choose_tag "$mode" "$tag")"

    work_dir="$(mktemp --directory)"
    trap 'rm --recursive --force -- "$work_dir"' EXIT
    # pacman reads the package as an unprivileged user while it resolves dependencies.
    chmod 755 "$work_dir"

    download "$tag" "$work_dir"
    install_package "${work_dir}/${package}"
    write_config

    printf '\nInstalled. Run: nosarch-apply --dry-run to see what it would change, then nosarch-apply\n'
}

main "$@"
