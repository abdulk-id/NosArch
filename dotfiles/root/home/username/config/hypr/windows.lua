-- === WINDOWS AND WORKSPACES ===
-- See https://wiki.hypr.land/Configuring/Window-Rules/ for more
-- See https://wiki.hypr.land/Configuring/Workspace-Rules/ for workspace rules

-- Ignore maximize requests from all apps. You'll probably like this.
hl.window_rule({
    name = "suppress-maximize-events",
    match = {
        class = ".*"
    },
    -- Static effects
    suppress_event = "maximize",
})

-- Fix some dragging issues with XWayland
hl.window_rule({
    name = "fix-xwayland-drags",
    match = {
        class = "^$",
        title = "^$",
        xwayland = true,
        float = true,
        fullscreen = false,
        pin = false,
    },
    -- Dynamic effects
    no_focus = true
})

-- Hyprland-run window rule
hl.window_rule({
    name = "move-hyprland-run",
    match = {
        class = "hyprland-run",
    },
    -- Static effects
    float = true,
    move = { "20", "monitor_h - 120" }
})

-- Vicinae layer rule
hl.layer_rule({
    name = "vicinae-blur",
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

-- File-picker windows
hl.window_rule({
    name = "file-picker-windows-rules",
    match = {
        class = "(xdg-desktop-portal-gtk|sublime_text|DesktopEditors|org.gnome.Nautilus)",
        -- title = "^(Open.*Files?|Open [Ff]older.*|Save.*Files?|Save.*As|Save|All Files|.*wants to (open|save).*|[Cc]hoose.*|Enter name of file to save to.*|Select [Ff]older.*)"
        title =
        "^(Open.*|Save.*Files?|Save.*As|Save|All Files|.*wants to (open|save).*|[Cc]hoose.*|Enter name of file to save to.*|Select [Ff]older.*)"
    },
    -- Static effects
    float = true,
    size = { "875", "600" },
    center = true,
})

-- Define terminal tag to style them uniformly
-- TODO: Removable?? No window rules tagging windows with 'terminal' tag
hl.window_rule({
    name = "tag-terminal-windows",
    match = {
        class = "(Alacritty|kitty|com.mitchellh.ghostty)"
    },
    tag = "+terminal"
})

-- ## App-specific tweaks ##

-- 1password
hl.window_rule({
    name = "1password-rules",
    match = {
        class = "^(1[p|P]assword)$"
    },
    -- Static effects
    float = true,
    size = { "875", "600" },
    center = true,

    -- Dynamic effects
    no_screen_share = true,
})

-- Bitwarden
hl.window_rule({
    name = "bitwarden-rules",
    match = {
        class = "^([b|B]itwarden)$"
    },
    -- Static effects
    float = true,
    size = { "875", "600" },
    center = true,

    -- Dynamic effects
    no_screen_share = true,
})

-- Browser rules
hl.window_rule({
    name = "chromium-based-browser-rules",
    match = {
        class = "((google-)?[cC]hrom(e|ium)|[bB]rave-browser|[mM]icrosoft-edge|Vivaldi-stable|[hH]elium)"
    },
    -- Static effects
    tile = true, -- Force chromium-based browsers into a tile to deal with --app bug

    -- Dynamic effects
    opacity = "1.0 override 0.97 override"
})
hl.window_rule({
    name = "firefox-based-browser-rules",
    match = {
        class = "([fF]irefox|[zZ]en|[lL]ibrewolf)"
    },
    -- Dynamic effects
    opacity = "1.0 override 0.97 override"
})
hl.window_rule({
    name = "browser-video-site-opacity-rules",
    match = {
        initial_title = "((?i)(?:[a-z0-9-]+\\.)*youtube\\.com_/|app\\.zoom\\.us_/wc/home)",
    },
    -- Static effects
    content = "video",

    -- Dynamic effects
    opacity = "1.0 override 1.0 override" -- Some video sites should never have opacity applied to them
})

-- Picture-in-picture window overlays
hl.window_rule({
    name = "picture-in-picture-rules",
    match = {
        title = "(Picture[\\s-]?in[\\s-]?Picture)"
    },
    -- Static effects
    float = true,
    move = { "(monitor_w - window_w - 25)", "(monitor_h - window_h - 50)" }, -- Move to bottom-right corner of screen
    size = { "384", "216" },
    pin = true,
    content = "video",

    -- Dynamic effects
    border_size = 3,
    opacity = "1.0 override 1.0 override",
    keep_aspect_ratio = true,
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

-- DaVinci Resolve
hl.window_rule({
    name = "davinci-resolve-rules",
    match = {
        class = ".*[Rr]esolve.*",
        float = true,
    },
    -- Dynamic effects
    stay_focused = true, -- Focus floating DaVinci Resolve dialog windows
})

-- Jetbrains rules
-- For XWayland IDEs only, not needed in Wayland IDEs.
hl.window_rule({
    -- Fix splash screen showing in weird places and prevent annoying focus takeovers
    name = "jetbrains-splash-rules",
    match = {
        class = "^(jetbrains-.*)$",
        title = "^(splash)$",
        xwayland = true,
        float = true,
    },
    -- Static effects
    center = true,

    -- Dynamic effects
    border_size = 0,
    no_focus = true,
})
hl.window_rule({
    name = "jetbrains-popup-rules",
    match = {
        class = "^(jetbrains-.*)$",
        title = "^()$",
        xwayland = true,
        float = true,
    },
    -- Static effects
    center = true, -- Center popups/find windows

    -- Dynamic effects
    stay_focused = true, -- Enabling this makes it possible to provide input in popup dialogs (search window, new file, etc.)
    min_size = { "(monitor_w * 0.5)", "(monitor_h * 0.5)" },
    border_size = 0,
})
hl.window_rule({
    name = "jetbrains-tooltips-rules",
    match = {
        class = "^(jetbrains-.*)$",
        title = "^(win.*)$",
        xwayland = true,
        float = true,
    },
    -- Static effects
    no_initial_focus = true -- Disable window flicker when autocomplete or tooltips appear
})
hl.window_rule({
    name = "manual-jetbrains-window-focus",
    match = {
        class = "^(jetbrains-.*)$",
        xwayland = true,
    },
    -- Dynamic effects
    no_follow_mouse = true, -- Disable mouse focus
})

-- QEMU
hl.window_rule({
    name = "qemu-rules",
    match = {
        class = "qemu"
    },
    -- Dynamic effects
    opacity = "1.0 override 1.0 override",
})

-- Steam
hl.window_rule({
    name = "steam-rules",
    match = {
        class = "steam"
    },
    -- Static effects
    float = true,

    -- Dynamic effects
    idle_inhibit = "always",
    opacity = "1.0 override 1.0 override",
})
hl.window_rule({
    name = "also-steam-rules",
    match = {
        class = "steam",
        title = "^Steam$"
    },
    -- Static effects
    size = { "1100", "700" },
    center = true,
})
hl.window_rule({
    name = "steam-friends-rules",
    match = {
        class = "steam",
        title = "Friends List",
    },
    -- Static effects
    size = { "460", "800" },
})
hl.window_rule({
    name = "steam-big-picture-rules",
    match = {
        class = "steam",
        title = "Steam Big Picture Mode",
    },
    -- Static effects
    fullscreen = true,
    content = "game"
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
})

-- Localsend
hl.window_rule({
    name = "localsend-rules",
    match = {
        class = "localsend"
    },
    -- Static effects
    float = true,
    size = { "400", "600" },
    center = true
})

-- Gear Level
hl.window_rule({
    name = "gearlever-rules",
    match = {
        class = "it.mijorus.gearlever"
    },
    -- Static effects
    float = true,
    size = { "600", "600" },
    center = true,
})
hl.window_rule({
    name = "also-gearlever-rules",
    match = {
        class = "gearlever"
    },
    -- Static effects
    float = true,
    size = { "600", "600" },
    center = true
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
