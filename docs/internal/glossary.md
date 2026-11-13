# Glossary

- **Target system**: The Arch Linux system NosArch applies changes to.
- **Dotfile**: Any file NosArch applies to the target system. See [dotfiles.md](dotfiles.md).
- **Definition code**: What NosArch applies, and the hooks around applying it.
- **Engine**: What reads the definition and applies it on the target system.
- **Apply**: Make the target system match the definition (`mise apply`). A dry run reports what an apply would do.
- **decman**: The declarative Arch configuration tool the engine descends from. See
  [engine.md](engine.md#where-it-differs-from-decman-on-purpose).
