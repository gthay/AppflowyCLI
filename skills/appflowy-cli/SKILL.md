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
  --priority-field "<priority field>" \
  --project-field "<project relation field>"
```

Only include optional fields that exist. The profile is saved to
`.appflowy-cli.toml`; set `APPFLOWY_CLI_CONFIG` when a different profile path is
needed.

## Task Workflow

Use semantic task commands after the profile is configured:

```bash
./appflowy task list --json
./appflowy task list --status "Todo" --json
./appflowy task list --status "Todo" --status "In Progress" --summary --json
./appflowy task list --exclude-status "Done" --exclude-status "Archived" --summary --json
./appflowy task create "Send invoice" --status "Todo" --priority "High"
./appflowy task create "Send invoice" --status "Todo" --summary-text "Agent-facing task context"
./appflowy task create "Send invoice" --project "Website"
./appflowy task move "Send invoice" "In review"
./appflowy task note "Send invoice" "Checked contract and invoice draft."
```

Use row IDs when task titles are ambiguous. Use `--fuzzy` only when a unique
substring title match is acceptable.

For single-select fields such as status or priority, pass the visible option
name, for example `--status "Todo"` or `--priority "High"`. The CLI maps option
names to AppFlowy option IDs before writing.

For date fields such as due dates, pass `YYYY-MM-DD` or an ISO datetime, for
example `--due "2026-05-13"` or `--cell "Deadline=2026-05-15T09:30:00+07:00"`.

Use `--summary` for compact task body context. It returns only the leading
H4 `Summary` section from each task body and stops at the next heading. Use
`--summary-heading` when a database uses another heading, and
`--summary-stop-heading` or repeated `--body-heading` when flattened AppFlowy
row text needs explicit section boundaries. Tasks without the requested leading
summary section omit the `summary` field.

Use `task create --summary-text` to initialize that Summary section for
agent-facing task details. Add `--description-text` for a following Description
section, or `--document` to provide the full row body yourself.

If the task database has a project relation field, configure it with
`--project-field`, then pass `--project "<project name or row ID>"`. The CLI
resolves project names against the relation target database.

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
./appflowy rows <database-id> --summary --json
./appflowy rows <database-id> --status-field "Status" --exclude-status "Done" --exclude-status "Archived" --summary --json
./appflowy rows <database-id> --summary --summary-heading "Brief" --summary-stop-heading "Notes" --json
./appflowy row-create <database-id> --cell "Title=Follow up"
./appflowy row-update <database-id> <row-id> --cell "Status=In review"
```

Before changing user data, inspect the current rows or page content unless the
user gave exact IDs and values.
