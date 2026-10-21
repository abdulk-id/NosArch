import os
from typing import override

import decman
import utils.paths
from decman import File
from decman.plugins import pacman

# Standard Homebrew-on-Linux prefix. Everything the git-clone install creates
# lives here, so teardown is a single directory removal.
_BREW_PREFIX: str = "/home/linuxbrew/.linuxbrew"
_BREW_BIN: str = f"{_BREW_PREFIX}/bin/brew"


class HomebrewModule(decman.Module):
    """
    Bootstraps Homebrew itself so the `homebrew` plugin has a `brew` to drive.
    """

    def __init__(self, username) -> None:
        super().__init__(name="homebrew")
        self._username: str = username

    @override
    def files(self) -> dict[str, File]:
        # nosarch-package sources this when it exists and skips Homebrew when it does not, which is how the CLI
        # follows this module being enabled or disabled.
        files: dict[str, File] = utils.paths.Dotfiles("../dotfiles/system-root").files(
            "/usr/local/bin/util/package/homebrew.sh"
        )

        homebrew_bashrc_contents: str = (
            "#\n"
            + "# .bashrc for homebrew\n"
            + "#\n"
            + "\n"
            + "# Use Homebrew in your user\n"
            + 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"'
        )

        return files | {
            f"/home/{self._username}/.bashrc.d/homebrew.bashrc": File(
                content=homebrew_bashrc_contents, owner=f"{self._username}"
            )
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
        _ = decman.sh(f"mkdir -p {_BREW_PREFIX} && chown -R {self._username}:{self._username} /home/linuxbrew")

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
            user=self._username,
            mimic_login=True,
        )

    # Runs before the pacman step, so the prefix is still there for brew itself to uninstall from.
    @staticmethod
    def on_disable() -> None:
        import os
        import re
        import shutil
        import sys
        from pathlib import Path

        import decman
        import decman.core.command
        import decman.core.output

        # decman lifts this function into a standalone script, so it can only use builtins and what it imports here.
        # The username comes from the environment rather than the config for that reason.
        username: str = os.environ.get("SUDO_USER", "root")
        userhome: Path = Path("/home") / username

        paths: list[Path] = [
            Path("/home/linuxbrew"),  # The prefix: brew itself, the Cellar, and every formula
            userhome / ".cache/Homebrew",  # Downloaded bottles and the API cache, which grows without bound
            userhome / ".config/homebrew",  # The analytics trust record
            userhome / ".homebrew",  # Its lock file
        ]
        present: list[Path] = [p for p in paths if p.exists() or p.is_symlink()]

        if not present:
            return

        decman.core.output.print_warning("Homebrew is disabled, but its data is still on disk.")
        decman.core.output.print_list("These paths can be deleted:", [str(p) for p in present], 1)
        decman.core.output.print_warning(
            "Deleting them also deletes every formula brew installed. This cannot be undone."
        )

        if not sys.stdin.isatty():
            # Nothing was asked, so leave the data.
            return

        if not decman.core.output.prompt_confirm("Delete all Homebrew data?", default=False):
            return

        # A cask can install files outside the prefix, so deleting the prefix leaves them behind and brew then
        # holds no record that they were ever installed. Uninstall through brew while it still runs, as the user,
        # and before the prefix goes. This has to sit after the prompt: uninstalling a cask is itself a change to
        # the system, not part of listing what is there.
        # `brew uninstall` has no --all. List the installed casks and uninstall those.
        # `check=False` because anything brew cannot remove is not under the prefix either.
        brew: Path = Path("/home/linuxbrew/.linuxbrew/bin/brew")
        if brew.is_file():
            code, listed = decman.core.command.run(
                [str(brew), "list", "--cask", "-1"],
                user=username,
                mimic_login=True,
                env_overrides={"HOMEBREW_NO_ENV_HINTS": "1"},
            )
            # stderr is merged into this output, so a failed list must not be read as cask names.
            # A hint or an error line is not a cask, and uninstalling it would be a guess.
            cask_name = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+_.@-]*$")
            casks: list[str] = []
            if code == 0:
                casks = [name.strip() for name in listed.splitlines() if cask_name.fullmatch(name.strip())]

            if casks:
                _ = decman.prg(
                    [str(brew), "uninstall", "--cask", *casks],
                    user=username,
                    mimic_login=True,
                    pty=False,
                    check=False,
                    env_overrides={"HOMEBREW_NO_ENV_HINTS": "1"},
                )

        for path in present:
            if path.is_symlink() or path.is_file():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)

        decman.core.output.print_info("Deleted Homebrew data.")
