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


def test_coerce_database_cells_maps_single_select_names_to_ids(monkeypatch):
    def fake_get_database_fields(token, workspace_id, database_id):
        return [
            {
                "name": "Priority",
                "id": "priority-field-id",
                "field_type": "SingleSelect",
                "type_option": {
                    "content": {
                        "options": [
                            {"id": "high-id", "name": "High"},
                            {"id": "low-id", "name": "Low"},
                        ]
                    }
                },
            },
            {"name": "Name", "id": "name-field-id", "field_type": "RichText", "type_option": {}},
        ]

    monkeypatch.setattr(cli.af, "get_database_fields", fake_get_database_fields)

    assert cli._coerce_database_cells("token", "ws", "db", {"Name": "Task", "Priority": "High"}) == {
        "name-field-id": "Task",
        "priority-field-id": "high-id",
    }


def test_coerce_database_cells_accepts_field_ids(monkeypatch):
    def fake_get_database_fields(token, workspace_id, database_id):
        return [
            {"name": "Name", "id": "name-field-id", "field_type": "RichText", "type_option": {}},
        ]

    monkeypatch.setattr(cli.af, "get_database_fields", fake_get_database_fields)

    assert cli._coerce_database_cells("token", "ws", "db", {"name-field-id": "Task"}) == {
        "name-field-id": "Task",
    }


def test_coerce_database_cells_accepts_single_select_ids(monkeypatch):
    def fake_get_database_fields(token, workspace_id, database_id):
        return [
            {
                "name": "Priority",
                "id": "priority-field-id",
                "field_type": "SingleSelect",
                "type_option": {"content": {"options": [{"id": "high-id", "name": "High"}]}},
            },
        ]

    monkeypatch.setattr(cli.af, "get_database_fields", fake_get_database_fields)

    assert cli._coerce_database_cells("token", "ws", "db", {"Priority": "high-id"}) == {
        "priority-field-id": "high-id",
    }


def test_coerce_database_cells_rejects_unknown_single_select_names(monkeypatch):
    def fake_get_database_fields(token, workspace_id, database_id):
        return [
            {
                "name": "Priority",
                "id": "priority-field-id",
                "field_type": "SingleSelect",
                "type_option": {"content": {"options": [{"id": "high-id", "name": "High"}]}},
            },
        ]

    monkeypatch.setattr(cli.af, "get_database_fields", fake_get_database_fields)

    try:
        cli._coerce_database_cells("token", "ws", "db", {"Priority": "Urgent"})
    except af.AppFlowyError as exc:
        assert "Invalid option for Priority" in str(exc)
        assert "High" in str(exc)
    else:
        raise AssertionError("Expected invalid single select option")


def test_coerce_database_cells_maps_date_field_to_timestamp_payload(monkeypatch):
    def fake_get_database_fields(token, workspace_id, database_id):
        return [
            {"name": "Deadline", "id": "deadline-field-id", "field_type": "DateTime", "field_type_id": 2},
        ]

    monkeypatch.setattr(cli.af, "get_database_fields", fake_get_database_fields)

    assert cli._coerce_database_cells("token", "ws", "db", {"Deadline": "2026-05-13"}) == {
        "deadline-field-id": {
            "data": "1778630400",
            "field_type": 2,
            "is_range": False,
            "include_time": False,
            "end_timestamp": "",
            "reminder_id": "",
        },
    }


def test_coerce_database_cells_maps_datetime_field_to_timestamp_payload(monkeypatch):
    def fake_get_database_fields(token, workspace_id, database_id):
        return [
            {"name": "Deadline", "id": "deadline-field-id", "field_type": "DateTime", "field_type_id": 2},
        ]

    monkeypatch.setattr(cli.af, "get_database_fields", fake_get_database_fields)

    assert cli._coerce_database_cells("token", "ws", "db", {"Deadline": "2026-05-15T09:30:00+07:00"}) == {
        "deadline-field-id": {
            "data": "1778812200",
            "field_type": 2,
            "is_range": False,
            "include_time": True,
            "end_timestamp": "",
            "reminder_id": "",
        },
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


def test_extract_summary_section_stops_at_next_heading():
    markdown = "#### Summary\nThis is summary\nwith details\n# Description\nLong body"

    assert cli._extract_summary_section(markdown) == "This is summary\nwith details"


def test_extract_summary_section_ignores_body_without_summary_heading():
    markdown = "# Description\n#### Summary\nToo late"

    assert cli._extract_summary_section(markdown) is None


def test_extract_summary_section_requires_exact_summary_heading():
    markdown = "#### Not Summary\nText\n# Description"

    assert cli._extract_summary_section(markdown) is None


def test_extract_summary_section_accepts_custom_heading():
    markdown = "#### Brief\nShort version\n# Description\nLong body"

    assert cli._extract_summary_section(markdown, heading="Brief") == "Short version"


def test_extract_flattened_summary_stops_at_description_heading():
    text = "SummaryShort versionDescriptionLong body"

    assert cli._extract_flattened_summary(text, stop_headings=["Description"]) == "Short version"


def test_extract_flattened_summary_stops_at_next_known_heading():
    text = "SummaryShort versionNotesLong body"

    assert cli._extract_flattened_summary(text, stop_headings=["Description", "Notes"]) == "Short version"


def test_extract_flattened_summary_uses_custom_heading_and_stop_heading():
    text = "BriefShort versionDetailsLong body"

    assert cli._extract_flattened_summary(text, heading="Brief", stop_headings=["Details"]) == "Short version"


def test_extract_flattened_summary_allows_missing_description_heading():
    text = "SummaryShort version"

    assert cli._extract_flattened_summary(text) == "Short version"


def test_filter_rows_by_status_accepts_multiple_statuses():
    rows = [
        {"id": "row1", "cells": {"Stage": "Todo"}},
        {"id": "row2", "cells": {"Stage": "In Progress"}},
        {"id": "row3", "cells": {"Stage": "Done"}},
    ]

    assert cli._filter_rows_by_status(rows, "Stage", ["todo", "Done"]) == [rows[0], rows[2]]


def test_filter_rows_by_status_excludes_multiple_statuses():
    rows = [
        {"id": "row1", "cells": {"Stage": "Todo"}},
        {"id": "row2", "cells": {"Stage": "Archived"}},
        {"id": "row3", "cells": {"Stage": "Done"}},
    ]

    assert cli._filter_rows_by_status(rows, "Stage", exclude_statuses=["archived", "Done"]) == [rows[0]]


def test_filter_rows_by_status_combines_include_and_exclude():
    rows = [
        {"id": "row1", "cells": {"Stage": "Todo"}},
        {"id": "row2", "cells": {"Stage": "Doing"}},
        {"id": "row3", "cells": {"Stage": "Done"}},
    ]

    assert cli._filter_rows_by_status(
        rows,
        "Stage",
        statuses=["Todo", "Doing", "Done"],
        exclude_statuses=["done"],
    ) == [rows[0], rows[1]]


def test_add_row_summaries_omits_missing_summary(monkeypatch):
    rows = [
        {"id": "row1", "cells": {"Task": "Has summary"}},
        {"id": "row2", "cells": {"Task": "No summary"}},
    ]

    def fake_get_page_content(token, workspace_id, row_id):
        if row_id == "row1":
            return "#### Summary\nShort version\n# Description\nLong body"
        return "# Description\nLong body"

    monkeypatch.setattr(cli.af, "get_page_content", fake_get_page_content)

    assert cli._add_row_summaries("token", "ws", rows) == [
        {"id": "row1", "cells": {"Task": "Has summary"}, "summary": "Short version"},
        {"id": "row2", "cells": {"Task": "No summary"}},
    ]


def test_add_row_summaries_skips_undecodable_row_body(monkeypatch):
    rows = [
        {"id": "row1", "cells": {"Task": "Has summary"}},
        {"id": "row2", "cells": {"Task": "Undecodable body"}},
    ]

    def fake_get_page_content(token, workspace_id, row_id):
        if row_id == "row2":
            raise KeyError("document")
        return "#### Summary\nShort version"

    monkeypatch.setattr(cli.af, "get_page_content", fake_get_page_content)

    assert cli._add_row_summaries("token", "ws", rows) == [
        {"id": "row1", "cells": {"Task": "Has summary"}, "summary": "Short version"},
        {"id": "row2", "cells": {"Task": "Undecodable body"}},
    ]


def test_add_row_summaries_uses_row_detail_doc_before_collab(monkeypatch):
    rows = [
        {
            "id": "row1",
            "cells": {"Task": "Has flattened summary"},
            "doc": "SummaryShort versionDescriptionLong body",
        },
    ]

    def fail_get_page_content(token, workspace_id, row_id):
        raise AssertionError("row detail doc should be used before fetching collab")

    monkeypatch.setattr(cli.af, "get_page_content", fail_get_page_content)

    assert cli._add_row_summaries("token", "ws", rows) == [
        {
            "id": "row1",
            "cells": {"Task": "Has flattened summary"},
            "doc": None,
            "summary": "Short version",
        },
    ]


def test_add_row_summaries_accepts_custom_summary_heading(monkeypatch):
    rows = [
        {
            "id": "row1",
            "cells": {"Task": "Has custom summary"},
            "doc": "BriefShort versionDetailsLong body",
        },
    ]

    def fail_get_page_content(token, workspace_id, row_id):
        raise AssertionError("row detail doc should be used before fetching collab")

    monkeypatch.setattr(cli.af, "get_page_content", fail_get_page_content)

    assert cli._add_row_summaries(
        "token",
        "ws",
        rows,
        summary_heading="Brief",
        stop_heading="Details",
    ) == [
        {
            "id": "row1",
            "cells": {"Task": "Has custom summary"},
            "doc": None,
            "summary": "Short version",
        },
    ]
