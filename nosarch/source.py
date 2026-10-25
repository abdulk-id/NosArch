import decman.config
import decman.core.output
import utils.aur_chroot
from decman.extras.users import User, UserManager
from decman.plugins import flatpak as flatpak_plugin
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
from plugins import homebrew
from plugins import snap as snap_plugin
from user_config import UserConfigReader

# User config
user_config: UserConfigReader = UserConfigReader.load()
_username: str = user_config.user.username

# NosArch Works ===
if user_config.advanced.enable_nosarch_works:
    # decman.config.debug_output = True
    decman.config.quiet_output = False

    decman.pacman.packages |= {"desktop-file-utils", "lynis", "namcap", "pacman-contrib", "shellcheck"}

    """
    # Checks ---
    DISABLE_CHECKS_PARAM: bool = os.environ.get("NOSARCH_DECMAN_SKIP_CHECKS") == "1"

    if DISABLE_CHECKS_PARAM:
        decman.core.output.print_warning("Skipping NosArch pre-checks.")
    else:
        decman.core.output.print_summary("Running NosArch pre-checks.")
    """

else:
    decman.config.debug_output = False
    decman.config.quiet_output = True
# ===

# Decman configuration ===
decman.config.arch = "x86_64"
decman.execution_order = ["files", "pacman", "aur", "systemd"]

decman.aur.build_dir = "/var/cache/decman/build"

if utils.aur_chroot.is_available():
    # NosArch's own pacman hooks must not apply to the AUR build chroot. `mkarchroot` evaluates host hooks against an
    # empty root, where no `Depends =` can be satisfied, which aborts the build.
    decman.aur.commands = utils.aur_chroot.NoHostHooksAurCommands()
# ===

# Packaging ===
if user_config.packaging.flatpak.enabled:
    # Register the plugin here manually. decman only consults a plugin's `available()` when it is imported, which
    # happens before pacman installs the runtime, so on the run that enables Flatpak the plugin isn't registered yet
    # and its step would be skipped.
    if "flatpak" not in decman.plugins:
        decman.plugins["flatpak"] = flatpak_plugin.Flatpak()

    decman.execution_order.append("flatpak")
else:
    # Dropping the module is what runs `FlatpakModule.on_disable`, which offers to delete what the runtime
    # left behind. It cannot be driven from here: decman only runs that script when a registered module
    # disappears.
    _skipped_flatpak: list[str] = user_config.packaging.flatpak.install_packages
    _skipped_flatpak += user_config.packaging.flatpak.install_user_packages
    if _skipped_flatpak:
        decman.core.output.print_warning("[PACKAGING] Flatpak is disabled. Ignoring user packages")


if user_config.packaging.homebrew.enabled:
    # Registered here directly rather than left to `available()`, which decman only consults when it imports
    # a plugin. That happens before `HomebrewModule` bootstraps brew in `before_update`, so on the run that
    # enables Homebrew the plugin isn't registered yet and its step would be skipped.
    homebrew.plugin.user = _username  # brew cannot run as root
    decman.plugins["homebrew"] = homebrew.plugin
    decman.execution_order.append("homebrew")
else:
    # Dropping the module is what runs `HomebrewModule.on_disable`, which removes the prefix. It cannot be
    # driven from here: decman only runs that script when a registered module disappears.
    _skipped_homebrew: list[str] = user_config.packaging.homebrew.install_formulae
    _skipped_homebrew += user_config.packaging.homebrew.install_casks
    if _skipped_homebrew:
        decman.core.output.print_warning("[PACKAGING] Homebrew is disabled. Ignoring user packages")


if user_config.packaging.snap.enabled:
    # Registered here directly rather than left to `available()`, which decman only consults when it
    # imports a plugin. That happens before the AUR step installs snapd, so on the run that enables
    # Snap the plugin isn't registered yet and its step would be skipped. The plugin reports a missing
    # `snap` itself, which is what a dry run of that first run will see.
    decman.plugins["snap"] = snap_plugin.plugin
    decman.execution_order.append("snap")
else:
    # Dropping the module is what runs `SnapModule.on_disable`, which offers to delete what snap
    # left behind. It cannot be driven from here: decman only runs that script when a registered
    # module disappears.
    _skipped_snaps: dict[str, str] = user_config.packaging.snap.install_snaps
    _skipped_snaps |= user_config.packaging.snap.install_classic_snaps
    if _skipped_snaps:
        decman.core.output.print_warning("[PACKAGING] Snap is disabled. Ignoring user packages")
# ===

# User and Group management ===
userManager: UserManager = UserManager()

userManager.add_user(
    User(
        username=_username,
        group=_username,
        home=f"/home/{_username}",
        shell="/usr/bin/bash",
        groups=(_username, "wheel")
        + (("libvirt",) if user_config.setups.basic.enable_virtualization else ())
        + (
            ("input",) if user_config.setups.gaming.enabled else ()
            # Allow user access to controller devices (/dev/input)
        ),
        system=False,
    )
)

userManager.add_user(User(username="aurbuilduser", home="/var/lib/aurbuilduser", system=True))
decman.aur.makepkg_user = "aurbuilduser"

decman.modules.append(userManager)
# ===

# Decman modules ===
decman.modules.append(SystemModule(user_config))
decman.modules.append(DesktopModule(user_config))
decman.modules.append(ThemingModule(user_config))

if user_config.packaging.homebrew.enabled:
    decman.modules.append(HomebrewModule(_username))

if user_config.packaging.flatpak.enabled:
    decman.modules.append(FlatpakModule())

if user_config.packaging.snap.enabled:
    decman.modules.append(SnapModule())

desktop_enabled: bool = any(module.name == "desktop" for module in decman.modules)

if user_config.setups.basic.enabled:
    if desktop_enabled:
        decman.modules.append(BasicSetupModule(user_config))
    else:
        decman.core.output.print_error("[SETUPS] Basic setup requires Desktop module to be enabled.")
        raise SystemExit()

if user_config.setups.ai.enabled:
    if desktop_enabled:
        decman.modules.append(AISetupModule(user_config))
    else:
        decman.core.output.print_error("[SETUPS] AI setup requires Desktop module to be enabled.")
        raise SystemExit()

if user_config.setups.creative.enabled:
    if desktop_enabled:
        decman.modules.append(CreativeSetupModule(user_config))
    else:
        decman.core.output.print_error("[SETUPS] Creative setup requires Desktop module to be enabled.")
        raise SystemExit()

if user_config.setups.dev.enabled:
    if desktop_enabled:
        decman.modules.append(DevSetupModule(user_config))
    else:
        decman.core.output.print_error("[SETUPS] Dev setup requires Desktop module to be enabled.")
        raise SystemExit()

if user_config.setups.gaming.enabled:
    if desktop_enabled:
        decman.modules.append(GamingSetupModule(user_config))
    else:
        decman.core.output.print_error("[SETUPS] Gaming setup requires Desktop module to be enabled.")
        raise SystemExit()

decman.modules.append(UserDefinedModule(user_config))

# Last on purpose, and in its own statement. Its after_update runs the queued apply commands
# after every other after_update. Do not register a module after this.
decman.modules.append(ApplyModule())
# ===
