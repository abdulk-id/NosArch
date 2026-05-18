Name = "session"
NamePretty = "session"
Icon = "system-shutdown-symbolic"
Cache = false
HideFromProviderlist = true
FixedOrder = true

Action = "%VALUE%"

function GetEntries()
    return {
        {
            Text = "Toggle Idling",
            Value = "nosarch-toggle-idling",
            Icon = "emoji-objects-symbolic",
            Weight = 10
        },
        {
            Text = "Lock",
            Value = "loginctl lock-session",
            Icon = "system-lock-screen-symbolic",
            Weight = 9
        },
        {
            Text = "Suspend",
            Value = "systemctl suspend",
            Icon = "media-playback-pause-symbolic",
            Weight = 8
        },
        {
            Text = "Hibernate",
            Value = "systemctl hibernate",
            Icon = "media-playback-stop-symbolic",
            Weight = 7
        },
        {
            Text = "Restart",
            Value = "hyprshutdown -t 'Restarting...' --post-cmd 'systemctl reboot'",
            Icon = "system-reboot-symbolic",
            Weight = 6
        },
        {
            Text = "Shutdown",
            Value = "hyprshutdown -t 'Shutting down...' --post-cmd 'systemctl poweroff'",
            Icon = "system-shutdown-symbolic",
            Weight = 5
        }
    }
end
