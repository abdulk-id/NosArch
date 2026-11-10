import engine
import engine.output
import utils.session

# Requests recorded during `on_change`. `ApplyModule.after_update` runs them, and that module is
# registered last, so every hook has already recorded what it needs. A repeated request is one entry.
_pending: set[str] = set()
_user: str | None = None

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
    """Run a session process without the run waiting for it to exit.

    Walker does not exit. `setsid -f` returns once the new session exists. The redirects close the output pipe,
    which the run reads until EOF.
    """
    return ["/bin/sh", "-c", f"{command} </dev/null >/dev/null 2>&1"]


def _restart_user_service(unit: str) -> list[str]:
    """Restart a user service, and stop a leftover uwsm app scope of the same program.

    `systemctl restart` returns once the unit is up. The scope stop is a no-op once that program is the service.
    A scope name such as `swayosd-server` still matches `app-*swayosd*`.
    """
    return ["/bin/sh", "-c", f"systemctl --user stop 'app-*{unit}*.scope'; systemctl --user restart {unit}.service"]


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
    ("hypridle", "Restarting hypridle", _restart_user_service("hypridle")),
    ("hyprpaper", "Restarting hyprpaper", _restart_user_service("hyprpaper")),
    ("hyprsunset", "Restarting hyprsunset", _restart_user_service("hyprsunset")),
    ("walker", "Restarting walker", _detach("pkill --exact walker; setsid -f walker --gapplication-service")),
    ("swayosd", "Restarting swayosd", _restart_user_service("swayosd")),
    # Nautilus loads its Python extensions at start.
    # TODO: Can potentially disrupt user's work, for example file operations like moving or copying. Need safer option
    ("nautilus", "Quitting nautilus", ["/bin/sh", "-c", "nautilus --quit || :"]),
)


def _request(name: str) -> None:
    _pending.add(name)


def _remember_user(username: str) -> None:
    global _user
    _user = username


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
    engine.request_logout(description)


def request_reboot(description: str) -> None:
    engine.request_reboot(description)


def _clear() -> None:
    global _user
    _pending.clear()
    _user = None


def _run(cmd: list[str]) -> None:
    """Run one command. A failure is reported, and the commands after it still run.

    The report is whatever the engine already prints for a non-zero exit. Anything else that goes
    wrong is printed the same way. Neither one stops the rest of the list.
    """

    try:
        _ = engine.run(cmd, check=False)
    except Exception as error:
        engine.output.print_warning(str(error))


def _run_root(name: str, username: str | None) -> None:
    if name == "daemon_reload":
        engine.output.print_info("Reloading systemd.")
        _run(["systemctl", "daemon-reload"])
    elif name == "daemon_reexec":
        engine.output.print_info("Restarting systemd.")
        _run(["systemctl", "daemon-reexec"])
    elif name == "user_daemon_reload" and username is not None:
        engine.output.print_info("Reloading systemd user units.")
        # The user manager is not running when applying from a TTY.
        _run(["systemctl", "--user", "-M", f"{username}@", "daemon-reload"])
    elif name == "eyesight_timer" and username is not None:
        # `try-restart`, so a timer the user turned off stays off.
        _run(["systemctl", "--user", "-M", f"{username}@", "try-restart", "nosarch-eyesight-reminder.timer"])
    elif name == "sysctl":
        engine.output.print_info("Applying kernel parameters.")
        _run(["sysctl", "--system", "--quiet"])
    elif name == "networkmanager":
        engine.output.print_info("Reloading NetworkManager.")
        _run(["systemctl", "reload", "NetworkManager"])
    elif name == "journald":
        engine.output.print_info("Restarting systemd-journald.")
        _run(["systemctl", "restart", "systemd-journald"])
    elif name == "tmpfiles":
        engine.output.print_info("Cleaning tmp files.")
        _run(["systemd-tmpfiles", "--create", "--clean"])
    elif name == "udev":
        engine.output.print_info("Reloading udev.")
        _run(["udevadm", "control", "--reload"])
        _run(["udevadm", "trigger", "--subsystem-match=power_supply", "--action=change"])
    elif name == "ufw":
        engine.output.print_info("Restarting firewall (ufw).")
        _run(["systemctl", "restart", "ufw"])
    elif name == "gsettings":
        # GSettings reads compiled cache, not .override files, so the cache has to be rebuilt.
        engine.output.print_info("Rebuilding GSettings cache.")
        _run(["glib-compile-schemas", "/usr/share/glib-2.0/schemas"])


def _run_session(commands: list[tuple[str, list[str]]]) -> None:
    if not commands:
        return

    try:
        graphical = utils.session.has_graphical_session()
    except Exception as error:
        engine.output.print_warning(str(error))
        graphical = False

    if graphical:
        for description, command in commands:
            engine.output.print_info(description)
            try:
                _ = utils.session.run_in_session(command)
            except Exception as error:
                engine.output.print_warning(str(error))
        return

    engine.output.print_list(
        "No graphical session found. These changes will apply on the next login:",
        [description for description, _ in commands],
        one_per_line=True,
    )


def flush() -> None:
    """Run each recorded command once. Logout and reboot requests go to the engine, which offers them at the end."""

    pending: set[str] = set(_pending)
    username: str | None = _user
    _clear()

    for name in _ROOT_ORDER:
        if name in pending:
            _run_root(name, username)

    _run_session([(description, command) for name, description, command in _SESSION if name in pending])

    if "initramfs" in pending:
        engine.output.print_info("Rebuilding initramfs and updating Limine boot entries.")
        _run(["limine-mkinitcpio"])
