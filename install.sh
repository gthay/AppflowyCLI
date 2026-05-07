#!/usr/bin/env sh
set -eu

REPO_URL="${APPFLOWY_CLI_REPO_URL:-https://github.com/gthay/AppflowyCLI.git}"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required to install appflowy-cli."
  echo "Install uv first: https://docs.astral.sh/uv/getting-started/installation/"
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
