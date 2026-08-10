Name = "capture"
NamePretty = "Capture"
--Icon = "applets-screenshooter-symbolic"
Cache = false
HideFromProviderlist = true
FixedOrder = true

Action = "%VALUE%"

function GetEntries()
    return {
        {
            Text = "    Screenshot a region",
            Value = "sleep 0.2s; nosarch-capture screenshot region"
        },
        {
            Text = "    Screenshot a window",
            Value = "sleep 0.2s; nosarch-capture screenshot window"
        },
        {
            Text = "󰹑    Screenshot a monitor",
            Value = "sleep 0.2s; nosarch-capture screenshot monitor"
        },
        {
            Text = "    Record",
            Value = "walker -m menus:record"
        },
        {
            Text = "󰴑    Extract text from screen",
            Value = "sleep 0.2s; nosarch-capture extract-text"
        },
        {
            Text = "󰃉    Color picker",
            Value = "sleep 0.2s; nosarch-capture colorpick"
        }
    }
end
