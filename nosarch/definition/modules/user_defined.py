import engine
from definition.user_config import UserConfigReader
from engine.steps import aur, flatpak, homebrew, pacman, snap


class UserDefinedModule(engine.Module):
    def __init__(self, user_config_reader: UserConfigReader) -> None:
        super().__init__(name="user_defined")
        self._user_config: UserConfigReader = user_config_reader
        self._username: str = self._user_config.user.username

    @pacman.packages
    def arch_pkgs(self) -> set[str]:
        return set(self._user_config.packaging.arch.install_packages)

    @aur.packages
    def aur_pkgs(self) -> set[str]:
        return set(self._user_config.packaging.aur.install_packages)

    @flatpak.packages
    def flatpak_pkgs(self) -> set[str]:
        if not self._user_config.packaging.flatpak.enabled:
            return set()

        return set(self._user_config.packaging.flatpak.install_packages)

    @flatpak.user_packages
    def flatpak_user_pkgs(self) -> dict[str, set[str]]:
        if not self._user_config.packaging.flatpak.enabled:
            return {}

        return {self._username: set(self._user_config.packaging.flatpak.install_user_packages)}

    @homebrew.formulae
    def brew_formulae(self) -> set[str]:
        if not self._user_config.packaging.homebrew.enabled:
            return set()

        return set(self._user_config.packaging.homebrew.install_formulae)

    @homebrew.casks
    def brew_casks(self) -> set[str]:
        if not self._user_config.packaging.homebrew.enabled:
            return set()

        return set(self._user_config.packaging.homebrew.install_casks)

    @snap.snaps
    def snaps(self) -> dict[str, str]:
        if not self._user_config.packaging.snap.enabled:
            return {}

        return self._user_config.packaging.snap.install_snaps

    @snap.classic_snaps
    def classic_snaps(self) -> dict[str, str]:
        if not self._user_config.packaging.snap.enabled:
            return {}

        return self._user_config.packaging.snap.install_classic_snaps
