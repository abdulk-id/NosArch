-- Managed by NosArch

Name = "packages"
NamePretty = "Packages"
Cache = false
HideFromProviderlist = true
FixedOrder = true

Action = "%VALUE%"

function GetEntries()
    return {
        {
            Text = "󰐕    Install",
            Value = "walker -m menus:installing"
        },
        {
            Text = "    Update",
            Value = "nosarch-launch-tui nosarch-package update"
        },
        {
            Text = "󰭌    Remove",
            Value = "nosarch-launch-tui nosarch-package remove"
        },
        {
            Text = "󰩹    Remove unused",
            Value = "nosarch-launch-tui nosarch-package remove-unused"
        },
        {
            Text = "    Clean uninstalled package data",
            Value = "nosarch-launch-tui nosarch-package cleanup"
        },
    }
end
