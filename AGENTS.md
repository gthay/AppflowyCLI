# Agent Instructions

This repository builds `appflowy`, a Python CLI for AppFlowy Cloud pages and
databases. The CLI is intended for direct terminal use and for AI agents that
manage the user's AppFlowy tasks, notes, and database rows.

## Development

- Use `uv` for dependency management and commands.
- Run tests with `uv run pytest`.
- Keep commands scriptable and add `--json` output for agent-facing reads.
- Prefer small, explicit CLI commands over interactive flows.
- Do not commit local credentials, token files, `.env`, or task profile files.

## Architecture

- `src/appflowy_cli/cli.py`: argparse command surface and output formatting.
- `src/appflowy_cli/client.py`: AppFlowy Cloud API calls, auth, token/config persistence.
- `src/appflowy_cli/yjs_decoder.py`: AppFlowy document decoding helpers.
- `skills/appflowy-cli/`: short agent skill for using this CLI.

## Product Direction

The CLI should support two main workflows:

- General AppFlowy CLI usage: auth, workspaces, pages, databases, rows.
- Agent task management: discover schema, configure semantic task fields, list
  tasks, create tasks, move statuses, and append notes without hardcoded field
  names.

When adding features, preserve the low-level database commands and build
agent-friendly conveniences on top of them.
