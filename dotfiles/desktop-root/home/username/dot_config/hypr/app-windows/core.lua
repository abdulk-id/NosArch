-- File-picker windows
hl.window_rule({
    name = "file-picker-windows-rules",
    match = {
        class = "(xdg-desktop-portal-gtk|sublime_text|DesktopEditors|org.gnome.Nautilus)",
        title =
        "^(Open.*|Save.*Files?|Save.*As|Save|All Files|.*wants to (open|save).*|[Cc]hoose.*|Enter name of file to save to.*|Select [Ff]older.*)"
    },
    -- Static effects
    float = true,
    size = { "875", "600" },
    center = true,
})

-- Media windows
hl.window_rule({
    name = "media-window-rules",
    match = {
        class =
        "^(zoom|vlc|mpv|org.kde.kdenlive|com.obsproject.Studio|com.github.PintaProject.Pinta|imv|org.gnome.NautilusPreviewer)$"
    },
    -- Dynamic effects
    opacity = "1.0 override 1.0 override" -- No transparence on media windows
})

-- Satty
hl.window_rule({
    name = "satty-screenshot-annotation-rule",
    match = {
        class = "com.gabm.satty"
    },
    -- Static effects
    float = true,
    center = true,
})

-- Webcam overlay for screen recording
hl.window_rule({
    name = "webcam-overlay-rules",
    match = {
        title = "WebcamOverlay",
    },
    -- Static effects
    float = true,
    move = { "(monitor_w - window_w - 40)", "(monitor_h - window_h - 40)" },
    no_initial_focus = true,
    pin = true,

    -- Dynamic effects
    no_dim = true,
    no_follow_mouse = true,
})

-- Zenity dialogs
hl.window_rule({
    name = "zenity-dialog-rules",
    match = {
        class = "^(zenity)$",
    },
    -- Static effects
    float = true,
    center = true,
    pin = true,

    -- Dynamic effects
    stay_focused = true,
    border_size = 4,
    rounding = 20,
    no_blur = true,
    no_dim = true,
    no_vrr = true,
    opaque = true,
})

-- GNOME Calculator
hl.window_rule({
    name = "gnome-calculator-rules",
    match = {
        class = "org.gnome.Calculator"
    },
    -- Static effects
    float = true,
    size = { "400", "600" },
    center = true
})

-- GNOME clocks
hl.window_rule({
    name = "gnome-clocks-rules",
    match = {
        class = "org.gnome.clocks"
    },
    -- Static effects
    float = true,
    size = { "400", "600" },
    center = true
})
