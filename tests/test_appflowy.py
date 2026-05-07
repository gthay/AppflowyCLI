import pytest

from appflowy_cli import client as af


def test_find_page_prefers_view_id():
    pages = [
        {"view_id": "abc", "name": "Daily"},
        {"view_id": "def", "name": "Daily"},
    ]

    assert af.find_page_in_pages(pages, "def") == {"view_id": "def", "name": "Daily"}


def test_find_page_exact_name_is_case_insensitive():
    pages = [{"view_id": "abc", "name": "Daily Report"}]

    assert af.find_page_in_pages(pages, "daily report") == pages[0]


def test_find_page_rejects_ambiguous_exact_names():
    pages = [
        {"view_id": "abc", "name": "Daily"},
        {"view_id": "def", "name": "daily"},
    ]

    with pytest.raises(af.AmbiguousPageError):
        af.find_page_in_pages(pages, "Daily")


def test_find_page_requires_fuzzy_for_substring_match():
    pages = [{"view_id": "abc", "name": "Daily Report"}]

    assert af.find_page_in_pages(pages, "Report") is None
    assert af.find_page_in_pages(pages, "Report", allow_fuzzy=True) == pages[0]


def test_find_page_rejects_ambiguous_fuzzy_names():
    pages = [
        {"view_id": "abc", "name": "Client Tasks"},
        {"view_id": "def", "name": "Internal Tasks"},
    ]

    with pytest.raises(af.AmbiguousPageError):
        af.find_page_in_pages(pages, "Tasks", allow_fuzzy=True)


def test_exchange_magic_link_extracts_fragment_tokens():
    access_token, refresh_token = af.exchange_magic_link(
        "https://example.com/callback#access_token=access&refresh_token=refresh"
    )

    assert access_token == "access"
    assert refresh_token == "refresh"


def test_exchange_magic_link_rejects_link_without_token():
    with pytest.raises(af.AppFlowyError, match="No token found"):
        af.exchange_magic_link("https://example.com/callback")


def test_request_refreshes_expired_access_token(monkeypatch, tmp_path):
    token_file = tmp_path / "token.json"
    monkeypatch.setattr(af, "TOKEN_FILE", str(token_file))
    af.save_token("old-access", "refresh")

    calls = []

    class FakeResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload
            self.text = str(payload)

        def json(self):
            return self._payload

        def raise_for_status(self):
            if self.status_code >= 400:
                import requests

                raise requests.HTTPError("error", response=self)

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if url.endswith("/api/workspace"):
            if len([c for c in calls if c[1].endswith("/api/workspace")]) == 1:
                return FakeResponse(401, {"message": "expired"})
            return FakeResponse(200, {"data": [{"workspace_id": "ws"}]})
        if url.endswith("/gotrue/token"):
            return FakeResponse(200, {"access_token": "new-access", "refresh_token": "new-refresh"})
        raise AssertionError(url)

    monkeypatch.setattr(af.requests, "request", fake_request)

    assert af.get_workspaces("old-access") == [{"workspace_id": "ws"}]
    assert af.load_token_data() == {"access_token": "new-access", "refresh_token": "new-refresh"}
    assert calls[-1][2]["headers"]["Authorization"] == "Bearer new-access"


def test_api_result_errors_are_appflowy_errors():
    with pytest.raises(af.AppFlowyError, match="Create row failed"):
        af._check_api_result({"code": 500, "message": "bad cells"}, "Create row")
