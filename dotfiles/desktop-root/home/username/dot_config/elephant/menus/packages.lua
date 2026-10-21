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
            Text = "󰐕    Install package",
            Value = "walker -m menus:installing"
        },
        {
            Text = "    Update packages",
            Value = "nosarch-launch-tui nosarch-package update"
        },
        {
            Text = "󰭌    Remove package",
            Value = "nosarch-launch-tui nosarch-package remove"
        },
        {
            Text = "󰩹    Remove unused packages",
            Value = "nosarch-launch-tui nosarch-package remove-unused"
        },
        {
            Text = "    Clean uninstalled package data",
            Value = "nosarch-launch-tui nosarch-package cleanup"
        },
    }
end
