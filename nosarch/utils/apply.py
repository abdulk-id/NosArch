import decman
import utils.session
import utils.session_changes
from decman import Store

# Requests recorded during `on_change`. `ApplyModule.after_update` runs them, and that module is
# registered last, so every hook has already recorded what it needs. A repeated request is one entry.
_pending: set[str] = set()
_user: str | None = None
_logouts: list[str] = []
_reboots: list[str] = []

# Root commands, in the order they have to run. daemon-reload before anything that restarts a unit,
# then daemon-reexec, then the user manager, then the timer that depends on that reload.
_ROOT_ORDER: tuple[str, ...] = (
    "daemon_reload",
    "daemon_reexec",
    "user_daemon_reload",
    "eyesight_timer",
    "sysctl",
    "networkmanager",
    "journald",
    "tmpfiles",
    "udev",
    "ufw",
    "gsettings",
)


def _detach(command: str) -> list[str]:
    """Run a session daemon without decman waiting for it to exit.

    `uwsm-app` replaces itself with `systemd-run --scope`, and that waits until the daemon exits. decman waits on the
    command it started, so the flush never reaches the logout and reboot offer. `setsid -f` returns once the new
    session exists. The redirects close decman's stdout pipe; `communicate()` reads that pipe until EOF.
    """
    return ["/bin/sh", "-c", f"{command} </dev/null >/dev/null 2>&1"]


# Session commands keep the order the desktop module used to run them in. One missing session
# produces one notice for the whole list, rather than one notice per module.
_SESSION: tuple[tuple[str, str, list[str]], ...] = (
    ("hyprland", "Reloading Hyprland config", ["hyprctl", "reload", "config-only"]),
    ("waybar", "Reloading waybar", ["pkill", "--signal", "SIGUSR2", "waybar"]),
    ("swaync_config", "Reloading swaync config", ["swaync-client", "--reload-config"]),
    ("swaync_style", "Reloading swaync style", ["swaync-client", "--reload-css"]),
    (
        "portal",
        "Restarting the desktop portal",
        ["systemctl", "--user", "restart", "xdg-desktop-portal.service", "xdg-desktop-portal-hyprland.service"],
    ),
    ("hypridle", "Restarting hypridle", _detach("pkill --exact hypridle; setsid -f uwsm-app -- hypridle")),
    ("hyprpaper", "Restarting hyprpaper", _detach("pkill --exact hyprpaper; setsid -f uwsm-app -- hyprpaper")),
    ("hyprsunset", "Restarting hyprsunset", _detach("pkill --exact hyprsunset; setsid -f uwsm-app -- hyprsunset")),
    ("walker", "Restarting walker", _detach("pkill --exact walker; setsid -f walker --gapplication-service")),
    ("swayosd", "Restarting swayosd", _detach("pkill --exact swayosd-server; setsid -f uwsm-app -- swayosd-server")),
    # Nautilus loads its Python extensions at start.
    # TODO: Can potentially disrupt user's work, for example file operations like moving or copying. Need safer option
    ("nautilus", "Quitting nautilus", ["/bin/sh", "-c", "nautilus --quit || :"]),
)


def _request(name: str) -> None:
    _pending.add(name)


def _remember_user(username: str) -> None:
    global _user
    _user = username


def _note(items: list[str], description: str) -> None:
    if description not in items:
        items.append(description)


# --- Named requests. Each one records; none of them runs the command. ---


def reload_systemd() -> None:
    _request("daemon_reload")


def reexec_systemd() -> None:
    _request("daemon_reexec")


def reload_user_systemd(username: str) -> None:
    _remember_user(username)
    _request("user_daemon_reload")


def try_restart_eyesight_timer(username: str) -> None:
    _remember_user(username)
    _request("eyesight_timer")


def apply_sysctl() -> None:
    _request("sysctl")


def reload_network_manager() -> None:
    _request("networkmanager")


def restart_journald() -> None:
    _request("journald")


def clean_tmpfiles() -> None:
    _request("tmpfiles")


def reload_udev() -> None:
    _request("udev")


def restart_ufw() -> None:
    _request("ufw")


def rebuild_gsettings() -> None:
    _request("gsettings")


def reload_hyprland() -> None:
    """`config-only`, because a plain `reload` re-applies the monitor layout hyprmoncfgd owns."""

    _request("hyprland")


def reload_waybar() -> None:
    _request("waybar")


def reload_swaync_config() -> None:
    _request("swaync_config")


def reload_swaync_style() -> None:
    _request("swaync_style")


def restart_desktop_portal() -> None:
    _request("portal")


def restart_hypridle() -> None:
    _request("hypridle")


def restart_hyprpaper() -> None:
    _request("hyprpaper")


def restart_hyprsunset() -> None:
    _request("hyprsunset")


def restart_walker() -> None:
    _request("walker")


def restart_swayosd() -> None:
    _request("swayosd")


def quit_nautilus() -> None:
    _request("nautilus")


def rebuild_initramfs() -> None:
    _request("initramfs")


def request_logout(description: str) -> None:
    _note(_logouts, description)


def request_reboot(description: str) -> None:
    _note(_reboots, description)


def _clear() -> None:
    global _user
    _pending.clear()
    _logouts.clear()
    _reboots.clear()
    _user = None


def _run_root(name: str, username: str | None) -> None:
    if name == "daemon_reload":
        decman.core.output.print_info("Reloading systemd.")
        _ = decman.prg(["systemctl", "daemon-reload"])
    elif name == "daemon_reexec":
        decman.core.output.print_info("Restarting systemd.")
        _ = decman.prg(["systemctl", "daemon-reexec"])
    elif name == "user_daemon_reload" and username is not None:
        decman.core.output.print_info("Reloading systemd user units.")
        # `check=False`, because the user manager is not running when applying from a TTY.
        _ = decman.prg(["systemctl", "--user", "-M", f"{username}@", "daemon-reload"], check=False)
    elif name == "eyesight_timer" and username is not None:
        # `try-restart`, so a timer the user turned off stays off.
        _ = decman.prg(
            ["systemctl", "--user", "-M", f"{username}@", "try-restart", "nosarch-eyesight-reminder.timer"], check=False
        )
    elif name == "sysctl":
        decman.core.output.print_info("Applying kernel parameters.")
        _ = decman.prg(["sysctl", "--system", "--quiet"])
    elif name == "networkmanager":
        decman.core.output.print_info("Reloading NetworkManager.")
        _ = decman.prg(["systemctl", "reload", "NetworkManager"])
    elif name == "journald":
        decman.core.output.print_info("Restarting systemd-journald.")
        _ = decman.prg(["systemctl", "restart", "systemd-journald"])
    elif name == "tmpfiles":
        decman.core.output.print_info("Cleaning tmp files.")
        _ = decman.prg(["systemd-tmpfiles", "--create", "--clean"])
    elif name == "udev":
        decman.core.output.print_info("Reloading udev.")
        _ = decman.prg(["udevadm", "control", "--reload"])
        _ = decman.prg(["udevadm", "trigger", "--subsystem-match=power_supply", "--action=change"])
    elif name == "ufw":
        decman.core.output.print_info("Restarting firewall (ufw).")
        _ = decman.prg(["systemctl", "restart", "ufw"])
    elif name == "gsettings":
        # GSettings reads compiled cache, not .override files, so the cache has to be rebuilt.
        decman.core.output.print_info("Rebuilding GSettings cache.")
        _ = decman.prg(["glib-compile-schemas", "/usr/share/glib-2.0/schemas"])


def _run_session(commands: list[tuple[str, list[str]]]) -> None:
    if not commands:
        return

    if utils.session.has_graphical_session():
        for description, command in commands:
            decman.core.output.print_info(description)
            _ = utils.session.run_in_session(command)
        return

    decman.core.output.print_list(
        "No graphical session found. These changes will apply on the next login: ",
        [description for description, _ in commands],
        1,
    )


def flush(store: Store) -> None:
    """Run each recorded command once, then record logout and reboot for `tools/apply`."""

    pending: set[str] = set(_pending)
    username: str | None = _user
    logouts: list[str] = list(_logouts)
    reboots: list[str] = list(_reboots)
    _clear()

    for name in _ROOT_ORDER:
        if name in pending:
            _run_root(name, username)

    _run_session([(description, command) for name, description, command in _SESSION if name in pending])

    if "initramfs" in pending:
        decman.core.output.print_info("Rebuilding initramfs and updating Limine boot entries.")
        _ = decman.prg(["limine-mkinitcpio"])

    if logouts:
        decman.core.output.print_list("These changes will take effect after logging out: ", logouts, 1)
        for change in logouts:
            utils.session_changes.defer(store, "logout", change)

    if reboots:
        decman.core.output.print_list("These changes will take effect after a reboot: ", reboots, 1)
        for change in reboots:
            utils.session_changes.defer(store, "reboot", change)
