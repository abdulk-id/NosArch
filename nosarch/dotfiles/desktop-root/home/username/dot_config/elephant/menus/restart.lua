-- Managed by NosArch

Name = "restart"
NamePretty = "Restart"
Cache = false
HideFromProviderlist = true
FixedOrder = true

Action = "%VALUE%"

function GetEntries()
    return {
        {
            Text = "󰤥    Wi-Fi",
            Value = "nosarch-restart wifi"
        },
        {
            Text = "    Bluetooth",
            Value = "nosarch-restart bluetooth"
        },
        {
            Text = "󱔓    Waybar",
            Value = "nosarch-restart waybar"
        },
        {
            Text = "󰖔    Hyprsunset",
            Value = "nosarch-restart hyprsunset"
        },
        {
            Text = "󰌧    Launcher",
            Value = "nosarch-restart launcher"
        }
    }
end
