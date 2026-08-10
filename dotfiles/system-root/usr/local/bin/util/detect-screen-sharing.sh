#!/bin/sh

is_screen_shared() {
    pw-dump | jq -e '
        .[]
        | .info?.props?
        | select(
            .["media.class"] == "Video/Source"
            and .["stream.is-live"] == true
            and (
                (.["media.name"] // "") | startswith("xdp")
            )
        )
    ' >/dev/null
}

main() {
    if is_screen_shared; then
        echo "true"
    else
        echo "false"
    fi
}

main
