Name = "share"
NamePretty = "Share"
Cache = false
HideFromProviderlist = true
FixedOrder = true
SearchName = true

Action = "%VALUE%"

local function run(cmd)
    local f = io.popen(cmd)
    if not f then return nil end
    local result = f:read("*a")
    f:close()
    return result
end

local function find_terminal()
    local terminals = {
        "xdg-terminal-exec",
        "ghostty",
        "foot",
        "kitty",
        "alacritty",
        "wezterm",
        "xterm",
    }
    for _, t in ipairs(terminals) do
        local result = run("which " .. t .. " 2>/dev/null")
        if result and result:match("%S") then
            return t
        end
    end
    return nil
end

local function pick_with_fzf(mode)
    local term = find_terminal()
    if not term then return nil end

    local outfile = os.tmpname()

    local find_cmd
    if mode == "folder" then
        find_cmd = string.format("find \"$HOME\" -type d 2>/dev/null | fzf > %q", outfile)
    else
        find_cmd = string.format("find \"$HOME\" -type f 2>/dev/null | fzf --multi > %q", outfile)
    end

    -- Launch terminal running fzf, wait for it to close
    os.execute(string.format("%s -e sh -c %q", term, find_cmd))

    local f = io.open(outfile, "r")
    if not f then return nil end
    local content = f:read("*a")
    f:close()
    os.remove(outfile)

    if not content or content == "" then return nil end
    return content
end

function share_clipboard()
    local tmp = os.tmpname() .. ".txt"
    os.execute(string.format("wl-paste > %q", tmp))
    os.execute(string.format(
        "systemd-run --user --quiet --collect localsend --headless send %q",
        tmp
    ))
end

function share_files()
    local result = pick_with_fzf("file")
    if not result then return end

    local files = {}
    for path in result:gmatch("[^\n]+") do
        if path ~= "" then
            table.insert(files, string.format("%q", path))
        end
    end

    if #files == 0 then return end

    os.execute(string.format(
        "systemd-run --user --quiet --collect localsend --headless send %s",
        table.concat(files, " ")
    ))
end

function share_folder()
    local result = pick_with_fzf("folder")
    if not result then return end

    local path = result:match("^(.-)%s*$")
    if not path or path == "" then return end

    os.execute(string.format(
        "systemd-run --user --quiet --collect localsend --headless send %q",
        path
    ))
end

function GetEntries()
    return {
        {
            Text = "Share Clipboard",
            Icon = "edit-paste-symbolic",
            Actions = { Run = "lua:share_clipboard" }
        },
        {
            Text = "Share File(s)",
            Icon = "text-x-generic-symbolic",
            Actions = { Run = "lua:share_files" }
        },
        {
            Text = "Share Folder",
            Icon = "folder-symbolic",
            Actions = { Run = "lua:share_folder" }
        }
    }
end
