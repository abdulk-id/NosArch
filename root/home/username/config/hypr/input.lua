-- === INPUT ===

-- https://wiki.hypr.land/Configuring/Basics/Variables/#input
hl.config({
    input = {
        kb_model = "",
        kb_layout = "us",
        kb_variant = "",
        kb_options = "",
        kb_rules = "",

        sensitivity = 0, -- -1.0 - 1.0, 0 means no modification.
        left_handed = false,

        follow_mouse = 1,

        touchpad = {
            disable_while_typing = true,
            natural_scroll = true,
        }
    },

    gestures = {
        workspace_swipe_touch = true,
    }
})

-- https://wiki.hypr.land/Configuring/Basics/Variables/#gestures
hl.gesture({
    fingers = 3,
    direction = "horizontal",
    action = "workspace"
})

-- Example per-device config
-- See https://wiki.hypr.land/Configuring/Advanced-and-Cool/Devices/ for more
-- hl.device({
--     name = "my-epic-keyboard",
--     sensitivity = -0.5
-- })
