import engine
from engine.steps import aur, flatpak, homebrew, pacman, snap
from user_config import UserConfigReader


class UserDefinedModule(engine.Module):
    def __init__(self, user_config_reader: UserConfigReader) -> None:
        super().__init__(name="user_defined")
        self._user_config: UserConfigReader = user_config_reader
        self._username: str = self._user_config.user.username

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
    def arch_pkgs(self) -> set[str]:
        return set(self._user_config.packaging.arch.install_packages)

    @aur.packages  # pyright: ignore[reportUnknownMemberType]
    def aur_pkgs(self) -> set[str]:
        return set(self._user_config.packaging.aur.install_packages)

    @flatpak.packages  # pyright: ignore[reportUnknownMemberType]
    def flatpak_pkgs(self) -> set[str]:
        if not self._user_config.packaging.flatpak.enabled:
            return set()

        return set(self._user_config.packaging.flatpak.install_packages)

    @flatpak.user_packages  # pyright: ignore[reportUnknownMemberType]
    def flatpak_user_pkgs(self) -> dict[str, set[str]]:
        if not self._user_config.packaging.flatpak.enabled:
            return {}

        return {self._username: set(self._user_config.packaging.flatpak.install_user_packages)}

    @homebrew.formulae  # pyright: ignore[reportUnknownMemberType]
    def brew_formulae(self) -> set[str]:
        if not self._user_config.packaging.homebrew.enabled:
            return set()

        return set(self._user_config.packaging.homebrew.install_formulae)

    @homebrew.casks  # pyright: ignore[reportUnknownMemberType]
    def brew_casks(self) -> set[str]:
        if not self._user_config.packaging.homebrew.enabled:
            return set()

        return set(self._user_config.packaging.homebrew.install_casks)

    @snap.snaps  # pyright: ignore[reportUnknownMemberType]
    def snaps(self) -> dict[str, str]:
        if not self._user_config.packaging.snap.enabled:
            return {}

        return self._user_config.packaging.snap.install_snaps

    @snap.classic_snaps  # pyright: ignore[reportUnknownMemberType]
    def classic_snaps(self) -> dict[str, str]:
        if not self._user_config.packaging.snap.enabled:
            return {}

        return self._user_config.packaging.snap.install_classic_snaps
