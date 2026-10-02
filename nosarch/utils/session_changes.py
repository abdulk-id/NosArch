from decman import Store

# Where the hooks leave what could not be applied live. `tools/apply` reads it after decman has
# exited, which is the only point where every hook has finished and the store is on disk.
_PENDING_KEY: str = "nosarch_pending_session_changes"


def reset(store: Store) -> None:
    """Forget anything a previous run left pending.

    Call from `before_update`. That hook runs before the files step and before every `on_change`,
    so which module does this does not matter, unlike a prompt placed after the last hook.
    """

    store[_PENDING_KEY] = {}


def defer(store: Store, category: str, description: str) -> None:
    """Record a change that needs a new login to take effect.

    Call from `on_change`, with `category` as `logout` or `reboot`. The hook still prints its own
    notice, so a plain `decman` run informs the user even though it cannot offer the action.
    """

    pending: dict[str, list[str]] = store.get(_PENDING_KEY, {})
    pending.setdefault(category, []).append(description)
    store[_PENDING_KEY] = pending
