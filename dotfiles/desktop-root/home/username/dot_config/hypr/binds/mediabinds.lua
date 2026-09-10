-- === MEDIA BINDS ===
-- See https://wiki.hypr.land/Configuring/Basics/Binds/

local osdclient = "swayosd-client --monitor \"$(hyprctl monitors -j | jq -r '.[] | select(.focused == true).name')\" "

-- Laptop multimedia keys for volume and LCD brightness
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd(osdclient .. "--output-volume raise"),
    { locked = true, repeating = true, description = "Volume Up" })
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd(osdclient .. "--output-volume lower"),
    { locked = true, repeating = true, description = "Volume Down" })
hl.bind("XF86AudioMute", hl.dsp.exec_cmd(osdclient .. "--output-volume mute-toggle"),
    { locked = true, repeating = true, description = "Mute Volume" })
hl.bind("XF86AudioMicMute", hl.dsp.exec_cmd(osdclient .. "--input-volume mute-toggle"),
    { locked = true, repeating = true, description = "Mute Microphone" })
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd(osdclient .. "--brightness raise"),
    { locked = true, repeating = true, description = "Brightness Up" })
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd(osdclient .. "--brightness lower"),
    { locked = true, repeating = true, description = "Brightness Down" })

-- Precise 1% multimedia adjustments with Alt modifier
hl.bind("ALT + XF86AudioRaiseVolume", hl.dsp.exec_cmd(osdclient .. "--output-volume +1"),
    { locked = true, repeating = true, description = "Volume Up Precise" })
hl.bind("ALT + XF86AudioLowerVolume", hl.dsp.exec_cmd(osdclient .. "--output-volume -1"),
    { locked = true, repeating = true, description = "Volume Down Precise" })
hl.bind("ALT + XF86MonBrightnessUp", hl.dsp.exec_cmd(osdclient .. "--brightness +1"),
    { locked = true, repeating = true, description = "Brightness Up Precise" })
hl.bind("ALT + XF86MonBrightnessDown", hl.dsp.exec_cmd(osdclient .. "--brightness -1"),
    { locked = true, repeating = true, description = "Brightness Down Precise" })

-- Requires playerctl
hl.bind("XF86AudioPlay", hl.dsp.exec_cmd(osdclient .. "--playerctl play-pause"),
    { locked = true, description = "Play" })
hl.bind("XF86AudioPause", hl.dsp.exec_cmd(osdclient .. "--playerctl play-pause"),
    { locked = true, description = "Pause" })
hl.bind("XF86AudioNext", hl.dsp.exec_cmd(osdclient .. "--playerctl next"),
    { locked = true, description = "Next track" })
hl.bind("XF86AudioPrev", hl.dsp.exec_cmd(osdclient .. "--playerctl previous"),
    { locked = true, description = "Previous track" })
