---
name: appflowy-cli
description: Use when managing AppFlowy Cloud pages, databases, or task rows through this repository's AppFlowy CLI, especially when an agent needs to discover database schemas, configure semantic task fields, list tasks, create tasks, move task statuses, or append task notes for the user.
---

# AppFlowy CLI

Use the local CLI from the repository root:

```bash
./appflowy <command>
```

Prefer `--json` for discovery and agent workflows. If authentication or workspace
configuration is missing, run `./appflowy auth`, then `./appflowy workspaces` and
ensure `APPFLOWY_WORKSPACE_ID` is set.

## Discover Schema

1. List databases:

```bash
./appflowy databases --json
```

2. Inspect fields for the target database:

```bash
./appflowy fields <database-id> --json
```

3. Configure the task profile using the user's real field names:

```bash
./appflowy task config \
  --database <database-id> \
  --title-field "<title field>" \
  --status-field "<status field>" \
  --notes-field "<notes field>" \
  --due-field "<due field>" \
  --priority-field "<priority field>"
```

Only include optional fields that exist. The profile is saved to
`.appflowy-cli.toml`; set `APPFLOWY_CLI_CONFIG` when a different profile path is
needed.

## Task Workflow

Use semantic task commands after the profile is configured:

```bash
./appflowy task list --json
./appflowy task list --status "Todo" --json
./appflowy task create "Send invoice" --status "Todo" --priority "High"
./appflowy task move "Send invoice" "In review"
./appflowy task note "Send invoice" "Checked contract and invoice draft."
```

Use row IDs when task titles are ambiguous. Use `--fuzzy` only when a unique
substring title match is acceptable.

## Pages And Raw Rows

For page notes:

```bash
./appflowy pages --json
./appflowy read "Daily"
./appflowy append "Daily" "Finished the review" --type paragraph
```

For direct database operations:

```bash
./appflowy rows <database-id> --json
./appflowy row-create <database-id> --cell "Title=Follow up"
./appflowy row-update <database-id> <row-id> --cell "Status=In review"
```

Before changing user data, inspect the current rows or page content unless the
user gave exact IDs and values.
