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
