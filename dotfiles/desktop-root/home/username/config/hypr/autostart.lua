-- === AUTOSTART ===
-- See https://wiki.hypr.land/Configuring/Basics/Autostart/

-- Autostart necessary processes (like notifications daemons, status bars, etc.)
-- Or execute your favorite apps at launch like this:
-- hl.on("hyprland.start", function()
--     hl.exec_cmd(terminal)
--     hl.exec_cmd("nm-applet")
--     hl.exec_cmd("waybar & hyprpaper & firefox") -- Execute waybar, hyprpaper, firefox
-- end)


hl.on("hyprland.start", function()
    hl.exec_cmd("systemctl --user start hyprpolkitagent")
    hl.exec_cmd("uwsm-app -- hypridle")
    hl.exec_cmd("uwsm-app -- hyprsunset")
    -- hl.exec_cmd("uwsm-app -- vicinae server")
    hl.exec_cmd("walker --gapplication-service")

    hl.exec_cmd("uwsm-app -- quickshell --no-duplicate")
    -- Replaced by Quickshell
    -- hl.exec_cmd("uwsm-app -- waybar")
    -- hl.exec_cmd("uwsm-app -- swaync")
    -- hl.exec_cmd("uwsm-app -- hyprpaper")
    -- hl.exec_cmd("uwsm-app -- swayosd-server")

    -- Set systemd vars
    hl.exec_cmd("systemctl --user import-environment $(env | cut -d'=' -f 1)")
    hl.exec_cmd("dbus-update-activation-environment --systemd --all")
end)
