# AppFlowy CLI

A Python command-line client for AppFlowy Cloud pages and databases.

The CLI is designed for direct terminal use and for AI agents that need a small,
scriptable interface for managing pages, task databases, and notes.

Status: early open-source release. The CLI currently targets AppFlowy Cloud.

## Requirements

- An AppFlowy Cloud account

## Quick Start

```bash
curl -LsSf https://raw.githubusercontent.com/gthay/AppflowyCLI/main/install.sh | sh
appflowy config --email "you@example.com"
appflowy auth
appflowy workspaces
appflowy config --workspace-id "<workspace-id>"
```

The installer sets up the CLI and installs `uv` automatically if needed.

## Update Or Remove

```bash
uv tool upgrade appflowy-cli
uv tool uninstall appflowy-cli
```

## Common Commands

```bash
appflowy spaces
appflowy pages
appflowy read "Daily"
appflowy append "Daily" "Finished the review"
appflowy databases
appflowy fields <database-id>
appflowy rows <database-id>
```

Use `--json` on list/read commands when calling the CLI from an agent.

## Tasks

```bash
appflowy databases
appflowy fields <database-id>
appflowy task config \
  --database <database-id> \
  --title-field "Task" \
  --status-field "Stage" \
  --notes-field "Body"
appflowy task list --status "Todo"
appflowy task create "Send invoice" --status "Todo"
appflowy task move "Send invoice" "In review"
appflowy task note "Send invoice" "Checked the contract."
```

The task profile maps the user's real AppFlowy field names to stable CLI
commands. It is saved to `.appflowy-cli.toml`.

## Configuration

`appflowy config` saves persistent settings to
`~/.config/appflowy-cli/config.env`. Set `APPFLOWY_CONFIG_FILE` to use a
different path.

The CLI writes these local files:

- Auth token: `~/.config/appflowy-cli/token.json`
- Persistent CLI config: `~/.config/appflowy-cli/config.env`
- Task profile: `.appflowy-cli.toml`

Do not commit these files.

## Development

```bash
git clone https://github.com/gthay/AppflowyCLI.git
cd AppflowyCLI
uv sync
cp .env.example .env
./appflowy auth
./appflowy workspaces
```

Set `APPFLOWY_WORKSPACE_ID` in `.env` after listing your workspaces.

## Agent Skill

This repo ships a short agent skill in `skills/appflowy-cli/`. Agents can use it
to discover the user's AppFlowy schema, configure the task profile, and operate
on tasks through stable commands.
