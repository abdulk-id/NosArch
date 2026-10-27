"""Changes that only take effect on a new login, and the offer to start one."""

import os

import engine.output

_SESSION_COMMAND: str = "/usr/local/bin/nosarch/nosarch-session"

_logouts: list[str] = []
_reboots: list[str] = []


def request_logout(description: str) -> None:
    """Records a change that takes effect after logging out. Repeated descriptions are listed once."""
    if description not in _logouts:
        _logouts.append(description)


def request_reboot(description: str) -> None:
    """Records a change that takes effect after a reboot. Repeated descriptions are listed once."""
    if description not in _reboots:
        _reboots.append(description)


def offer(prompt: bool) -> None:
    """
    Lists what is waiting on a new login, then offers to log out or reboot.

    Called once everything else has finished and the state is saved: logging out or rebooting ends the process, and
    anything after this point would not run.
    """

    if not _logouts and not _reboots:
        return

    engine.output.print_list("These changes will take effect after logging out:", _logouts, one_per_line=True)
    engine.output.print_list("These changes will take effect after a reboot:", _reboots, one_per_line=True)

    if not prompt:
        return

    # A reboot gives a fresh login too, so it covers the logout cases.
    action: str = "restart" if _reboots else "logout"
    question: str = "Restart now?" if _reboots else "Log out now?"

    if not engine.output.prompt_confirm(question, default=False):
        return

    os.execv(_SESSION_COMMAND, [_SESSION_COMMAND, action])
