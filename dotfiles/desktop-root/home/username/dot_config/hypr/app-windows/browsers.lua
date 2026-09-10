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
    size = { "384", "216" },
    move = { "(monitor_w - window_w - 25)", "(monitor_h - window_h - 50)" }, -- Move to bottom-right corner of screen
    pin = true,
    content = "video",

    -- Dynamic effects
    border_size = 3,
    opacity = "1.0 override 1.0 override",
    keep_aspect_ratio = true,
})

-- Google Meet Picture-in-picture window overlays
hl.window_rule({
    name = "google-meet-pip-rules",
    match = {
        title = "^Meet - .+"
    },
    -- Static effects
    float = true,
    size = { "600", "338" },
    move = { "(monitor_w - window_w - 40)", "(monitor_h - window_h - 40)" }, -- Move to bottom-right corner of screen
    pin = true,
    content = "video",

    -- Dynamic effects
    border_size = 2,
    opacity = "1.0 override 1.0 override",
    keep_aspect_ratio = true,
})
