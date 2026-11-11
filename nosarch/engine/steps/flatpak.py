import shutil

import nosarch.engine.command
import nosarch.engine.module
import nosarch.engine.output
import nosarch.engine.setup

packages = nosarch.engine.module.declares("flatpak")
user_packages = nosarch.engine.module.declares("flatpak_user")


def _apply(ctx: nosarch.engine.setup.Context, user: str | None, wanted: set[str]) -> None:
    scope: str = "--user" if user else "--system"
    label: str = f" for {user}" if user else ""
    dry: bool = ctx.dry_run

    if user is not None and not nosarch.engine.command.can_run_as(user):
        nosarch.engine.output.print_warning(f"Flatpak apps of {user} can only be checked as root or as {user}.")
        return

    listed: str = nosarch.engine.command.run(
        ["flatpak", "list", "--app", scope, "--columns=application"], user=user, capture=True
    )
    installed: set[str] = {
        line.strip() for line in listed.splitlines() if line.strip() and line.strip() != "Application ID"
    }
    to_remove: set[str] = installed - wanted
    to_install: set[str] = wanted - installed

    nosarch.engine.output.print_list(
        f"Removing Flatpak apps{label}:" if not dry else f"Flatpak apps to remove{label}:", to_remove
    )
    if to_remove and not dry:
        nosarch.engine.command.run(["flatpak", "remove", scope, *sorted(to_remove)], user=user)
        nosarch.engine.command.run(["flatpak", "remove", "--unused", scope], user=user)

    if dry:
        nosarch.engine.output.print_info(f"Would update Flatpak apps{label}.")
    else:
        nosarch.engine.output.print_summary(f"Updating Flatpak apps{label}.")
        nosarch.engine.command.run(["flatpak", "update", scope], user=user)

    nosarch.engine.output.print_list(
        f"Installing Flatpak apps{label}:" if not dry else f"Flatpak apps to install{label}:", to_install
    )
    if to_install and not dry:
        nosarch.engine.command.run(["flatpak", "install", scope, *sorted(to_install)], user=user)


def run(ctx: nosarch.engine.setup.Context) -> None:
    nosarch.engine.output.print_summary("Checking Flatpak apps.")

    if shutil.which("flatpak") is None:
        nosarch.engine.output.print_warning("Flatpak is not installed yet, so its apps cannot be checked.")
        if not ctx.dry_run:
            raise RuntimeError("The flatpak command is missing.")
        return

    _apply(ctx, None, ctx.declared("flatpak"))

    for user, apps in sorted(ctx.declared("flatpak_user").items()):
        _apply(ctx, user, apps)
