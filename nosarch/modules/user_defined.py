import decman
import user_config.config_reader as userConfig
from decman.plugins import aur, flatpak, pacman
from plugins import homebrew

userConfig.load()


class UserDefinedModule(decman.Module):
    def __init__(self) -> None:
        super().__init__(name="user_defined")

    @pacman.packages  # pyright: ignore[reportUnknownMemberType]
    def arch_pkgs(self) -> set[str]:
        return set(userConfig.get_str_list("user_packages.arch"))

    @aur.packages  # pyright: ignore[reportUnknownMemberType]
    def aur_pkgs(self) -> set[str]:
        return set(userConfig.get_str_list("user_packages.aur"))

    @flatpak.packages  # pyright: ignore[reportUnknownMemberType]
    def flatpak_pkgs(self) -> set[str]:
        return set(userConfig.get_str_list("user_packages.flatpak"))

    @flatpak.user_packages  # pyright: ignore[reportUnknownMemberType]
    def flatpak_user_pkgs(self) -> dict[str, set[str]]:
        return {userConfig.get_str("user.username"): set(userConfig.get_str_list("user_packages.flatpak_user"))}

    @homebrew.formulae  # pyright: ignore[reportUnknownMemberType]
    def brew_formulae(self) -> set[str]:
        return set(userConfig.get_str_list("user_packages.homebrew_formulae"))

    @homebrew.casks  # pyright: ignore[reportUnknownMemberType]
    def brew_casks(self) -> set[str]:
        return set(userConfig.get_str_list("user_packages.homebrew_casks"))
