#!/bin/sh

battery_percentage="$1"

notify-send --urgency=critical --transient \
    --icon=battery-level-10-symbolic \
    "Low Battery (${battery_percentage}%)" \
    "Plug in soon to recharge"
