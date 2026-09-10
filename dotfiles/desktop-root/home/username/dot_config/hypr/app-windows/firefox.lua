hl.window_rule({
    name = "firefox-based-browser-rules",
    match = {
        class = "([fF]irefox|[zZ]en|[lL]ibrewolf)"
    },
    -- Dynamic effects
    opacity = "1.0 override 0.97 override"
})

-- Firefox-based browser extension windows
hl.on("window.title", function(w)
    if w == nil then
        return
    end

    if (
            w.class:match("^[Ff]irefox$")
            or w.class:match("^[Zz]en$")
            or w.class:match("^[Ll]ibrewolf$")
        ) then
        if w.title:match("^Extension: ") then
            hl.dispatch(
                hl.dsp.window.float({
                    action = "enable",
                    window = w,
                })
            )

            hl.dispatch(
                hl.dsp.window.resize({
                    x = 338,
                    y = 600,
                    relative = false,
                    window = w,
                })
            )

            hl.dispatch(
                hl.dsp.window.center({
                    window = w,
                })
            )
        end
    end
end)
