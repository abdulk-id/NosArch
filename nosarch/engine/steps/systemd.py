import nosarch.engine.command
import nosarch.engine.module
import nosarch.engine.output
import nosarch.engine.setup

units = nosarch.engine.module.declares("systemd")
user_units = nosarch.engine.module.declares("systemd_user")


def _missing_unit(error: nosarch.engine.command.CommandFailedError) -> bool:
    text: str = f"{error.output or ''}\n{error.stderr or ''}"
    return "does not exist" in text or "not found" in text


def _enable(prefix: list[str], names: list[str]) -> set[str]:
    """Enable names. A unit that is not installed is skipped and returned, so one missing file does not undo the rest."""
    if not names:
        return set()

    try:
        nosarch.engine.command.run([*prefix, "enable", *names], capture=True)
    except nosarch.engine.command.CommandFailedError as error:
        if not _missing_unit(error):
            raise
        if len(names) == 1:
            nosarch.engine.output.print_warning(f"{names[0]} is not installed, so it was not enabled.")
            return set(names)

        missing: set[str] = set()
        for name in names:
            missing |= _enable(prefix, [name])
        return missing

    return set()


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
    missing: set[str] = _enable(["systemctl"], sorted(to_enable)) if to_enable and not dry else set()
    nosarch.engine.output.print_list("Disabling systemd units:", to_disable)
    if to_disable and not dry:
        nosarch.engine.command.run(["systemctl", "disable", *sorted(to_disable)], check=False)
    if not dry:
        ctx.state.systemd_units = sorted(declared - missing)

    for verb, planned in user_changes:
        label: str = "Enabling" if verb == "enable" else "Disabling"
        for user in users:
            nosarch.engine.output.print_list(f"{label} systemd units for {user}:", planned[user])
            if dry:
                continue
            skipped: set[str] = set()
            if planned[user]:
                prefix: list[str] = ["systemctl", "--user", "-M", f"{user}@"]
                if verb == "enable":
                    skipped = _enable(prefix, sorted(planned[user]))
                else:
                    nosarch.engine.command.run([*prefix, verb, *sorted(planned[user])], check=False)
            current: set[str] = set(enabled_user.get(user, []))
            updated: set[str] = (current | planned[user]) - skipped if verb == "enable" else current - planned[user]
            enabled_user[user] = sorted(updated)

    if dry:
        return

    # Rereads unit files. A running service keeps its old process until on_change restarts it.
    nosarch.engine.command.run(["systemctl", "daemon-reload"])
    for user in users:
        # The user manager is absent on a TTY and during a fresh install.
        nosarch.engine.command.run(["systemctl", "--user", "-M", f"{user}@", "daemon-reload"], check=False)
