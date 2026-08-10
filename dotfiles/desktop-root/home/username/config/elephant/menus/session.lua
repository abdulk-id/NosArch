Name = "session"
NamePretty = "session"
--Icon = "system-shutdown-symbolic"
Cache = false
HideFromProviderlist = true
FixedOrder = true

Action = "%VALUE%"

function GetEntries()
    return {
        {
            Text = "󱫖    Toggle Idling",
            Value = "nosarch-session idle-lock toggle"
        },
        {
            Text = "    Lock",
            Value = "nosarch-session lock"
        },
        {
            Text = "󰒲    Suspend",
            Value = "systemctl suspend"
        },
        {
            Text = "󰍃    Log Out",
            Value = "nosarch-session logout"
        },
        {
            Text = "󰜉    Restart",
            Value = "nosarch-session restart"
        },
        {
            Text = "󰐥    Shutdown",
            Value = "nosarch-session shutdown"
        }
    }
end
