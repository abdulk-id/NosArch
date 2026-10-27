"""Installs, updates, and removes Flatpak apps, system-wide and per user."""

import shutil

import engine.command
import engine.module
import engine.output
import engine.setup

# Marks a module method as returning `set[str]` of system-wide Flatpak app ids.
packages = engine.module.declares("flatpak")
# Marks a module method as returning `dict[str, set[str]]` of user name to that user's Flatpak app ids.
user_packages = engine.module.declares("flatpak_user")


def _installed(user: str | None) -> set[str]:
    scope: str = "--user" if user else "--system"
    output: str = engine.command.run(
        ["flatpak", "list", "--app", scope, "--columns=application"], user=user, capture=True
    )
    return {line.strip() for line in output.splitlines() if line.strip() and line.strip() != "Application ID"}


def _apply(ctx: engine.setup.Context, user: str | None, wanted: set[str]) -> None:
    scope: str = "--user" if user else "--system"
    label: str = f" for {user}" if user else ""
    dry: bool = ctx.dry_run

    if user is not None and not engine.command.can_run_as(user):
        engine.output.print_warning(f"Flatpak apps of {user} can only be checked as root or as {user}.")
        return

    installed: set[str] = _installed(user)
    to_remove: set[str] = installed - wanted
    to_install: set[str] = wanted - installed

    engine.output.print_list(
        f"Removing Flatpak apps{label}:" if not dry else f"Flatpak apps to remove{label}:", to_remove
    )
    if to_remove and not dry:
        engine.command.run(["flatpak", "remove", scope, *sorted(to_remove)], user=user)
        engine.command.run(["flatpak", "remove", "--unused", scope], user=user)

    if dry:
        engine.output.print_info(f"Would update Flatpak apps{label}.")
    else:
        engine.output.print_summary(f"Updating Flatpak apps{label}.")
        engine.command.run(["flatpak", "update", scope], user=user)

    engine.output.print_list(
        f"Installing Flatpak apps{label}:" if not dry else f"Flatpak apps to install{label}:", to_install
    )
    if to_install and not dry:
        engine.command.run(["flatpak", "install", scope, *sorted(to_install)], user=user)


def run(ctx: engine.setup.Context) -> None:
    engine.output.print_summary("Checking Flatpak apps.")

    if shutil.which("flatpak") is None:
        # The pacman step installs the runtime, so only a dry run of the run that enables Flatpak gets here.
        engine.output.print_warning("Flatpak is not installed yet, so its apps cannot be checked.")
        if not ctx.dry_run:
            raise RuntimeError("The flatpak command is missing.")
        return

    _apply(ctx, None, ctx.declared("flatpak"))

    for user, apps in sorted(ctx.declared("flatpak_user").items()):
        _apply(ctx, user, apps)
