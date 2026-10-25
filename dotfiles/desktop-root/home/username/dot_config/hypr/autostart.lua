-- Managed by NosArch

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
    -- Walker has no user unit. The other session utilities are user services.
    hl.exec_cmd("walker --gapplication-service")

    -- Set systemd vars
    hl.exec_cmd("systemctl --user import-environment $(env | cut -d'=' -f 1)")
    hl.exec_cmd("dbus-update-activation-environment --systemd --all")
end)
