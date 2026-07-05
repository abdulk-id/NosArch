#
# .bashrc for Dev module
#

# try setup
eval "$(try init ~/Codespace/Tries)"

# mise-en-place setup
eval "$(mise activate bash)"
export MISE_CARGO_HOME="$HOME/Codespace/Language-Tooling/Rust/cargo"
export MISE_RUSTUP_HOME="$HOME/Codespace/Language-Tooling/Rust/rustup"
export CARGO_HOME="$MISE_CARGO_HOME"
export RUSTUP_HOME="$MISE_RUSTUP_HOME"
export PATH="$CARGO_HOME/bin:$PATH"
