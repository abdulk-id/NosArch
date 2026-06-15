-- === LOOK AND FEEL ===
-- Refer to https://wiki.hypr.land/Configuring/Basics/Variables/

-- local active_border_color = { colors = { "rgba(33ccffee)", "rgba(00ff99ee)" }, angle = 45 }
local active_border_color = "rgb(%ACCENT%)"
local inactive_border_color = "rgba(595959aa)"

hl.config({
    -- https://wiki.hypr.land/Configuring/Basics/Variables/#general
    general = {
        border_size = 2,
        gaps_in = 5,
        gaps_out = 5,

        col = {
            active_border = active_border_color,
            inactive_border = inactive_border_color,
        },

        layout = "dwindle",

        resize_on_border = true,

        -- Please see https://wiki.hypr.land/Configuring/Tearing/ before you turn this on
        allow_tearing = false,
    },

    -- https://wiki.hypr.land/Configuring/Basics/Variables/#decoration
    decoration = {
        rounding = 10,
        rounding_power = 2,

        active_opacity = 1,
        inactive_opacity = 0.95,

        dim_modal = true,
        border_part_of_window = false,

        blur = {
            enabled = true,

            size = 2,
            passes = 2,

            new_optimizations = true,

            -- TODO: noise
            contrast = 0.75,
            brightness = 0.60,

            special = true,
        },

        shadow = {
            enabled = true,
            range = 2,
            render_power = 3,
            color = "rgba(1a1a1aee)"
        }
    },

    -- https://wiki.hypr.land/Configuring/Basics/Variables/#animations
    animations = {
        enabled = true, -- yes, please :)

        -- TODO: Learn Spring animations

        -- Curves
        hl.curve("easeOutQuint", { type = "bezier", points = { { 0.23, 1 }, { 0.32, 1 } } }),
        hl.curve("easeInOutCubic", { type = "bezier", points = { { 0.65, 0.05 }, { 0.36, 1 } } }),
        hl.curve("linear", { type = "bezier", points = { { 0, 0 }, { 1, 1 } } }),
        hl.curve("almostLinear", { type = "bezier", points = { { 0.5, 0.5 }, { 0.75, 1 } } }),
        hl.curve("quick", { type = "bezier", points = { { 0.15, 0 }, { 0.1, 1 } } }),

        hl.curve("md3_decel", { type = "bezier", points = { { 0.05, 0.7 }, { 0.1, 1 } } }),

        -- Animations
        hl.animation({ leaf = "global", enabled = true, speed = 10, bezier = "default" }),
        hl.animation({ leaf = "border", enabled = true, speed = 5.39, bezier = "easeOutQuint" }),
        hl.animation({ leaf = "windows", enabled = true, speed = 3, bezier = "easeOutQuint" }),
        hl.animation({ leaf = "windowsIn", enabled = true, speed = 4.1, bezier = "easeOutQuint", style = "popin 87%" }),
        hl.animation({ leaf = "windowsOut", enabled = true, speed = 1.49, bezier = "linear", style = "popin 87%" }),
        hl.animation({ leaf = "fade", enabled = true, speed = 3.03, bezier = "quick" }),
        hl.animation({ leaf = "fadeIn", enabled = true, speed = 1.73, bezier = "almostLinear" }),
        hl.animation({ leaf = "fadeOut", enabled = true, speed = 1.46, bezier = "almostLinear" }),
        hl.animation({ leaf = "layers", enabled = true, speed = 3.81, bezier = "easeOutQuint" }),
        hl.animation({ leaf = "layersIn", enabled = true, speed = 4, bezier = "easeOutQuint", style = "fade" }),
        hl.animation({ leaf = "layersOut", enabled = true, speed = 1.5, bezier = "linear", style = "fade" }),
        hl.animation({ leaf = "fadeLayersIn", enabled = true, speed = 1.79, bezier = "almostLinear" }),
        hl.animation({ leaf = "fadeLayersOut", enabled = true, speed = 1.39, bezier = "almostLinear" }),

        hl.animation({ leaf = "workspaces", enabled = true, speed = 2, bezier = "md3_decel", style = "slide" }),
    },

    -- https://wiki.hypr.land/Configuring/Basics/Variables/#group
    group = {
        col = {
            border_active = active_border_color,
            border_inactive = inactive_border_color,
            --border_locked_active = -1,
            --border_locked_inactive = -1,
        },

        groupbar = {
            enabled = true,

            font_family = "JetbrainsMono Nerd Font",
            font_size = 12,
            font_weight_active = "ultraheavy",
            font_weight_inactive = "normal",

            height = 20,
            indicator_gap = 5,
            indicator_height = 2, -- 0
            gaps_in = 5,
            gaps_out = 0,

            scrolling = false,

            gradients = true,
            gradient_rounding = 0,
            gradient_round_only_edges = false,

            text_color = "rgb(ffffff)",
            text_color_inactive = "rgba(ffffff90)",

            col = {
                active = "rgba(00000040)",
                inactive = "rgba(00000020)",
            },

            middle_click_close = false
        }
    },

    -- Layouts (https://wiki.hypr.land/Configuring/Layouts/)
    dwindle = {
        force_split = 2,       -- Always split on the right
        preserve_split = true, -- You probably want this
    },
    master = {
        new_status = "master",
    },
    scrolling = {
        column_width = 0.49,
    },

    -- https://wiki.hypr.land/Configuring/Basics/Variables/#cursor
    cursor = {
        enable_hyprcursor = true,
        hide_on_key_press = true,
    },

    -- https://wiki.hypr.land/Configuring/Basics/Variables/#misc
    misc = {
        disable_hyprland_logo = true,    -- If true disables the random hyprland logo / anime girl background. :(
        disable_splash_rendering = true, -- If true disables the Hyprland splash rendering.
        font_family = "JetbrainsMono Nerd Font",
        force_default_wallpaper = 1,     -- Set to 0 or 1 to disable the anime mascot wallpapers

        focus_on_activate = true,
        on_focus_under_fullscreen = 1,

        enable_anr_dialog = true,
        anr_missed_pings = 3
    }
})

-- Style Gum confirm to match terminal theme
hl.env("GUM_CONFIRM_PROMPT_FOREGROUND", 6)
hl.env("GUM_CONFIRM_SELECTED_FOREGROUND", 0)
hl.env("GUM_CONFIRM_SELECTED_BACKGROUND", 2)
hl.env("GUM_CONFIRM_UNSELECTED_FOREGROUND", 0)
hl.env("GUM_CONFIRM_UNSELECTED_BACKGROUND", 8)
