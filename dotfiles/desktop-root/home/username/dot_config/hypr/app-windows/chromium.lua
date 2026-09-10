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
