#!/usr/bin/env python3
"""AppFlowy CLI — read and write pages, query databases.

Usage:
    appflowy auth                              Authenticate via magic link
    appflowy config --email EMAIL             Save persistent CLI settings
    appflowy workspaces                        List all workspaces
    appflowy spaces                            List spaces in current workspace
    appflowy pages [--space NAME]              List pages
    appflowy read <name-or-id> [--json]        Read a page (markdown or JSON)
    appflowy append <name-or-id> <text>        Append text to a page
    appflowy databases                         List databases
    appflowy fields <database-id>              Show database fields
    appflowy rows <database-id> [--updated]    Show database rows
    appflowy row-create <db-id> --cell K=V     Create a row
    appflowy row-update <db-id> <row> --cell   Update a row
    appflowy task config --database ID --title-field NAME
    appflowy task list [--status STATUS]
    appflowy task create <title>
    appflowy task move <task> <status>
    appflowy task note <task> <note>
"""
import argparse
import sys
import json
import os
from pathlib import Path
from dotenv import dotenv_values
from . import client as af

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

CONFIG_FILE = os.getenv("APPFLOWY_CLI_CONFIG", ".appflowy-cli.toml")
TASK_FIELD_KEYS = {
    "title": "title_field",
    "status": "status_field",
    "notes": "notes_field",
    "due": "due_field",
    "priority": "priority_field",
}
ENV_CONFIG_KEYS = (
    "APPFLOWY_BASE_URL",
    "APPFLOWY_EMAIL",
    "APPFLOWY_WORKSPACE_ID",
    "APPFLOWY_REQUEST_TIMEOUT",
)


def print_json(data):
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def get_ws():
    ws = af.WORKSPACE_ID
    if not ws:
        print("Set APPFLOWY_WORKSPACE_ID in .env or use 'appflowy workspaces' to find it.")
        sys.exit(1)
    return ws


def _config_path():
    return Path(CONFIG_FILE).expanduser()


def _load_config():
    path = _config_path()
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def _toml_string(value):
    return json.dumps(value)


def _save_task_profile(profile):
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["[tasks]"]
    for key in ("database", "title_field", "status_field", "notes_field", "due_field", "priority_field"):
        value = profile.get(key)
        if value:
            lines.append(f"{key} = {_toml_string(value)}")
    path.write_text("\n".join(lines) + "\n")


def _env_config_path():
    return af.config_path()


def _load_env_config():
    path = _env_config_path()
    if not path.exists():
        return {}
    return {k: v for k, v in dotenv_values(path).items() if v is not None}


def _save_env_config(config):
    path = _env_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for key in ENV_CONFIG_KEYS:
        value = config.get(key)
        if value:
            lines.append(f"{key}={json.dumps(value)}")
    path.write_text("\n".join(lines) + "\n")


def _task_profile():
    profile = _load_config().get("tasks", {})
    if not profile.get("database"):
        raise af.AppFlowyError("No task database configured. Run: appflowy task config --database <db-id> --title-field <field>")
    if not profile.get("title_field"):
        raise af.AppFlowyError("No task title field configured. Run: appflowy task config --title-field <field>")
    return profile


def _task_field(profile, semantic, required=False):
    field = profile.get(TASK_FIELD_KEYS[semantic])
    if required and not field:
        raise af.AppFlowyError(f"No task {semantic} field configured.")
    return field


def _task_cells_from_args(args, profile, include_empty=False):
    cells = {}
    for semantic in ("title", "status", "notes", "due", "priority"):
        value = getattr(args, semantic, None)
        field = _task_field(profile, semantic)
        if field and (include_empty or value not in (None, "")):
            cells[field] = value
    return cells


def _cell_text(row, field):
    value = row.get("cells", {}).get(field)
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def _row_id(row):
    return row.get("id") or row.get("row_id")


def _find_task_row(rows, title, title_field, allow_fuzzy=False):
    q = title.casefold()
    exact = [r for r in rows if _cell_text(r, title_field).casefold() == q]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise af.AppFlowyError(f"Task title '{title}' is ambiguous; use a row ID.")
    if not allow_fuzzy:
        by_id = [r for r in rows if _row_id(r) == title]
        return by_id[0] if by_id else None
    matches = [r for r in rows if q in _cell_text(r, title_field).casefold()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise af.AppFlowyError(f"Task query '{title}' is ambiguous; use a more specific title or row ID.")
    by_id = [r for r in rows if _row_id(r) == title]
    return by_id[0] if by_id else None


# ── Auth ──────────────────────────────────────────────────────────────

def cmd_auth(args):
    email = af.request_magic_link()
    print(f"Magic link sent to {email}.")
    print("Right-click the link in the email and copy it (don't click it).\n")
    link = input("Paste link here: ").strip()
    access_token, refresh_token = af.exchange_magic_link(link)
    af.save_token(access_token, refresh_token)
    print("Authenticated and token saved.")


def cmd_config(args):
    config = _load_env_config()
    updates = {
        "APPFLOWY_BASE_URL": args.base_url,
        "APPFLOWY_EMAIL": args.email,
        "APPFLOWY_WORKSPACE_ID": args.workspace_id,
        "APPFLOWY_REQUEST_TIMEOUT": args.request_timeout,
    }
    changed = False
    for key, value in updates.items():
        if value is not None:
            config[key] = str(value)
            changed = True
    if changed:
        _save_env_config(config)
    data = {"path": str(_env_config_path()), "config": {k: config.get(k) for k in ENV_CONFIG_KEYS if config.get(k)}}
    if args.json:
        print_json(data)
        return
    if changed:
        print(f"Config saved to {_env_config_path()}.")
    else:
        print(f"Config path: {_env_config_path()}")
    for key, value in data["config"].items():
        print(f"  {key}={value}")


# ── Structure ─────────────────────────────────────────────────────────

def cmd_workspaces(args):
    token = af.require_token()
    workspaces = af.get_workspaces(token)
    if args.json:
        print_json(workspaces)
        return
    for ws in workspaces:
        marker = " *" if ws["workspace_id"] == af.WORKSPACE_ID else ""
        print(f"  {ws['workspace_name']:<40} {ws['workspace_id']}{marker}")
    if af.WORKSPACE_ID:
        print(f"\n  * = active workspace (from .env)")


def cmd_spaces(args):
    token = af.require_token()
    ws = get_ws()
    spaces = af.get_spaces(token, ws)
    if args.json:
        print_json(spaces)
        return
    if not spaces:
        print("No spaces found.")
        return
    for s in spaces:
        icon = ""
        extra = s.get("extra") or {}
        if isinstance(extra, dict) and extra.get("space_icon"):
            icon = extra["space_icon"].split("/")[-1] + " "
        print(f"  {icon}{s['name']:<40} {s['view_id']}")


def cmd_pages(args):
    token = af.require_token()
    ws = get_ws()
    pages = af.collect_pages(token, ws)

    if args.space:
        q = args.space.lower()
        space = next((p for p in pages if p.get("is_space") and q in p["name"].lower()), None)
        if not space:
            print(f"Space '{args.space}' not found.")
            return
        space_id = space["view_id"]
        pages = [p for p in pages if p.get("parent_view_id") == space_id]

    if args.json:
        print_json(pages)
        return

    for p in pages:
        extra = p.get("extra") or {}
        is_db = extra.get("is_database_container") if isinstance(extra, dict) else False
        kind = "[space]" if p.get("is_space") else "[db]" if is_db else ""
        icon = ""
        if isinstance(p.get("icon"), dict) and p["icon"].get("ty") == 0:
            icon = p["icon"]["value"] + " "
        print(f"  {icon}{p['name']:<40} {kind:<8} {p['view_id'][:8]}...")


# ── Pages ─────────────────────────────────────────────────────────────

def cmd_read(args):
    token = af.require_token()
    ws = get_ws()
    page = af.find_page(token, ws, args.name, allow_fuzzy=args.fuzzy)
    if not page:
        print(f"Page not found: '{args.name}'")
        sys.exit(1)

    if args.json:
        from .yjs_decoder import decode_document_json
        data = af.get_page_collab(token, ws, page["view_id"])
        blocks = decode_document_json(data["doc_state"])
        print_json(blocks)
    else:
        content = af.get_page_content(token, ws, page["view_id"])
        if content:
            print(content)
        else:
            print("(empty page)")


def cmd_append(args):
    token = af.require_token()
    ws = get_ws()
    page = af.find_page(token, ws, args.name, allow_fuzzy=args.fuzzy)
    if not page:
        print(f"Page not found: '{args.name}'")
        sys.exit(1)
    block_type = args.type if args.type else "paragraph"
    af.append_to_page(token, ws, page["view_id"], args.text, block_type=block_type)
    print(f"Appended to '{page['name']}'.")


# ── Databases ─────────────────────────────────────────────────────────

def cmd_databases(args):
    token = af.require_token()
    ws = get_ws()
    databases = af.get_databases(token, ws)
    if args.json:
        print_json(databases)
        return
    for db in databases:
        views = db.get("views", [])
        view_names = ", ".join(v["name"] for v in views)
        print(f"  {db['id']}  {view_names}")


def cmd_fields(args):
    token = af.require_token()
    ws = get_ws()
    fields = af.get_database_fields(token, ws, args.database_id)
    if args.json:
        print_json(fields)
        return
    for f in fields:
        primary = " (primary)" if f.get("is_primary") else ""
        options = _get_field_options(f)
        opts_str = f"  [{', '.join(options)}]" if options else ""
        print(f"  {f['name']:<30} {f['field_type']:<15} {f['id']}{primary}{opts_str}")


def _get_field_options(field):
    to = field.get("type_option", {})
    content = to.get("content") if isinstance(to, dict) else None
    options = content.get("options", []) if isinstance(content, dict) else []
    return [o["name"] for o in options]


def _format_cell(key, val):
    if val is None:
        return None
    if isinstance(val, list):
        return ", ".join(str(v) for v in val) if val else None
    if isinstance(val, dict):
        return None
    if isinstance(val, str):
        if not val.strip():
            return None
        try:
            parsed = json.loads(val)
            if isinstance(parsed, (dict, list)):
                return None
        except (json.JSONDecodeError, TypeError):
            pass
        return val
    return str(val)


def cmd_rows(args):
    token = af.require_token()
    ws = get_ws()

    if args.updated:
        rows = af.get_database_rows_updated(token, ws, args.database_id)
        if not rows:
            print("No recently updated rows.")
            return
        if args.json:
            print_json(rows)
            return
        row_ids = [r.get("row_id", r.get("id")) for r in rows]
        details = af.get_database_row_details(token, ws, args.database_id, row_ids)
    else:
        details = af.get_database_row_details(token, ws, args.database_id)

    if not details:
        print("No rows found.")
        return

    if args.json:
        print_json(details)
        return

    for row in details:
        cells = row.get("cells", {})
        parts = []
        for key, val in cells.items():
            display = _format_cell(key, val)
            if display is not None:
                parts.append(f"{key}: {display}")
        summary = " | ".join(parts) if parts else "(empty)"
        print(f"  [{row['id'][:8]}] {summary}")


def _parse_cells(cell_args):
    cells = {}
    for item in cell_args:
        if "=" not in item:
            print(f"Invalid cell format: '{item}' (expected KEY=VALUE)")
            sys.exit(1)
        key, value = item.split("=", 1)
        cells[key] = _parse_cell_value(value)
    return cells


def _parse_cell_value(value):
    if not value:
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def cmd_row_create(args):
    token = af.require_token()
    ws = get_ws()
    cells = _parse_cells(args.cell)
    result = af.create_database_row(token, ws, args.database_id, cells)
    if args.json:
        print_json(result)
    else:
        row_id = result.get("data", "")
        print(f"Row created: {row_id}")


def cmd_row_update(args):
    token = af.require_token()
    ws = get_ws()
    cells = _parse_cells(args.cell)
    result = af.upsert_database_row(token, ws, args.database_id, args.row_id, cells, pre_hash=args.pre_hash)
    if args.json:
        print_json(result)
    else:
        print(f"Row {args.row_id[:8]}... updated.")


# ── Task profile ──────────────────────────────────────────────────────

def cmd_task_config(args):
    current = _load_config().get("tasks", {})
    profile = dict(current)
    updates = {
        "database": args.database,
        "title_field": args.title_field,
        "status_field": args.status_field,
        "notes_field": args.notes_field,
        "due_field": args.due_field,
        "priority_field": args.priority_field,
    }
    for key, value in updates.items():
        if value is not None:
            profile[key] = value
    _save_task_profile(profile)
    if args.json:
        print_json({"tasks": profile, "path": str(_config_path())})
    else:
        print(f"Task profile saved to {_config_path()}.")


def cmd_task_list(args):
    token = af.require_token()
    ws = get_ws()
    profile = _task_profile()
    details = af.get_database_row_details(token, ws, profile["database"])

    if args.status:
        status_field = _task_field(profile, "status", required=True)
        details = [r for r in details if _cell_text(r, status_field).casefold() == args.status.casefold()]

    if args.json:
        print_json(details)
        return

    title_field = _task_field(profile, "title", required=True)
    status_field = _task_field(profile, "status")
    due_field = _task_field(profile, "due")
    priority_field = _task_field(profile, "priority")
    for row in details:
        row_id = _row_id(row)
        parts = [_cell_text(row, title_field) or "(untitled)"]
        if status_field and _cell_text(row, status_field):
            parts.append(f"status: {_cell_text(row, status_field)}")
        if priority_field and _cell_text(row, priority_field):
            parts.append(f"priority: {_cell_text(row, priority_field)}")
        if due_field and _cell_text(row, due_field):
            parts.append(f"due: {_cell_text(row, due_field)}")
        print(f"  [{row_id[:8]}] " + " | ".join(parts))


def cmd_task_create(args):
    token = af.require_token()
    ws = get_ws()
    profile = _task_profile()
    args.title = args.title
    cells = _task_cells_from_args(args, profile)
    title_field = _task_field(profile, "title", required=True)
    cells[title_field] = args.title
    result = af.create_database_row(token, ws, profile["database"], cells)
    if args.json:
        print_json(result)
    else:
        print(f"Task created: {args.title}")


def _load_task_for_update(token, ws, profile, query, allow_fuzzy=False):
    rows = af.get_database_row_details(token, ws, profile["database"])
    title_field = _task_field(profile, "title", required=True)
    row = _find_task_row(rows, query, title_field, allow_fuzzy=allow_fuzzy)
    if not row:
        raise af.AppFlowyError(f"Task not found: '{query}'")
    return row


def cmd_task_move(args):
    token = af.require_token()
    ws = get_ws()
    profile = _task_profile()
    status_field = _task_field(profile, "status", required=True)
    row = _load_task_for_update(token, ws, profile, args.task, allow_fuzzy=args.fuzzy)
    row_id = _row_id(row)
    result = af.upsert_database_row(token, ws, profile["database"], row_id, {status_field: args.status})
    if args.json:
        print_json(result)
    else:
        print(f"Task {row_id[:8]}... moved to {args.status}.")


def cmd_task_note(args):
    token = af.require_token()
    ws = get_ws()
    profile = _task_profile()
    notes_field = _task_field(profile, "notes", required=True)
    row = _load_task_for_update(token, ws, profile, args.task, allow_fuzzy=args.fuzzy)
    row_id = _row_id(row)
    existing = _cell_text(row, notes_field)
    note = args.note if not existing else f"{existing}\n{args.note}"
    result = af.upsert_database_row(token, ws, profile["database"], row_id, {notes_field: note})
    if args.json:
        print_json(result)
    else:
        print(f"Note added to task {row_id[:8]}...")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(prog="appflowy", description="AppFlowy CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("auth", help="Authenticate via magic link")

    config_p = sub.add_parser("config", help="Save persistent CLI settings")
    config_p.add_argument("--email", help="AppFlowy account email")
    config_p.add_argument("--workspace-id", help="Default AppFlowy workspace ID")
    config_p.add_argument("--base-url", help="AppFlowy base URL")
    config_p.add_argument("--request-timeout", help="Request timeout in seconds")
    config_p.add_argument("--json", action="store_true", help="Output as JSON")

    workspaces_p = sub.add_parser("workspaces", help="List workspaces")
    workspaces_p.add_argument("--json", action="store_true", help="Output as JSON")

    spaces_p = sub.add_parser("spaces", help="List spaces in current workspace")
    spaces_p.add_argument("--json", action="store_true", help="Output as JSON")

    pages_p = sub.add_parser("pages", help="List pages")
    pages_p.add_argument("--space", help="Filter by space name")
    pages_p.add_argument("--json", action="store_true", help="Output as JSON")

    read_p = sub.add_parser("read", help="Read page content")
    read_p.add_argument("name", help="Page name or view ID")
    read_p.add_argument("--json", action="store_true", help="Output block structure as JSON")
    read_p.add_argument("--fuzzy", action="store_true", help="Allow unique substring page-name matches")

    append_p = sub.add_parser("append", help="Append text to a page")
    append_p.add_argument("name", help="Page name or view ID")
    append_p.add_argument("text", help="Text to append")
    append_p.add_argument("--fuzzy", action="store_true", help="Allow unique substring page-name matches")
    append_p.add_argument("--type", choices=["paragraph", "heading", "bulleted_list", "todo_list", "quote"],
                          default="paragraph", help="Block type (default: paragraph)")

    databases_p = sub.add_parser("databases", help="List databases")
    databases_p.add_argument("--json", action="store_true", help="Output as JSON")

    fields_p = sub.add_parser("fields", help="Show database fields")
    fields_p.add_argument("database_id", help="Database ID")
    fields_p.add_argument("--json", action="store_true", help="Output as JSON")

    rows_p = sub.add_parser("rows", help="Show database rows")
    rows_p.add_argument("database_id", help="Database ID")
    rows_p.add_argument("--updated", action="store_true", help="Only show recently updated rows")
    rows_p.add_argument("--json", action="store_true", help="Output as JSON")

    rc_p = sub.add_parser("row-create", help="Create a database row")
    rc_p.add_argument("database_id", help="Database ID")
    rc_p.add_argument("--cell", action="append", required=True, metavar="KEY=VALUE",
                      help="Cell value (repeatable)")
    rc_p.add_argument("--json", action="store_true", help="Output as JSON")

    ru_p = sub.add_parser("row-update", help="Update a database row")
    ru_p.add_argument("database_id", help="Database ID")
    ru_p.add_argument("row_id", help="Row ID")
    ru_p.add_argument("--cell", action="append", required=True, metavar="KEY=VALUE",
                      help="Cell value (repeatable)")
    ru_p.add_argument("--pre-hash", default="", help="Existing row pre_hash for conflict detection")
    ru_p.add_argument("--json", action="store_true", help="Output as JSON")

    task_p = sub.add_parser("task", help="Manage tasks through a configured database profile")
    task_sub = task_p.add_subparsers(dest="task_command")

    task_config_p = task_sub.add_parser("config", help="Configure semantic task fields")
    task_config_p.add_argument("--database", help="Task database ID")
    task_config_p.add_argument("--title-field", help="Field containing the task title")
    task_config_p.add_argument("--status-field", help="Field containing the task status")
    task_config_p.add_argument("--notes-field", help="Field containing task notes")
    task_config_p.add_argument("--due-field", help="Field containing the due date")
    task_config_p.add_argument("--priority-field", help="Field containing the priority")
    task_config_p.add_argument("--json", action="store_true", help="Output as JSON")

    task_list_p = task_sub.add_parser("list", help="List tasks")
    task_list_p.add_argument("--status", help="Filter by configured status field")
    task_list_p.add_argument("--json", action="store_true", help="Output as JSON")

    task_create_p = task_sub.add_parser("create", help="Create a task")
    task_create_p.add_argument("title", help="Task title")
    task_create_p.add_argument("--status", help="Initial status")
    task_create_p.add_argument("--notes", help="Initial notes")
    task_create_p.add_argument("--due", help="Due date")
    task_create_p.add_argument("--priority", help="Priority")
    task_create_p.add_argument("--json", action="store_true", help="Output as JSON")

    task_move_p = task_sub.add_parser("move", help="Move a task to a new status")
    task_move_p.add_argument("task", help="Task title or row ID")
    task_move_p.add_argument("status", help="New status")
    task_move_p.add_argument("--fuzzy", action="store_true", help="Allow unique substring title matches")
    task_move_p.add_argument("--json", action="store_true", help="Output as JSON")

    task_note_p = task_sub.add_parser("note", help="Append a note to a task notes field")
    task_note_p.add_argument("task", help="Task title or row ID")
    task_note_p.add_argument("note", help="Note text")
    task_note_p.add_argument("--fuzzy", action="store_true", help="Allow unique substring title matches")
    task_note_p.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    commands = {
        "auth": cmd_auth,
        "config": cmd_config,
        "workspaces": cmd_workspaces,
        "spaces": cmd_spaces,
        "pages": cmd_pages,
        "read": cmd_read,
        "append": cmd_append,
        "databases": cmd_databases,
        "fields": cmd_fields,
        "rows": cmd_rows,
        "row-create": cmd_row_create,
        "row-update": cmd_row_update,
    }

    task_commands = {
        "config": cmd_task_config,
        "list": cmd_task_list,
        "create": cmd_task_create,
        "move": cmd_task_move,
        "note": cmd_task_note,
    }

    try:
        if args.command in commands:
            commands[args.command](args)
        elif args.command == "task" and args.task_command in task_commands:
            task_commands[args.task_command](args)
        else:
            parser.print_help()
    except af.AmbiguousPageError as exc:
        print(str(exc), file=sys.stderr)
        print("Use a full page ID/name or rerun with a more specific query.", file=sys.stderr)
        sys.exit(2)
    except af.AppFlowyError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
