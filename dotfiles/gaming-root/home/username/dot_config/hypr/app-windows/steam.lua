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
