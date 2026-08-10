-- === MEDIA BINDS ===
-- See https://wiki.hypr.land/Configuring/Basics/Binds/

-- Laptop multimedia keys for volume and display brightness
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("nosarch-volume output increase"),
    { locked = true, repeating = true, description = "Volume Up" })
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("nosarch-volume output decrease"),
    { locked = true, repeating = true, description = "Volume Down" })
hl.bind("XF86AudioMute", hl.dsp.exec_cmd("nosarch-volume output mute toggle"),
    { locked = true, repeating = true, description = "Mute Volume" })
hl.bind("XF86AudioMicMute", hl.dsp.exec_cmd("nosarch-volume input mute toggle"),
    { locked = true, repeating = true, description = "Mute Microphone" })
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd("nosarch-display brightness increase"),
    { locked = true, repeating = true, description = "Brightness Up" })
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("nosarch-display brightness decrease"),
    { locked = true, repeating = true, description = "Brightness Down" })

-- Precise 1% multimedia adjustments with Alt modifier
hl.bind("ALT + XF86AudioRaiseVolume", hl.dsp.exec_cmd("nosarch-volume output increase 1"),
    { locked = true, repeating = true, description = "Volume Up Precise" })
hl.bind("ALT + XF86AudioLowerVolume", hl.dsp.exec_cmd("nosarch-volume output decrease 1"),
    { locked = true, repeating = true, description = "Volume Down Precise" })
hl.bind("ALT + XF86MonBrightnessUp", hl.dsp.exec_cmd("nosarch-display brightness increase 1"),
    { locked = true, repeating = true, description = "Brightness Up Precise" })
hl.bind("ALT + XF86MonBrightnessDown", hl.dsp.exec_cmd("nosarch-display brightness decrease 1"),
    { locked = true, repeating = true, description = "Brightness Down Precise" })

-- Media playback keys
hl.bind("XF86AudioPlay", hl.dsp.exec_cmd("nosarch-media play-pause"),
    { locked = true, description = "Play" })
hl.bind("XF86AudioPause", hl.dsp.exec_cmd("nosarch-media play-pause"),
    { locked = true, description = "Pause" })
hl.bind("XF86AudioNext", hl.dsp.exec_cmd("nosarch-media next"),
    { locked = true, description = "Next track" })
hl.bind("XF86AudioPrev", hl.dsp.exec_cmd("nosarch-media previous"),
    { locked = true, description = "Previous track" })
