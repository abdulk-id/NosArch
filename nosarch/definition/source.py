import nosarch.engine
import nosarch.engine.output
import nosarch.utils.custom_packages
from nosarch.definition.modules.apply import ApplyModule
from nosarch.definition.modules.basic_setup import BasicSetupModule
from nosarch.definition.modules.desktop import DesktopModule
from nosarch.definition.modules.packaging.flatpak import FlatpakModule
from nosarch.definition.modules.packaging.homebrew import HomebrewModule
from nosarch.definition.modules.packaging.snap import SnapModule
from nosarch.definition.modules.setups.ai_setup import AISetupModule
from nosarch.definition.modules.setups.creative_setup import CreativeSetupModule
from nosarch.definition.modules.setups.dev_setup import DevSetupModule
from nosarch.definition.modules.setups.gaming_setup import GamingSetupModule
from nosarch.definition.modules.system import SystemModule
from nosarch.definition.modules.theme import ThemingModule
from nosarch.definition.modules.user_defined import UserDefinedModule
from nosarch.definition.user_config import UserConfigReader


def setup() -> nosarch.engine.Setup:
    user_config: UserConfigReader = UserConfigReader.load()
    username: str = user_config.user.username

    system: nosarch.engine.Setup = nosarch.engine.Setup()

    # Packaging ===
    system.aur.build_user = "aurbuilduser"
    system.aur.clean_chroot = user_config.advanced.build_aur_in_clean_chroot
    system.aur.custom_pkgbuild_dir = nosarch.utils.custom_packages.package_dir
    system.aur.ignored |= {"xdg-terminal-exec"}

    if user_config.packaging.flatpak.enabled:
        system.steps.append("flatpak")
    elif user_config.packaging.flatpak.install_packages or user_config.packaging.flatpak.install_user_packages:
        nosarch.engine.output.print_warning("[PACKAGING] Flatpak is disabled. Ignoring user packages")

    if user_config.packaging.homebrew.enabled:
        system.homebrew_user = username  # brew cannot run as root
        system.steps.append("homebrew")
    elif user_config.packaging.homebrew.install_formulae or user_config.packaging.homebrew.install_casks:
        nosarch.engine.output.print_warning("[PACKAGING] Homebrew is disabled. Ignoring user packages")

    if user_config.packaging.snap.enabled:
        system.steps.append("snap")
    elif user_config.packaging.snap.install_snaps or user_config.packaging.snap.install_classic_snaps:
        nosarch.engine.output.print_warning("[PACKAGING] Snap is disabled. Ignoring user packages")
    # ===

    # Users and groups ===
    system.users.append(
        nosarch.engine.User(
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
    system.users.append(nosarch.engine.User(username="aurbuilduser", home="/var/lib/aurbuilduser", system=True))
    # ===

    # Modules ===
    # Disabled modules are added too, so their on_disable can run on the run that disables them.
    system.add(SystemModule(user_config))
    system.add(DesktopModule(user_config))
    system.add(ThemingModule(user_config))

    system.add(HomebrewModule(username), enabled=user_config.packaging.homebrew.enabled)
    system.add(FlatpakModule(username), enabled=user_config.packaging.flatpak.enabled)
    system.add(SnapModule(username), enabled=user_config.packaging.snap.enabled)

    # The setups extend the desktop. It is always registered for now; the check is for when NosArch allows headless
    # installs.
    desktop_enabled: bool = any(module.name == "desktop" for module in system.modules)
    setups: list[tuple[str, bool, nosarch.engine.Module]] = [
        ("Basic", user_config.setups.basic.enabled, BasicSetupModule(user_config)),
        ("AI", user_config.setups.ai.enabled, AISetupModule(user_config)),
        ("Creative", user_config.setups.creative.enabled, CreativeSetupModule(user_config)),
        ("Dev", user_config.setups.dev.enabled, DevSetupModule(user_config)),
        ("Gaming", user_config.setups.gaming.enabled, GamingSetupModule(user_config)),
    ]
    for label, enabled, module in setups:
        if enabled and not desktop_enabled:
            raise ValueError(f"[SETUPS] {label} setup requires Desktop module to be enabled.")
        system.add(module, enabled=enabled)

    system.add(UserDefinedModule(user_config))

    # Last on purpose. Its after_update runs the queued apply commands after every other after_update. Do not register
    # a module after this.
    system.add(ApplyModule())
    # ===

    return system
