-- Managed by NosArch

hl.window_rule({
    name = "davinci-resolve-rules",
    match = {
        class = ".*[Rr]esolve.*",
    },
    -- Dynamic effects
    no_follow_mouse = true,                -- Prevent modal dialog pointer warps when focus follows the mouse.
    opacity = "1.0 override 1.0 override", -- translucency distorts colour-critical grading work.
    stay_focused = true,                   -- Focus floating DaVinci Resolve dialog windows
})
hl.window_rule({
    match = {
        class = ".*[Rr]esolve.*",
        title = "^DaVinci Resolve( Studio)? - .+$",
    },
    -- Static effects
    fullscreen = true
})

-- Resolve exposes the Voiceover panel under the generic "Dialog" title.
hl.window_rule({
    match = {
        class = ".*[Rr]esolve.*",
        title = "^(DaVinci Resolve( Studio)? - .+|Project Manager|Preferences|Find Directory|Dialog)$",
    },
    -- Dynamic effects
    stay_focused = false
})
