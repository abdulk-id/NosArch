Name = "main"
NamePretty = "Main Menu"
Icon = "view-grid-symbolic"
Cache = false
HideFromProviderlist = true
FixedOrder = true
SearchName = true

Action = "%VALUE%"

function GetEntries()
    return {
        {
            Text = "Applications",
            Value = "walker -m desktopapplications",
            Icon = "view-app-grid-symbolic"
        },
        {
            Text = "Learn Keybinds",
            Value = "walker -m menus:keybinds",
            Icon = "preferences-desktop-keyboard-symbolic"
        },
        {
            Text = "Capture",
            Value = "walker -m menus:capture",
            Icon = "applets-screenshooter-symbolic"
        },
        {
            Text = "Share",
            Value = "walker -m menus:share",
            Icon = "send-to-symbolic"
        },
        {
            Text = "Manage Software",
            Value = "walker -m menus:software",
            Icon = "system-software-install-symbolic"
        },
        {
            Text = "Settings",
            Value = "walker -m menus:settings",
            Icon = "preferences-system-symbolic"
        },
        {
            Text = "Session",
            Value = "walker -m menus:session",
            Icon = "system-shutdown-symbolic"
        }
    }
end
