import os

import nosarch.engine.output

_SESSION_COMMAND: str = "/usr/local/bin/nosarch/nosarch-session"

_logouts: list[str] = []
_reboots: list[str] = []


def request_logout(description: str) -> None:
    if description not in _logouts:
        _logouts.append(description)


def request_reboot(description: str) -> None:
    if description not in _reboots:
        _reboots.append(description)


def offer(prompt: bool) -> None:
    if not _logouts and not _reboots:
        return

    nosarch.engine.output.print_list("These changes will take effect after logging out:", _logouts, one_per_line=True)
    nosarch.engine.output.print_list("These changes will take effect after a reboot:", _reboots, one_per_line=True)

    if not prompt:
        return

    action: str = "restart" if _reboots else "logout"
    question: str = "Restart now?" if _reboots else "Log out now?"

    if not nosarch.engine.output.prompt_confirm(question, default=False):
        return

    os.execv(_SESSION_COMMAND, [_SESSION_COMMAND, action])
