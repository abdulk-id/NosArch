hl.window_rule({
    name = "spotify-rules",
    match = {
        initial_class = "Spotify"
    },
    -- Static effects
    float = true,
    size = { "1280", "720" },
    center = true,

    -- Dynamic effects
    tag = "+spotify-player",
})

hl.on("window.open", function(window)
    -- Find the Spotify main window by its dynamic tag.
    local spotify = nil

    for _, client in pairs(hl.get_windows()) do
        for _, tag in ipairs(client.tags) do
            if tag == "spotify-player*" then
                spotify = client
                break
            end
        end
    end

    if spotify == nil then
        return
    end

    -- The miniplayer is created by the same process as the main Spotify window.
    if window.pid == spotify.pid
        and window.class == "Chromium-browser"
    then
        hl.dispatch(hl.dsp.window.float({
            window = window,
            action = "set",
        }))

        hl.dispatch(hl.dsp.window.resize({
            window = window,
            x = 308,
            y = 304,
        }))

        hl.dispatch(hl.dsp.window.move({
            window = window,
            x = window.monitor.width - 308 - 25,
            y = window.monitor.height - 304 - 50,
        }))

        hl.dispatch(hl.dsp.window.pin({
            window = window,
            action = "set",
        }))
    end
end)
