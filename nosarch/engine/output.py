"""Terminal output for the engine and for the definition code."""

import os
import shutil
import sys
import textwrap

# Debug lines are only printed when this is set, by `--debug` or NosArch Works.
debug_output: bool = False


def _color_enabled() -> bool:
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def _paint(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _color_enabled() else text


def _tag() -> str:
    return _paint("1;34", "[NosArch]")


def print_summary(message: str) -> None:
    print(f"{_tag()} {_paint('1', message)}", flush=True)


def print_info(message: str) -> None:
    print(f"{_tag()} {message}", flush=True)


def print_debug(message: str) -> None:
    if debug_output:
        print(f"{_tag()} {_paint('90', message)}", flush=True)


def print_warning(message: str) -> None:
    print(f"{_tag()} {_paint('93', 'WARNING')} {message}", file=sys.stderr, flush=True)


def print_error(message: str) -> None:
    print(f"{_tag()} {_paint('91', 'ERROR')} {message}", file=sys.stderr, flush=True)


def print_list(message: str, items: list[str] | set[str], one_per_line: bool = False) -> None:
    """Prints a message followed by its items, or nothing at all when there are no items."""

    if not items:
        return

    print_summary(message)

    ordered: list[str] = sorted(items) if isinstance(items, set) else list(items)
    if one_per_line:
        for item in ordered:
            print(f"    {item}", flush=True)
        return

    width: int = max(shutil.get_terminal_size().columns - 4, 40)
    for line in textwrap.wrap("  ".join(ordered), width=width, break_on_hyphens=False):
        print(f"    {line}", flush=True)


def prompt_confirm(message: str, default: bool) -> bool:
    """Asks a yes/no question. Without a terminal to ask on, the default is the answer."""

    if not sys.stdin.isatty():
        return default

    suffix: str = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            answer: str = input(f"{_tag()} {_paint('92', 'PROMPT')} {message} {suffix} ").strip().lower()
        except EOFError:
            return default

        if answer == "":
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print_error("Answer y or n.")


def prompt_choice(message: str, choices: list[str]) -> str:
    """Asks the user to pick one of `choices`. The first one is the default."""

    print_summary(message)
    for index, choice in enumerate(choices, start=1):
        print(f"    {index}: {choice}", flush=True)

    if not sys.stdin.isatty():
        return choices[0]

    while True:
        try:
            answer: str = input(f"{_tag()} {_paint('92', 'PROMPT')} [1-{len(choices)}] (default 1): ").strip()
        except EOFError:
            return choices[0]

        if answer == "":
            return choices[0]
        if answer.isdigit() and 1 <= int(answer) <= len(choices):
            return choices[int(answer) - 1]
        print_error("Pick one of the numbers above.")
