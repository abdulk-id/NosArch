import functools

import decman

# The graphical session's environment lives in its systemd user manager, because Hyprland's
# autostart config runs `systemctl --user import-environment`. Reading it back is exact.
# Reconstructing `WAYLAND_DISPLAY` or the Hyprland instance signature would be guessing, so
# `run_in_session` skips the action instead of acting on a guessed environment.
_SESSION_ENV_KEYS: tuple[str, ...] = (
    "DBUS_SESSION_BUS_ADDRESS",
    "DISPLAY",
    "HYPRLAND_INSTANCE_SIGNATURE",
    "PATH",
    "WAYLAND_DISPLAY",
    "XAUTHORITY",
    "XDG_RUNTIME_DIR",
    "XDG_SESSION_TYPE",
)


@functools.cache
def _graphical_session() -> tuple[int, str] | None:
    """UID and username of the active graphical session, or None when there is none."""

    # `pty=False`: these outputs are parsed, and on a terminal systemd colorizes them, which puts
    # escape codes in the middle of the fields.
    sessions: str = decman.prg(["loginctl", "list-sessions", "--no-legend"], check=False, pty=False)

    for line in sessions.splitlines():
        # SESSION UID USER SEAT SEAT_ID TTY REMOTE CLASS, and remote sessions add more columns.
        fields: list[str] = line.split()
        if len(fields) < 3:
            continue

        properties: str = decman.prg(
            ["loginctl", "show-session", fields[0], "--property=State", "--property=Type"],
            check=False,
            pty=False,
        )

        state, session_type = "", ""
        for property_line in properties.splitlines():
            key, separator, value = property_line.partition("=")
            if not separator:
                continue
            if key == "State":
                state = value.strip()
            elif key == "Type":
                session_type = value.strip()

        if state == "active" and session_type in ("wayland", "x11"):
            return int(fields[1]), fields[2]

    return None


def has_graphical_session() -> bool:
    return _graphical_session() is not None


def run_in_session(cmd: list[str]) -> bool:
    """Run a command as the owner of the active graphical session.

    Returns False when there is no graphical session to run in, or when its environment could not
    be read. Never raises: applying a change to a live session is best-effort and must not fail a
    decman run.
    """

    session: tuple[int, str] | None = _graphical_session()
    if session is None:
        return False

    uid, username = session

    # `-M` goes through the system manager, so root reaches the user's manager without the
    # session's bus.
    show_environment: str = decman.prg(
        ["systemctl", "--user", "-M", f"{username}@", "show-environment"], check=False, pty=False
    )

    environment: dict[str, str] = {"XDG_RUNTIME_DIR": f"/run/user/{uid}"}
    for line in show_environment.splitlines():
        key, separator, value = line.partition("=")
        if separator and key in _SESSION_ENV_KEYS:
            environment[key] = value.strip()

    if "WAYLAND_DISPLAY" not in environment:
        return False

    _ = decman.prg(
        cmd,
        user=username,
        env_overrides=environment,
        pass_environment=False,
        mimic_login=True,
        check=False,
        pty=False,
    )
    return True