"""Enables the declared systemd units, and disables the ones the engine enabled that nothing declares any more."""

import engine.command
import engine.module
import engine.output
import engine.setup

# Marks a module method as returning `set[str]` of system unit names.
units = engine.module.declares("systemd")
# Marks a module method as returning `dict[str, set[str]]` of user name to user unit names.
user_units = engine.module.declares("systemd_user")


def run(ctx: engine.setup.Context) -> None:
    """
    Units are compared against what the engine enabled before, not against what systemd reports. A unit the user
    enabled by hand, or a package enabled through a preset, is never disabled.

    Enabling a unit does not start it, so a newly declared unit starts at the next boot or login.
    """

    engine.output.print_summary("Checking systemd units.")
    dry: bool = ctx.dry_run

    declared: set[str] = ctx.declared("systemd")
    enabled: set[str] = set(ctx.state.systemd_units)

    to_enable: set[str] = declared - enabled
    to_disable: set[str] = enabled - declared

    engine.output.print_list("Enabling systemd units:" if not dry else "Systemd units to enable:", to_enable)
    engine.output.print_list("Disabling systemd units:" if not dry else "Systemd units to disable:", to_disable)

    if not dry:
        if to_enable:
            engine.command.run(["systemctl", "enable", *sorted(to_enable)])
        if to_disable:
            # A unit whose package is gone cannot be disabled, and there is nothing left to disable.
            engine.command.run(["systemctl", "disable", *sorted(to_disable)], check=False)
        ctx.state.systemd_units = sorted(declared)
        # Unit files the files step just wrote are only seen after a reload.
        engine.command.run(["systemctl", "daemon-reload"])

    declared_user: dict[str, set[str]] = ctx.declared("systemd_user")
    enabled_user: dict[str, list[str]] = ctx.state.systemd_user_units

    for user in sorted(set(declared_user) | set(enabled_user)):
        wanted: set[str] = declared_user.get(user, set())
        current: set[str] = set(enabled_user.get(user, []))
        user_enable: set[str] = wanted - current
        user_disable: set[str] = current - wanted

        engine.output.print_list(
            f"Enabling systemd units for {user}:" if not dry else f"Units to enable for {user}:", user_enable
        )
        engine.output.print_list(
            f"Disabling systemd units for {user}:" if not dry else f"Units to disable for {user}:", user_disable
        )

        if dry or not (user_enable or user_disable):
            continue

        # `-M user@` reaches the user's manager through the system manager, so it works without the user's session.
        manager: list[str] = ["systemctl", "--user", "-M", f"{user}@"]
        if user_enable:
            engine.command.run([*manager, "enable", *sorted(user_enable)])
        if user_disable:
            engine.command.run([*manager, "disable", *sorted(user_disable)], check=False)
        # The user manager is not running when applying from a TTY or during a fresh install.
        engine.command.run([*manager, "daemon-reload"], check=False)

        if wanted:
            enabled_user[user] = sorted(wanted)
        else:
            enabled_user.pop(user, None)
