#!/usr/bin/env sh
set -eu

REPO_URL="${APPFLOWY_CLI_REPO_URL:-https://github.com/gthay/AppflowyCLI.git}"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed. Installing uv with Astral's official installer..."
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- https://astral.sh/uv/install.sh | sh
  else
    echo "curl or wget is required to install uv."
    echo "Install uv manually: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
  fi

  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv was installed, but it is not available on PATH yet."
  echo "Restart your shell, then rerun this installer."
  exit 1
fi

uv tool install "git+$REPO_URL"

echo "Installed appflowy CLI."
if ! command -v appflowy >/dev/null 2>&1; then
  echo ""
  echo "appflowy is installed, but it is not on your PATH yet."
  echo "Run: uv tool update-shell"
  echo "Then restart your shell."
fi
echo ""
echo "Next steps:"
echo "  appflowy auth"
echo "  appflowy workspaces"
echo "  appflowy task config --database <db-id> --title-field <field>"
