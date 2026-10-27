"""
Installs, upgrades, and removes Homebrew formulae, casks, and taps.

brew refuses to run as root, so every command runs as `Setup.homebrew_user`, the account that owns the prefix.
"""

import os
import re

import engine.command
import engine.module
import engine.output
import engine.setup

BREW: str = "/home/linuxbrew/.linuxbrew/bin/brew"

# Taps Homebrew manages itself. Never untapped.
_PROTECTED_TAPS: set[str] = {"homebrew/core", "homebrew/cask"}

# brew's environment and analytics hints would end up in the output being parsed.
_ENV: dict[str, str] = {"HOMEBREW_NO_ENV_HINTS": "1"}

_NAME: re.Pattern[str] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+_.@/-]*$")

# Mark a module method as returning `set[str]` of formulae, casks, or taps.
formulae = engine.module.declares("brew_formula")
casks = engine.module.declares("brew_cask")
taps = engine.module.declares("brew_tap")


def _brew(user: str, *args: str, capture: bool = False) -> str:
    return engine.command.run([BREW, *args], user=user, env=_ENV, capture=capture)


def _names(user: str, *args: str) -> set[str]:
    # A line that is not a name is a hint or a warning, not something installed.
    return {line.strip() for line in _brew(user, *args, capture=True).splitlines() if _NAME.match(line.strip())}


def run(ctx: engine.setup.Context) -> None:
    engine.output.print_summary("Checking Homebrew packages.")

    user: str | None = ctx.setup.homebrew_user
    if user is None:
        raise RuntimeError("Homebrew needs `Setup.homebrew_user`, since brew cannot run as root.")

    if not os.path.isfile(BREW):
        # HomebrewModule bootstraps brew in `before_update`, which a dry run skips.
        engine.output.print_warning("Homebrew is not installed yet, so its packages cannot be checked.")
        if not ctx.dry_run:
            raise RuntimeError(f"{BREW} is missing.")
        return

    if not engine.command.can_run_as(user):
        engine.output.print_warning(f"Homebrew packages can only be checked as root or as {user}.")
        return

    dry: bool = ctx.dry_run

    # Taps first: a formula or cask can live in one.
    wanted_taps: set[str] = ctx.declared("brew_tap")
    current_taps: set[str] = _names(user, "tap")
    to_tap: set[str] = wanted_taps - current_taps
    to_untap: set[str] = current_taps - wanted_taps - _PROTECTED_TAPS
    engine.output.print_list("Homebrew taps to add:", to_tap)
    engine.output.print_list("Homebrew taps to remove:", to_untap)
    if not dry:
        for tap in sorted(to_tap):
            _brew(user, "tap", tap)
        for tap in sorted(to_untap):
            _brew(user, "untap", tap)

    # Only formulae installed on request are candidates for removal. Dependencies go with `brew autoremove`.
    wanted_formulae: set[str] = ctx.declared("brew_formula")
    installed_formulae: set[str] = _names(user, "list", "--formula", "-1")
    on_request: set[str] = _names(user, "leaves", "--installed-on-request")
    to_remove: set[str] = on_request - wanted_formulae
    to_install: set[str] = wanted_formulae - installed_formulae
    engine.output.print_list("Homebrew formulae to remove:", to_remove)
    if to_remove and not dry:
        _brew(user, "uninstall", "--formula", *sorted(to_remove))
        _brew(user, "autoremove")

    if dry:
        engine.output.print_info("Would upgrade Homebrew packages.")
    else:
        engine.output.print_summary("Upgrading Homebrew packages.")
        _brew(user, "upgrade", "--greedy", "--yes")

    engine.output.print_list("Homebrew formulae to install:", to_install)
    if to_install and not dry:
        _brew(user, "install", "--formula", *sorted(to_install))

    wanted_casks: set[str] = ctx.declared("brew_cask")
    installed_casks: set[str] = _names(user, "list", "--cask", "-1")
    cask_remove: set[str] = installed_casks - wanted_casks
    cask_install: set[str] = wanted_casks - installed_casks
    engine.output.print_list("Homebrew casks to remove:", cask_remove)
    engine.output.print_list("Homebrew casks to install:", cask_install)
    if not dry:
        if cask_remove:
            _brew(user, "uninstall", "--cask", *sorted(cask_remove))
        if cask_install:
            _brew(user, "install", "--cask", *sorted(cask_install))
