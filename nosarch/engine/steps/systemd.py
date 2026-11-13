import nosarch.engine.command
import nosarch.engine.module
import nosarch.engine.output
import nosarch.engine.setup

units = nosarch.engine.module.declares("systemd")
user_units = nosarch.engine.module.declares("systemd_user")


def run(ctx: nosarch.engine.setup.Context) -> None:
    nosarch.engine.output.print_summary("Checking systemd units.")

    try:
        _apply(ctx)
    except nosarch.engine.command.CommandFailedError:
        nosarch.engine.output.print_error("Running a systemd command failed.")
        raise


def _apply(ctx: nosarch.engine.setup.Context) -> None:
    dry: bool = ctx.dry_run
    # Disable only units this engine enabled. A unit enabled by hand, or by a package preset, is not in this state.
    declared: set[str] = ctx.declared("systemd")
    enabled: set[str] = set(ctx.state.systemd_units)
    declared_user: dict[str, set[str]] = ctx.declared("systemd_user")
    enabled_user: dict[str, list[str]] = ctx.state.systemd_user_units
    users: list[str] = sorted(set(declared_user) | set(enabled_user))
    user_changes: tuple[tuple[str, dict[str, set[str]]], ...] = (
        ("enable", {user: declared_user.get(user, set()) - set(enabled_user.get(user, [])) for user in users}),
        ("disable", {user: set(enabled_user.get(user, [])) - declared_user.get(user, set()) for user in users}),
    )

    to_enable: set[str] = declared - enabled
    to_disable: set[str] = enabled - declared
    nosarch.engine.output.print_list("Enabling systemd units:", to_enable)
    if to_enable and not dry:
        nosarch.engine.command.run(["systemctl", "enable", *sorted(to_enable)])
    nosarch.engine.output.print_list("Disabling systemd units:", to_disable)
    if to_disable and not dry:
        nosarch.engine.command.run(["systemctl", "disable", *sorted(to_disable)], check=False)
    if not dry:
        ctx.state.systemd_units = sorted(declared)

    for verb, planned in user_changes:
        label: str = "Enabling" if verb == "enable" else "Disabling"
        for user in users:
            nosarch.engine.output.print_list(f"{label} systemd units for {user}:", planned[user])
            if dry:
                continue
            if planned[user]:
                nosarch.engine.command.run(
                    ["systemctl", "--user", "-M", f"{user}@", verb, *sorted(planned[user])], check=verb == "enable"
                )
            current: set[str] = set(enabled_user.get(user, []))
            updated: set[str] = (current | planned[user]) if verb == "enable" else (current - planned[user])
            enabled_user[user] = sorted(updated)

    if dry:
        return

    # Rereads unit files. A running service keeps its old process until on_change restarts it.
    nosarch.engine.command.run(["systemctl", "daemon-reload"])
    for user in users:
        # The user manager is absent on a TTY and during a fresh install.
        nosarch.engine.command.run(["systemctl", "--user", "-M", f"{user}@", "daemon-reload"], check=False)
