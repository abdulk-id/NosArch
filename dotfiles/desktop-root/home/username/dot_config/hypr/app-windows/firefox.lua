-- Managed by NosArch

hl.window_rule({
    name = "firefox-based-browser-rules",
    match = {
        class = "([fF]irefox|[zZ]en|[lL]ibrewolf)"
    },
    -- Dynamic effects
    opacity = "1.0 override 0.97 override"
})

-- Firefox-based browser extension windows
hl.on("window.open", function(w)
    if w.class ~= "firefox" then return end
    if w.initial_title ~= "Mozilla Firefox" then return end

    local ff_windows = hl.get_windows({ class = "firefox" })
    if #ff_windows <= 1 then return end

    hl.dispatch(hl.dsp.window.float({ action = "set", window = w }))

    local sub
    sub = hl.on("window.title", function(tw)
        if tw.address ~= w.address then return end
        if tw.title == ""
            or tw.title == "Mozilla Firefox"
            or tw.title == "about:blank"
            or tw.title:match("^about:.*Mozilla Firefox$") then
            return
        end

        sub:remove()

        if tw.title:match("^Extension:") then
            hl.dispatch(hl.dsp.window.resize({ x = 800, y = 600, window = tw }))
            hl.dispatch(hl.dsp.window.center({ window = tw }))
            hl.dispatch(hl.dsp.focus({ window = tw }))
        else
            hl.dispatch(hl.dsp.window.float({ action = "unset", window = tw }))
        end
    end)
end)

--[[
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
]]
