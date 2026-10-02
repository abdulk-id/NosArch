#!/bin/sh
# Managed by NosArch

start_sudo_keepalive() {
    sudo -v || return 1

    while true; do
        sudo -n -v
        sleep 60
    done 2>/dev/null &

    export SUDO_KEEPALIVE_PID=$!
}

stop_sudo_keepalive() {
    # Always succeed: callers run under `set -e`, and the keepalive may never have been started
    if [ -n "${SUDO_KEEPALIVE_PID:-}" ]; then
        kill "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
    fi

    return 0
}
