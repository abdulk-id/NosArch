-- === WINDOWS AND WORKSPACES ===
-- See https://wiki.hypr.land/Configuring/Window-Rules/ for more
-- See https://wiki.hypr.land/Configuring/Workspace-Rules/ for workspace rules

hl.config({
    -- Miscellaneous config related to windows
    misc = {
        focus_on_activate = true,
        on_focus_under_fullscreen = 1,

        enable_anr_dialog = true,
        anr_missed_pings = 3,

        -- Solve issue of windows opening in workspace 1 when called from other workspaces
        initial_workspace_tracking = 0
    }
})

-- Ignore maximize requests from all apps.
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
    center = true
})

-- App-specific tweaks
require("./app-windows/*")
