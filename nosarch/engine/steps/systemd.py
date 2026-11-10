import engine.command
import engine.module
import engine.output
import engine.setup

units = engine.module.declares("systemd")
user_units = engine.module.declares("systemd_user")


def run(ctx: engine.setup.Context) -> None:
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
    users: list[str] = sorted(set(declared_user) | set(enabled_user))
    user_changes: tuple[tuple[str, dict[str, set[str]]], ...] = (
        ("enable", {user: declared_user.get(user, set()) - set(enabled_user.get(user, [])) for user in users}),
        ("disable", {user: set(enabled_user.get(user, [])) - declared_user.get(user, set()) for user in users}),
    )

    to_enable: set[str] = declared - enabled
    to_disable: set[str] = enabled - declared
    engine.output.print_list("Enabling systemd units:", to_enable)
    if to_enable and not dry:
        engine.command.run(["systemctl", "enable", *sorted(to_enable)])
    engine.output.print_list("Disabling systemd units:", to_disable)
    if to_disable and not dry:
        engine.command.run(["systemctl", "disable", *sorted(to_disable)], check=False)
    if not dry:
        ctx.state.systemd_units = sorted(declared)

    for verb, planned in user_changes:
        label: str = "Enabling" if verb == "enable" else "Disabling"
        for user in users:
            engine.output.print_list(f"{label} systemd units for {user}:", planned[user])
            if dry:
                continue
            if planned[user]:
                engine.command.run(
                    ["systemctl", "--user", "-M", f"{user}@", verb, *sorted(planned[user])], check=verb == "enable"
                )
            current: set[str] = set(enabled_user.get(user, []))
            updated: set[str] = (current | planned[user]) if verb == "enable" else (current - planned[user])
            enabled_user[user] = sorted(updated)

    if dry:
        return

    engine.command.run(["systemctl", "daemon-reload"])
    for user in users:
        engine.command.run(["systemctl", "--user", "-M", f"{user}@", "daemon-reload"], check=False)
