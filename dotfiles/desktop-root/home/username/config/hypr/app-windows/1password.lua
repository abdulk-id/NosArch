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
