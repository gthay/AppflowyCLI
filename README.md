# AppFlowy CLI

A Python command-line client for AppFlowy Cloud pages and databases.

The CLI is designed for direct terminal use and for AI agents that need a small,
scriptable interface for managing pages, task databases, and notes.

Status: early open-source release. The CLI currently targets AppFlowy Cloud.

## Requirements

- Python 3.10+
- `uv`
- An AppFlowy Cloud account

## Install

Install globally with `uv`:

```bash
uv tool install git+https://github.com/gthay/AppflowyCLI.git
```

Or use the install script:

```bash
curl -LsSf https://raw.githubusercontent.com/gthay/AppflowyCLI/main/install.sh | sh
```

The install script requires `uv`. Install `uv` first if needed:
https://docs.astral.sh/uv/getting-started/installation/

Update later with:

```bash
uv tool upgrade appflowy-cli
```

Uninstall with:

```bash
uv tool uninstall appflowy-cli
```

## First Run

Set your email, authenticate, and choose a workspace:

```bash
appflowy config --email "you@example.com"
appflowy auth
appflowy workspaces
appflowy config --workspace-id "<workspace-id>"
```

`appflowy config` saves persistent settings to
`~/.config/appflowy-cli/config.env` by default. Set `APPFLOWY_CONFIG_FILE` to use
a different path.

You can also use a local `.env` file in the directory where you run the CLI:

```bash
APPFLOWY_BASE_URL=https://beta.appflowy.cloud
APPFLOWY_EMAIL=you@example.com
APPFLOWY_WORKSPACE_ID=<workspace-id>
```

## Local Development

```bash
git clone https://github.com/gthay/AppflowyCLI.git
cd AppflowyCLI
uv sync
cp .env.example .env
./appflowy auth
./appflowy workspaces
```

Set `APPFLOWY_WORKSPACE_ID` in `.env` after listing your workspaces.

## Common Commands

```bash
appflowy spaces
appflowy pages
appflowy read "Daily"
appflowy append "Daily" "Finished the review"
appflowy databases
appflowy fields <database-id>
appflowy rows <database-id>
appflowy row-create <database-id> --cell "Title=Follow up"
appflowy row-update <database-id> <row-id> --cell "Status=In review"
```

Use `--json` on list/read commands when calling the CLI from an agent.

## Task Profile

Agents can configure a semantic task profile once, then use task commands without
hardcoding each user's field names.

```bash
appflowy task config \
  --database <database-id> \
  --title-field "Task" \
  --status-field "Stage" \
  --notes-field "Body" \
  --due-field "Deadline" \
  --priority-field "Importance"
```

After that, agents can work with stable task commands:

```bash
appflowy task list --status "Todo" --json
appflowy task create "Send invoice" --status "Todo" --priority "High"
appflowy task move "Send invoice" "In review"
appflowy task note "Send invoice" "Checked the contract."
```

The profile is saved to `.appflowy-cli.toml`. Set `APPFLOWY_CLI_CONFIG` to use a
different config path.

## Agent Skill

This repo ships a short agent skill in `skills/appflowy-cli/`. Agents can use it
to discover the user's AppFlowy schema, configure the task profile, and operate
on tasks through stable commands.

## Files Written Locally

- Auth token: `~/.config/appflowy-cli/token.json`
- Persistent CLI config: `~/.config/appflowy-cli/config.env`
- Task profile: `.appflowy-cli.toml` in the current directory unless
  `APPFLOWY_CLI_CONFIG` is set

These files may contain account-specific values and should not be committed.
