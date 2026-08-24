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
