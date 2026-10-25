-- Managed by NosArch

Name = "help"
NamePretty = "Help"
Cache = false
HideFromProviderlist = true
FixedOrder = true

Action = "%VALUE%"

function GetEntries()
    return {
        {
            Text = "󰜉    Restart service",
            Value = "walker -m menus:restart"
        }
    }
end
