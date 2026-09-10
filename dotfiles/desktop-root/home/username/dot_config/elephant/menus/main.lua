Name = "main"
NamePretty = "Main Menu"
--Icon = "view-grid-symbolic"
Cache = false
HideFromProviderlist = true
FixedOrder = true
SearchName = true

Action = "%VALUE%"

function GetEntries()
    return {
        {
            Text = "󰀻    Applications",
            Value = "walker -m desktopapplications"
        },
        {
            Text = "    Capture",
            Value = "walker -m menus:capture"
        },
        {
            Text = "    Share",
            Value = "walker -m menus:share"
        },
        {
            Text = "    Packages",
            Value = "walker -m menus:packages"
        },
        {
            Text = "    Settings",
            Value = "walker -m menus:settings"
        },
        {
            Text = "    Session",
            Value = "walker -m menus:session"
        }
    }
end
