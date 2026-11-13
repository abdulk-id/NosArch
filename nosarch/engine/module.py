from collections.abc import Callable
from typing import Any, TypeVar

import nosarch.engine.changes
import nosarch.engine.fs

_F = TypeVar("_F", bound=Callable[..., Any])

USER_KINDS: tuple[str, ...] = ("systemd_user", "flatpak_user")
DETAIL_KINDS: tuple[str, ...] = ("snap", "snap_classic")

_ATTRIBUTE: str = "__nosarch_declares__"


def declares(kind: str) -> Callable[[_F], _F]:
    if kind not in nosarch.engine.changes.KINDS:
        raise ValueError(f"Unknown declaration kind '{kind}'.")

    def decorator(fn: _F) -> _F:
        setattr(fn, _ATTRIBUTE, kind)
        return fn

    return decorator


def _absorb(kind: str, into: Any, value: Any) -> None:
    if kind in USER_KINDS:
        for user, names in value.items():
            into.setdefault(user, set()).update(names)
        return
    into.update(value)


class Module:
    """What a module deploys, and the hooks that run around deploying it."""

    def __init__(self, name: str) -> None:
        self.name: str = name

    def before_update(self) -> None:
        """Runs for every enabled module before the steps other than users."""

    def on_enable(self) -> None:
        """Runs once, after the steps, the first time the module is enabled."""

    def on_change(self, changes: nosarch.engine.changes.Changes) -> None:
        """Runs once after the steps, when anything this module declares changed.

        The call is not once per file, so check `changes` for the path this hook cares about.
        """

    def after_update(self) -> None:
        """Runs for every enabled module after the other hooks."""

    def on_disable(self) -> None:
        """Runs when the module stops being enabled, before the steps remove what it installed."""

    def files(self) -> dict[str, nosarch.engine.fs.File]:
        return {}

    def directories(self) -> dict[str, nosarch.engine.fs.Directory]:
        return {}

    def symlinks(self) -> dict[str, str | nosarch.engine.fs.Symlink]:
        return {}

    def file_variables(self) -> dict[str, str]:
        return {}


def declarations(module: Module) -> dict[str, Any]:
    result: dict[str, Any] = {
        kind: {} if kind in USER_KINDS or kind in DETAIL_KINDS else set() for kind in nosarch.engine.changes.KINDS
    }
    for attribute_name in dir(type(module)):
        attribute: Any = getattr(type(module), attribute_name, None)
        kind: str | None = getattr(attribute, _ATTRIBUTE, None)
        if kind is not None:
            _absorb(kind, result[kind], getattr(module, attribute_name)())
    return result


def identities(kind: str, value: Any) -> set[str]:
    if kind in USER_KINDS:
        return {f"{user}:{name}" for user, names in value.items() for name in names}
    return set(value)


def collect(kind: str, by_module: dict[str, dict[str, Any]]) -> Any:
    result: Any = {} if kind in USER_KINDS or kind in DETAIL_KINDS else set()
    for module_declarations in by_module.values():
        _absorb(kind, result, module_declarations[kind])
    return result
