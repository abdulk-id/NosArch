-- === HYPR BINDS ===
-- See https://wiki.hypr.land/Configuring/Basics/Binds/

-- === Window Binds ===
hl.bind("SUPER + W", hl.dsp.window.close(), { description = "Close window" })

hl.bind("SUPER + J", hl.dsp.layout("togglesplit"), { description = "Toggle window split" })
hl.bind("SUPER + T", hl.dsp.window.float("toggle"), { description = "Toggle window floating/tiling" })
hl.bind("SUPER + C", hl.dsp.window.center(), { description = "Center floating window" })
hl.bind("SUPER + F", hl.dsp.window.fullscreen("fullscreen", "toggle"), { description = "Toggle Full screen window" })
hl.bind("SUPER + ALT + F", hl.dsp.window.fullscreen("maximize", "toggle"), { description = "Toggle Maximize window" })
hl.bind("SUPER + P", hl.dsp.window.pseudo("toggle"), { description = "Pseudo window" })

-- Mouse binds to move (left-click) and resize (right-click) window
hl.bind("SUPER + mouse:272", hl.dsp.window.drag(), { mouse = true, description = "Move window" })
hl.bind("SUPER + mouse:273", hl.dsp.window.resize(), { mouse = true, description = "Resize window" })

-- Move focus with SUPER + arrow keys
hl.bind("SUPER + left", hl.dsp.focus({ direction = "l" }), { description = "Focus on left window" })
hl.bind("SUPER + right", hl.dsp.focus({ direction = "r" }), { description = "Focus on right window" })
hl.bind("SUPER + up", hl.dsp.focus({ direction = "u" }), { description = "Focus on top window" })
hl.bind("SUPER + down", hl.dsp.focus({ direction = "d" }), { description = "Focus on bottom window" })

-- Swap active window with the one next to it with SUPER + SHIFT + arrow keys
hl.bind("SUPER + SHIFT + left", hl.dsp.window.swap({ direction = "l" }), { description = "Swap window to the left" })
hl.bind("SUPER + SHIFT + right", hl.dsp.window.swap({ direction = "r" }), { description = "Swap window to the right" })
hl.bind("SUPER + SHIFT + up", hl.dsp.window.swap({ direction = "u" }), { description = "Swap window up" })
hl.bind("SUPER + SHIFT + down", hl.dsp.window.swap({ direction = "d" }), { description = "Swap window down" })

-- Cycle through applications on active workspace
hl.bind("ALT + TAB", function()
    hl.dsp.window.cycle_next({ next = true })
    hl.dsp.window.alter_zorder({ mode = "top" })
end, { description = "Cycle to next window" })
hl.bind("ALT + SHIFT + TAB", function()
    hl.dsp.window.cycle_next({ next = false })
    hl.dsp.window.alter_zorder({ mode = "top" })
end, { description = "Cycle to previous window" })
hl.bind("ALT + TAB", function()
    hl.dsp.window.cycle_next({ next = true, tiled = true })
    hl.dsp.window.alter_zorder({ mode = "top" })
end, { description = "Cycle to next window (Monocle)" })
hl.bind("ALT + SHIFT + TAB", function()
    hl.dsp.window.cycle_next({ next = false, tiled = true })
    hl.dsp.window.alter_zorder({ mode = "top" })
end, { description = "Cycle to previous window (Monocle)" })

-- === Workspace Binds ===

-- Switch workspaces with SUPER + [0-9]
-- Move active window to a workspace with SUPER + SHIFT + [0-9]
-- Move active window silently to a workspace with SUPER + SHIFT + ALT + [0-9]
for workspace = 1, 10 do
    local key = "code:" .. tostring(workspace + 9)
    hl.bind("SUPER + " .. key, hl.dsp.focus({ workspace = tostring(workspace) }),
        { description = "Switch to workspace " .. workspace })
    hl.bind("SUPER + SHIFT + " .. key, hl.dsp.window.move({ workspace = tostring(workspace) }),
        { description = "Move window to workspace " .. workspace })
    hl.bind("SUPER + SHIFT + ALT + " .. key, hl.dsp.window.move({ workspace = tostring(workspace), follow = false }),
        { description = "Move window silently to workspace " .. workspace })
end

-- TAB between workspaces
hl.bind("SUPER + TAB", hl.dsp.focus({ workspace = "e+1" }), { description = "Next workspace" })
hl.bind("SUPER + SHIFT + TAB", hl.dsp.focus({ workspace = "e-1" }), { description = "Previous workspace" })
hl.bind("SUPER + CTRL + TAB", hl.dsp.focus({ workspace = "previous" }), { description = "Former workspace" })

-- Move workspaces to other monitors
hl.bind("SUPER + SHIFT + ALT + LEFT", hl.dsp.workspace.move({ monitor = "l" }),
    { description = "Move workspace to left monitor" })
hl.bind("SUPER + SHIFT + ALT + RIGHT", hl.dsp.workspace.move({ monitor = "r" }),
    { description = "Move workspace to right monitor" })
hl.bind("SUPER + SHIFT + ALT + UP", hl.dsp.workspace.move({ monitor = "u" }),
    { description = "Move workspace to up monitor" })
hl.bind("SUPER + SHIFT + ALT + DOWN", hl.dsp.workspace.move({ monitor = "d" }),
    { description = "Move workspace to down monitor" })

-- Special workspace
hl.bind("SUPER + S", hl.dsp.workspace.toggle_special("scratchpad"), { description = "Toggle scratchpad workspace" })
hl.bind("SUPER + ALT + S", hl.dsp.window.move({ workspace = "special:scratchpad", follow = false }),
    { description = "Move window to scratchpad workspace" })

-- === Window Group Binds ===
hl.bind("SUPER + G", hl.dsp.group.toggle(), { description = "Toggle window grouping" })
hl.bind("SUPER + ALT + G", hl.dsp.window.move({ out_of_group = true }),
    { description = "Move active window out of group" })

hl.bind("SUPER + ALT + LEFT", hl.dsp.window.move({ into_group = "l" }), { description = "Move window to group on left" })
hl.bind("SUPER + ALT + RIGHT", hl.dsp.window.move({ into_group = "r" }),
    { description = "Move window to group on right" })
hl.bind("SUPER + ALT + UP", hl.dsp.window.move({ into_group = "u" }), { description = "Move window to group on top" })
hl.bind("SUPER + ALT + DOWN", hl.dsp.window.move({ into_group = "d" }),
    { description = "Move window to group on bottom" })

hl.bind("SUPER + ALT + TAB", hl.dsp.group.next(), { description = "Next window in group" })
hl.bind("SUPER + ALT + SHIFT + TAB", hl.dsp.group.prev(), { description = "Previous window in group" })

hl.bind("SUPER + CTRL + LEFT", hl.dsp.group.prev(), { description = "Move grouped window focus left" })
hl.bind("SUPER + CTRL + RIGHT", hl.dsp.group.next(), { description = "Move grouped window focus right" })

for index = 1, 5 do
    hl.bind("SUPER + ALT + code:" .. tostring(index + 9), hl.dsp.group.active({ index = index }),
        { description = "Switch to group window " .. tostring(index) })
end
