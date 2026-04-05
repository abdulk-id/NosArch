Name = "settings"
NamePretty = "Settings"
Icon = "preferences-system-symbolic"
Cache = false
HideFromProviderlist = true
FixedOrder = true

Action = "%VALUE%"

function GetEntries()
    return {
        {
            Text = "Audio",
            Value = "nosarch-launch-tui wiremix",
            Icon = "audio-volume-high-symbolic",
            Weight = 10
        },
        {
            Text = "WiFi",
            Value = "nosarch-launch-tui nmtui",
            Icon = "network-wireless-symbolic",
            Weight = 9
        },
        {
            Text = "Bluetooth",
            Value = "nosarch-launch-tui bluetui",
            Icon = "bluetooth-symbolic",
            Weight = 8
        },
        {
            Text = "Power Profiles",
            Value = "walker -m menus:power-profiles",
            Icon = "gnome-power-manager-symbolic",
            Weight = 7
        },
        {
            Text = "Displays",
            Value = "nosarch-launch-tui hyprdynamicmonitors tui",
            Icon = "preferences-desktop-display-symbolic",
            Weight = 6
        }
    }
end
