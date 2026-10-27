"""The module base class, and how a module's declarations are gathered."""

from collections.abc import Callable
from typing import Any, TypeVar

import engine.changes
import engine.fs

_F = TypeVar("_F", bound=Callable[..., Any])

# Kinds whose declarations map a user to a set of names, and kinds that map a name to one detail (a snap's channel).
USER_KINDS: tuple[str, ...] = ("systemd_user", "flatpak_user")
DETAIL_KINDS: tuple[str, ...] = ("snap", "snap_classic")

_ATTRIBUTE: str = "__nosarch_declares__"


def declares(kind: str) -> Callable[[_F], _F]:
    """Marks a module method as returning declarations of `kind`. The step modules export these as decorators."""

    if kind not in engine.changes.KINDS:
        raise ValueError(f"Unknown declaration kind '{kind}'.")

    def decorator(fn: _F) -> _F:
        setattr(fn, _ATTRIBUTE, kind)
        return fn

    return decorator


class Module:
    """
    A unit of definition code: what it deploys, and hooks that run around deploying it.

    `name` is the key everything about the module is stored under. Renaming a module makes everything it declares
    look newly added.

    Hooks run in phases, and within a phase in registration order:

    1. `before_update`, for every enabled module.
    2. `on_disable`, for each module that was enabled on the last run and is not now.
    3. The steps: users, files, then the package and unit steps.
    4. `on_enable`, for modules enabled for the first time.
    5. `on_change`, for modules the steps changed something for.
    6. `after_update`, for every enabled module.

    No hook runs during a dry run.
    """

    def __init__(self, name: str) -> None:
        self.name: str = name

    def before_update(self) -> None:
        pass

    def on_enable(self) -> None:
        pass

    def on_change(self, changes: engine.changes.Changes) -> None:
        pass

    def after_update(self) -> None:
        pass

    def on_disable(self) -> None:
        """
        Runs on the first run after the module stops being registered as enabled, before any step.

        So whatever the module installed is still installed here, and is removed by the steps that follow.
        """

    def files(self) -> dict[str, engine.fs.File]:
        return {}

    def directories(self) -> dict[str, engine.fs.Directory]:
        return {}

    def symlinks(self) -> dict[str, str | engine.fs.Symlink]:
        return {}

    def file_variables(self) -> dict[str, str]:
        return {}


def declarations(module: Module) -> dict[str, Any]:
    """
    Every declaration of `module`, by kind.

    Set kinds come back as `set[str]`, user kinds as `dict[str, set[str]]`, detail kinds as `dict[str, str]`. A kind
    the module never declares comes back empty, so callers can index any kind.
    """

    result: dict[str, Any] = {}
    for kind in engine.changes.KINDS:
        result[kind] = {} if kind in USER_KINDS or kind in DETAIL_KINDS else set()

    for attribute_name in dir(type(module)):
        attribute: Any = getattr(type(module), attribute_name, None)
        kind: str | None = getattr(attribute, _ATTRIBUTE, None)
        if kind is None:
            continue

        value: Any = getattr(module, attribute_name)()

        if kind in USER_KINDS:
            for user, names in value.items():
                result[kind].setdefault(user, set()).update(names)
        elif kind in DETAIL_KINDS:
            result[kind].update(value)
        else:
            result[kind] |= set(value)

    return result


def identities(kind: str, value: Any) -> set[str]:
    """Flattens one kind's declarations to the names that identify them, as recorded in `Changes`."""

    if kind in USER_KINDS:
        return {f"{user}:{name}" for user, names in value.items() for name in names}
    return set(value)
