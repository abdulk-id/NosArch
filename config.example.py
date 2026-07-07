CONFIG: dict[str, str] = {
    "%USER%": "your username",
    "%FULLNAME%": "your full name",
    "%GIT_EMAIL%": "your git email",
    "%FULL_SETUP%": "false",  # Enable to install the full setup
    "%CREATIVE_PROFILE%": "false",  # Enable to setup NosArch for creative work
    "%DEV_PROFILE%": "false",  # Enable to setup NosArch for development
    "%GAMING_PROFILE%": "false",  # Enable to setup NosArch for gaming
}


# Enable the languages you want to use
DEV_LANGS_ENABLED: dict[str, bool] = {
    "bunjs": False,
    "denojs": False,
    "go": False,
    "java_maven": False,
    "java_gradle": False,
    ".net": False,
    "nodejs": False,
    "python": False,
    "rust": False,
    "zig": False,
}
