from appflowy_cli import cli
from appflowy_cli import client as af


def test_parse_cells_keeps_plain_strings():
    assert cli._parse_cells(["Title=Write report"]) == {"Title": "Write report"}


def test_parse_cells_decodes_json_values():
    assert cli._parse_cells(["Done=true", "Estimate=2", "Tags=[\"client\",\"urgent\"]"]) == {
        "Done": True,
        "Estimate": 2,
        "Tags": ["client", "urgent"],
    }


def test_parse_cells_allows_equals_in_value():
    assert cli._parse_cells(["Formula=a=b"]) == {"Formula": "a=b"}


def test_task_profile_round_trips(tmp_path, monkeypatch):
    config = tmp_path / "appflowy.toml"
    monkeypatch.setattr(cli, "CONFIG_FILE", str(config))

    cli._save_task_profile({
        "database": "db1",
        "title_field": "Task",
        "status_field": "Stage",
        "notes_field": "Body",
    })

    assert cli._load_config()["tasks"] == {
        "database": "db1",
        "title_field": "Task",
        "status_field": "Stage",
        "notes_field": "Body",
    }


def test_env_config_round_trips(tmp_path, monkeypatch):
    config = tmp_path / "config.env"
    monkeypatch.setattr(cli.af, "CONFIG_FILE", str(config))

    cli._save_env_config({
        "APPFLOWY_EMAIL": "user@example.com",
        "APPFLOWY_WORKSPACE_ID": "ws1",
    })

    assert cli._load_env_config() == {
        "APPFLOWY_EMAIL": "user@example.com",
        "APPFLOWY_WORKSPACE_ID": "ws1",
    }


def test_task_cells_use_configured_field_names():
    class Args:
        title = "Send invoice"
        status = "Todo"
        notes = "Draft exists"
        due = None
        priority = "High"

    profile = {
        "title_field": "Task",
        "status_field": "Stage",
        "notes_field": "Body",
        "priority_field": "Importance",
    }

    assert cli._task_cells_from_args(Args, profile) == {
        "Task": "Send invoice",
        "Stage": "Todo",
        "Body": "Draft exists",
        "Importance": "High",
    }


def test_find_task_row_prefers_exact_title():
    rows = [
        {"id": "row1", "cells": {"Task": "Send invoice"}},
        {"id": "row2", "cells": {"Task": "Send invoice draft"}},
    ]

    assert cli._find_task_row(rows, "Send invoice", "Task", allow_fuzzy=True)["id"] == "row1"


def test_find_task_row_allows_row_id_without_fuzzy():
    rows = [{"id": "row1", "cells": {"Task": "Send invoice"}}]

    assert cli._find_task_row(rows, "row1", "Task")["id"] == "row1"


def test_find_task_row_allows_row_id_key_without_fuzzy():
    rows = [{"row_id": "row1", "cells": {"Task": "Send invoice"}}]

    assert cli._find_task_row(rows, "row1", "Task")["row_id"] == "row1"


def test_find_task_row_rejects_ambiguous_fuzzy_title():
    rows = [
        {"id": "row1", "cells": {"Task": "Client invoice"}},
        {"id": "row2", "cells": {"Task": "Vendor invoice"}},
    ]

    try:
        cli._find_task_row(rows, "invoice", "Task", allow_fuzzy=True)
    except af.AppFlowyError as exc:
        assert "ambiguous" in str(exc)
    else:
        raise AssertionError("Expected ambiguous task query")
