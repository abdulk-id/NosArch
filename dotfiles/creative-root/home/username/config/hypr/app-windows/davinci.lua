hl.window_rule({
    name = "davinci-resolve-rules",
    match = {
        class = ".*[Rr]esolve.*",
        float = true,
    },
    -- Dynamic effects
    stay_focused = true, -- Focus floating DaVinci Resolve dialog windows
})
