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
