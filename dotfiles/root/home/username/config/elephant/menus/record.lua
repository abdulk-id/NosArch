Name = "record"
NamePretty = "Record"
--Icon = "applets-screenshooter-symbolic"
Cache = false
HideFromProviderlist = true
FixedOrder = true

Action = "%VALUE%"

function GetEntries()
    return {
        {
            Text = "    Record screen",
            Value = "sleep 0.2s; nosarch-record start --record-output"
        },
        {
            Text = "    Record Screen with Camera and Mic",
            Value = "sleep 0.2s; nosarch-record start --record-output --record-input --show-webcam"
        },
        {
            Text = "    Stop Recording",
            Value = "nosarch-record stop"
        }
    }
end
