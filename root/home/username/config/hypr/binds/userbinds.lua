-- === USER BINDS ===
-- See https://wiki.hypr.land/Configuring/Basics/Binds/

-- === App Binds ===
hl.bind("SUPER + SPACE", hl.dsp.exec_cmd("nosarch-launcher"), { description = "Show Launcher" })
hl.bind("SUPER + RETURN", hl.dsp.exec_cmd("nosarch-launch-app terminal"), { description = "Open Terminal" })
hl.bind("SUPER + SHIFT + F", hl.dsp.exec_cmd("nosarch-launch-app files"), { description = "Open File Manager" })
hl.bind("SUPER + SHIFT + B", hl.dsp.exec_cmd("nosarch-launch-app browser"), { description = "Open Default Browser" })
hl.bind("SUPER + SHIFT + ALT + B", hl.dsp.exec_cmd("nosarch-launch-app browser-private"),
    { description = "Open Default Browser (private mode)" })
hl.bind("SUPER + SHIFT + E", hl.dsp.exec_cmd("nosarch-launch-app editor"), { description = "Open Editor" })

-- === Shortcut binds ===
hl.bind("SUPER + SHIFT + A",
    hl.dsp.exec_cmd("flatpak run --command=io.github.alainm23.planify.quick-add io.github.alainm23.planify"),
    { description = "Quick-Add Task to Planify" })

-- === Capture Binds ===
hl.bind("PRINT", hl.dsp.exec_cmd("nosarch-capture screenshot region"), { description = "Screenshow a region" })
hl.bind("SUPER + PRINT", hl.dsp.exec_cmd("nosarch-capture screenshot window"), { description = "Screenshow a window" })
hl.bind("SUPER + SHIFT + PRINT", hl.dsp.exec_cmd("nosarch-capture screenshot monitor"),
    { description = "Screenshow a monitor" })
hl.bind("SUPER + ALT + PRINT", hl.dsp.exec_cmd("nosarch-capture colorpick"), { description = "Open Color picker" })
hl.bind("SUPER + SHIFT + T", hl.dsp.exec_cmd("nosarch-capture extract-text"),
    { description = "Extract text from screen" })

-- === Notification binds ===
hl.bind("SUPER + N", hl.dsp.exec_cmd("swaync-client -t"))

-- === Power Binds ===
-- hl.bind("SUPER + M", hl.dsp.exec_cmd("command -v hyprshutdown >/dev/null 2>&1 && hyprshutdown || hyprctl dispatch exit"), { description = "Exit Hyprland" })

hl.bind("XF86PowerOff", hl.dsp.exec_cmd("vicinae vicinae://launch/power"), { description = "Power options" })
hl.bind("SUPER + CTRL + L", hl.dsp.exec_cmd("nosarch-session lock"), { description = "Lock screen" })
