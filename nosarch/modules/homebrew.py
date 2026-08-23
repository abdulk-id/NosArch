import os
from typing import override

import decman
import user_config.config_reader as userConfig
from decman import File
from decman.plugins import pacman

userConfig.load()
_username: str = userConfig.get_str("user.username")


# Standard Homebrew-on-Linux prefix. Everything the git-clone install creates
# lives here, so teardown is a single directory removal.
_BREW_PREFIX: str = "/home/linuxbrew/.linuxbrew"
_BREW_BIN: str = f"{_BREW_PREFIX}/bin/brew"


class HomebrewModule(decman.Module):
    """
    Bootstraps Homebrew itself so the `homebrew` plugin has a `brew` to drive.
    """

    def __init__(self) -> None:
        super().__init__(name="homebrew")

    @override
    def files(self) -> dict[str, File]:
        homebrew_bashrc_contents: str = (
            "#\n"
            + "# .bashrc for homebrew\n"
            + "#\n"
            + "\n"
            + "# Use Homebrew in your user\n"
            + '[ -x /home/linuxbrew/.linuxbrew/bin/brew ] && eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"'
        )

        return {
            f"/home/{_username}/.bashrc.d/homebrew.bashrc": File(content=homebrew_bashrc_contents, owner=f"{_username}")
        }

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
    def brew_prereqs(self) -> set[str]:
        # Homebrew's build prerequisites
        return {"curl", "file", "gcc", "git", "procps-ng"}

    @override
    def before_update(self, store: decman.Store) -> None:
        if os.path.exists(_BREW_BIN):
            return

        # Root phase: create the prefix and hand it to the user.
        # (brew refuses to run as root, and owning the prefix up front means the clone needs no privileges.)
        _ = decman.sh(f"mkdir -p {_BREW_PREFIX} && chown -R {_username}:{_username} /home/linuxbrew")

        # User phase: clone brew, link the launcher, prime the formula data.
        _ = decman.sh(
            "set -eu\n"
            + f'prefix="{_BREW_PREFIX}"\n'
            + 'if [ ! -d "$prefix/Homebrew" ]; then\n'
            + '    git clone https://github.com/Homebrew/brew "$prefix/Homebrew"\n'
            + "fi\n"
            + 'mkdir -p "$prefix/bin"\n'
            + 'ln -sf ../Homebrew/bin/brew "$prefix/bin/brew"\n'
            + '"$prefix/bin/brew" update --force --quiet\n',
            user=_username,
            mimic_login=True,
        )

    @override
    @staticmethod
    def on_disable() -> None:
        import shutil

        shutil.rmtree("/home/linuxbrew", ignore_errors=True)
