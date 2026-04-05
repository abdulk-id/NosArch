Name = "capture"
NamePretty = "Capture"
Icon = "applets-screenshooter-symbolic"
Cache = false
HideFromProviderlist = true
FixedOrder = true

Action = "%VALUE%"

function GetEntries()
    return {
        {
            Text = "Screenshot a region",
            Value = "hyprshot -m region",
            Icon = "edit-select-all-symbolic",
        },
        {
            Text = "Screenshot a window",
            Value = "hyprshot -m window",
            Icon = "window-maximize-symbolic",
        },
        {
            Text = "Screenshot a monitor",
            Value = "hyprshot -m output",
            Icon = "video-display-symbolic",
        },
        {
            Text = "Color picker",
            Value = "pkill hyprpicker || hyprpicker -a",
            Icon = "color-select-symbolic",
        }
    }
end
