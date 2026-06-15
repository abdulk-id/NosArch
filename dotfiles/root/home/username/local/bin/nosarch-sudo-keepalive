#!/bin/bash

start_sudo_keepalive() {
    sudo -v || return 1

    while true; do
        sudo -n -v
        sleep 60
    done 2>/dev/null &

    export SUDO_KEEPALIVE_PID=$!
}

stop_sudo_keepalive() {
    [[ -n "${SUDO_KEEPALIVE_PID:-}" ]] && \
        kill "$SUDO_KEEPALIVE_PID" 2>/dev/null
}
