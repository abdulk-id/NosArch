-- Managed by NosArch

Name = "power-profiles"
NamePretty = "Power profiles"
Cache = false
HideFromProviderlist = true
FixedOrder = true

Action = "powerprofilesctl set %VALUE%; notify-send 'Power Profile' 'Set to %VALUE%'"

function GetEntries()
    local entries = {}
    local handle = io.popen("powerprofilesctl")

    if not handle then
        return entries
    end

    for line in handle:lines() do
        local profile_name = line:match("^[* ] ([%a-]+):")

        if profile_name then
            local is_current = line:match("^%*")
            local display_name = profile_name:gsub("^%l", string.upper):gsub("-", " ")

            if is_current then
                display_name = "✓ " .. display_name
            end

            table.insert(entries, {
                Text = display_name,
                Value = profile_name,
                state = is_current and { "current" } or nil,
            })
        end
    end

    handle:close()

    return entries
end
