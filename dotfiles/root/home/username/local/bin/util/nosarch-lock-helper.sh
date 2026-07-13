#!/bin/sh

# Use this script for locking and running post-unlock steps
# Vicinae does not work with commands that keep running in the foreground (hyprlock)
# Using this helper script with `setsid` to avoid blocking

. nosarch-session

hyprlock
session_after_unlock
