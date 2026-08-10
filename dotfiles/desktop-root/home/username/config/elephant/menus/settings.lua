Name = "settings"
NamePretty = "Settings"
--Icon = "preferences-system-symbolic"
Cache = false
HideFromProviderlist = true
FixedOrder = true

Action = "%VALUE%"

function GetEntries()
    return {
        {
            Text = "    Network",
            Value = "nosarch-launch-tui nmtui"
        },
        {
            Text = "    Bluetooth",
            Value = "nosarch-launch-tui bluetui"
        },
        {
            Text = "    Audio",
            Value = "nosarch-launch-tui wiremix"
        },
        {
            Text = "󰍹    Displays",
            Value = "nosarch-launch-tui hyprmoncfg"
        },
        {
            Text = "󱐋    Power Profiles",
            Value = "walker -m menus:power-profiles"
        },
        {
            Text = "    Toggle Notifications",
            Value = "nosarch-toggle dnd"
        },
    }
end
