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

    try:
        _apply(ctx)
    except engine.command.CommandFailedError:
        engine.output.print_error("Running a systemd command failed.")
        raise


def _apply(ctx: engine.setup.Context) -> None:
    dry: bool = ctx.dry_run

    declared: set[str] = ctx.declared("systemd")
    enabled: set[str] = set(ctx.state.systemd_units)

    declared_user: dict[str, set[str]] = ctx.declared("systemd_user")
    enabled_user: dict[str, list[str]] = ctx.state.systemd_user_units
    # A user stays in the state once it has had units, even with none left. Its manager is reloaded on every run, since
    # the files step may have rewritten a unit file that is already enabled.
    users: list[str] = sorted(set(declared_user) | set(enabled_user))
    user_enable: dict[str, set[str]] = {
        user: declared_user.get(user, set()) - set(enabled_user.get(user, [])) for user in users
    }
    user_disable: dict[str, set[str]] = {
        user: set(enabled_user.get(user, [])) - declared_user.get(user, set()) for user in users
    }

    to_enable: set[str] = declared - enabled
    to_disable: set[str] = enabled - declared

    # The order is system enable, system disable, user enable, user disable, then the reloads.
    engine.output.print_list("Enabling systemd units:", to_enable)
    if to_enable and not dry:
        engine.command.run(["systemctl", "enable", *sorted(to_enable)])

    engine.output.print_list("Disabling systemd units:", to_disable)
    if to_disable and not dry:
        # A unit whose package is gone cannot be disabled, and there is nothing left to disable.
        engine.command.run(["systemctl", "disable", *sorted(to_disable)], check=False)

    if not dry:
        ctx.state.systemd_units = sorted(declared)

    # `-M user@` reaches the user's manager through the system manager, so it works without the user's session.
    for user in users:
        engine.output.print_list(f"Enabling systemd units for {user}:", user_enable[user])
        if not dry:
            if user_enable[user]:
                engine.command.run(["systemctl", "--user", "-M", f"{user}@", "enable", *sorted(user_enable[user])])
            enabled_user[user] = sorted(set(enabled_user.get(user, [])) | user_enable[user])

    for user in users:
        engine.output.print_list(f"Disabling systemd units for {user}:", user_disable[user])
        if not dry:
            if user_disable[user]:
                engine.command.run(
                    ["systemctl", "--user", "-M", f"{user}@", "disable", *sorted(user_disable[user])], check=False
                )
            enabled_user[user] = sorted(set(enabled_user.get(user, [])) - user_disable[user])

    if dry:
        return

    # Unit files the files step just wrote are only seen after a reload.
    engine.command.run(["systemctl", "daemon-reload"])
    for user in users:
        # The user manager is not running when applying from a TTY or during a fresh install.
        engine.command.run(["systemctl", "--user", "-M", f"{user}@", "daemon-reload"], check=False)
