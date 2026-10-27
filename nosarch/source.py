import engine
import engine.output
import utils.custom_packages
from modules.apply import ApplyModule
from modules.basic_setup import BasicSetupModule
from modules.desktop import DesktopModule
from modules.packaging.flatpak import FlatpakModule
from modules.packaging.homebrew import HomebrewModule
from modules.packaging.snap import SnapModule
from modules.setups.ai_setup import AISetupModule
from modules.setups.creative_setup import CreativeSetupModule
from modules.setups.dev_setup import DevSetupModule
from modules.setups.gaming_setup import GamingSetupModule
from modules.system import SystemModule
from modules.theme import ThemingModule
from modules.user_defined import UserDefinedModule
from user_config import UserConfigReader


def setup() -> engine.Setup:
    user_config: UserConfigReader = UserConfigReader.load()
    username: str = user_config.user.username

    nosarch: engine.Setup = engine.Setup()

    # Packaging ===
    nosarch.aur.build_user = "aurbuilduser"
    nosarch.aur.clean_chroot = user_config.advanced.build_aur_in_clean_chroot
    nosarch.aur.custom_pkgbuild_dir = utils.custom_packages.package_dir
    nosarch.aur.ignored |= {"xdg-terminal-exec"}

    if user_config.packaging.flatpak.enabled:
        nosarch.steps.append("flatpak")
    elif user_config.packaging.flatpak.install_packages or user_config.packaging.flatpak.install_user_packages:
        engine.output.print_warning("[PACKAGING] Flatpak is disabled. Ignoring user packages")

    if user_config.packaging.homebrew.enabled:
        nosarch.homebrew_user = username  # brew cannot run as root
        nosarch.steps.append("homebrew")
    elif user_config.packaging.homebrew.install_formulae or user_config.packaging.homebrew.install_casks:
        engine.output.print_warning("[PACKAGING] Homebrew is disabled. Ignoring user packages")

    if user_config.packaging.snap.enabled:
        nosarch.steps.append("snap")
    elif user_config.packaging.snap.install_snaps or user_config.packaging.snap.install_classic_snaps:
        engine.output.print_warning("[PACKAGING] Snap is disabled. Ignoring user packages")
    # ===

    # Users and groups ===
    nosarch.users.append(
        engine.User(
            username=username,
            group=username,
            home=f"/home/{username}",
            shell="/usr/bin/bash",
            groups=(username, "wheel")
            + (("libvirt",) if user_config.setups.basic.enable_virtualization else ())
            # Allow user access to controller devices (/dev/input)
            + (("input",) if user_config.setups.gaming.enabled else ()),
        )
    )
    nosarch.users.append(engine.User(username="aurbuilduser", home="/var/lib/aurbuilduser", system=True))
    # ===

    # Modules ===
    # Disabled modules are added too, so their on_disable can run on the run that disables them.
    nosarch.add(SystemModule(user_config))
    nosarch.add(DesktopModule(user_config))
    nosarch.add(ThemingModule(user_config))

    nosarch.add(HomebrewModule(username), enabled=user_config.packaging.homebrew.enabled)
    nosarch.add(FlatpakModule(username), enabled=user_config.packaging.flatpak.enabled)
    nosarch.add(SnapModule(username), enabled=user_config.packaging.snap.enabled)

    # The setups extend the desktop. It is always registered for now; the check is for when NosArch allows headless
    # installs.
    desktop_enabled: bool = any(module.name == "desktop" for module in nosarch.modules)
    setups: list[tuple[str, bool, engine.Module]] = [
        ("Basic", user_config.setups.basic.enabled, BasicSetupModule(user_config)),
        ("AI", user_config.setups.ai.enabled, AISetupModule(user_config)),
        ("Creative", user_config.setups.creative.enabled, CreativeSetupModule(user_config)),
        ("Dev", user_config.setups.dev.enabled, DevSetupModule(user_config)),
        ("Gaming", user_config.setups.gaming.enabled, GamingSetupModule(user_config)),
    ]
    for label, enabled, module in setups:
        if enabled and not desktop_enabled:
            raise ValueError(f"[SETUPS] {label} setup requires Desktop module to be enabled.")
        nosarch.add(module, enabled=enabled)

    nosarch.add(UserDefinedModule(user_config))

    # Last on purpose. Its after_update runs the queued apply commands after every other after_update. Do not register
    # a module after this.
    nosarch.add(ApplyModule())
    # ===

    return nosarch
