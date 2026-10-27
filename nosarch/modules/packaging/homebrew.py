import os
import re
import shutil
from pathlib import Path
from typing import override

import engine
import engine.output
import utils.paths
from engine import File
from engine.steps import pacman

# Standard Homebrew-on-Linux prefix. Everything the git-clone install creates
# lives here, so teardown is a single directory removal.
_BREW_PREFIX: str = "/home/linuxbrew/.linuxbrew"
_BREW_BIN: str = f"{_BREW_PREFIX}/bin/brew"


class HomebrewModule(engine.Module):
    """
    Bootstraps Homebrew itself so the `homebrew` step has a `brew` to drive.
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
    def before_update(self) -> None:
        if os.path.exists(_BREW_BIN):
            return

        # Root phase: create the prefix and hand it to the user.
        # (brew refuses to run as root, and owning the prefix up front means the clone needs no privileges.)
        _ = engine.sh(f"mkdir -p {_BREW_PREFIX} && chown -R {self._username}:{self._username} /home/linuxbrew")

        # User phase: clone brew, link the launcher, prime the formula data.
        _ = engine.sh(
            "set -eu\n"
            + f'prefix="{_BREW_PREFIX}"\n'
            + 'if [ ! -d "$prefix/Homebrew" ]; then\n'
            + '    git clone https://github.com/Homebrew/brew "$prefix/Homebrew"\n'
            + "fi\n"
            + 'mkdir -p "$prefix/bin"\n'
            + 'ln -sf ../Homebrew/bin/brew "$prefix/bin/brew"\n'
            + '"$prefix/bin/brew" update --force --quiet\n',
            user=self._username,
        )

    # Runs before the pacman step, so the prefix is still there for brew itself to uninstall from.
    @override
    def on_disable(self) -> None:
        userhome: Path = Path("/home") / self._username

        paths: list[Path] = [
            Path("/home/linuxbrew"),  # The prefix: brew itself, the Cellar, and every formula
            userhome / ".cache/Homebrew",  # Downloaded bottles and the API cache, which grows without bound
            userhome / ".config/homebrew",  # The analytics trust record
            userhome / ".homebrew",  # Its lock file
        ]
        present: list[Path] = [p for p in paths if p.exists() or p.is_symlink()]

        if not present:
            return

        engine.output.print_warning("Homebrew is disabled, but its data is still on disk.")
        engine.output.print_list("These paths can be deleted:", [str(p) for p in present], one_per_line=True)
        engine.output.print_warning("Deleting them also deletes every formula brew installed. This cannot be undone.")

        # Without a terminal nothing is asked, so the data stays.
        if not engine.output.prompt_confirm("Delete all Homebrew data?", default=False):
            return

        # A cask can install files outside the prefix, so deleting the prefix leaves them behind and brew then
        # holds no record that they were ever installed. Uninstall through brew while it still runs, as the user,
        # and before the prefix goes. This has to sit after the prompt: uninstalling a cask is itself a change to
        # the system, not part of listing what is there.
        # `brew uninstall` has no --all. List the installed casks and uninstall those.
        # `check=False` because anything brew cannot remove is not under the prefix either.
        if Path(_BREW_BIN).is_file():
            environment: dict[str, str] = {"HOMEBREW_NO_ENV_HINTS": "1"}
            try:
                listed: str = engine.run(
                    [_BREW_BIN, "list", "--cask", "-1"], user=self._username, env=environment, capture=True
                )
            except engine.CommandFailedError:
                listed = ""
            # A hint or an error line is not a cask, and uninstalling it would be a guess.
            cask_name = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+_.@-]*$")
            casks: list[str] = [name.strip() for name in listed.splitlines() if cask_name.fullmatch(name.strip())]

            if casks:
                _ = engine.run(
                    [_BREW_BIN, "uninstall", "--cask", *casks], user=self._username, env=environment, check=False
                )

        for path in present:
            if path.is_symlink() or path.is_file():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)

        engine.output.print_info("Deleted Homebrew data.")
