import os
import json
import struct
import uuid
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import requests
import pycrdt
from dotenv import load_dotenv


def _initial_config_path():
    configured = os.getenv("APPFLOWY_CONFIG_FILE")
    if configured:
        return Path(configured).expanduser()
    config_home = Path(os.getenv("XDG_CONFIG_HOME", "~/.config")).expanduser()
    return config_home / "appflowy-cli" / "config.env"


load_dotenv(_initial_config_path())
load_dotenv(override=True)

BASE_URL = os.getenv("APPFLOWY_BASE_URL", "https://beta.appflowy.cloud")
EMAIL = os.getenv("APPFLOWY_EMAIL")
WORKSPACE_ID = os.getenv("APPFLOWY_WORKSPACE_ID")
TOKEN_FILE = os.getenv("APPFLOWY_TOKEN_FILE")
CONFIG_FILE = os.getenv("APPFLOWY_CONFIG_FILE")
LEGACY_TOKEN_FILE = ".token"
REQUEST_TIMEOUT = float(os.getenv("APPFLOWY_REQUEST_TIMEOUT", "30"))


class AppFlowyError(RuntimeError):
    pass


class AmbiguousPageError(AppFlowyError):
    def __init__(self, query, matches):
        self.query = query
        self.matches = matches
        names = ", ".join(f"{p.get('name', '(untitled)')} ({p.get('view_id')})" for p in matches[:5])
        super().__init__(f"Page query '{query}' is ambiguous: {names}")


def _token_path():
    if TOKEN_FILE:
        return Path(TOKEN_FILE).expanduser()
    config_home = Path(os.getenv("XDG_CONFIG_HOME", "~/.config")).expanduser()
    return config_home / "appflowy-cli" / "token.json"


def config_path():
    if CONFIG_FILE:
        return Path(CONFIG_FILE).expanduser()
    config_home = Path(os.getenv("XDG_CONFIG_HOME", "~/.config")).expanduser()
    return config_home / "appflowy-cli" / "config.env"


def _legacy_token_path():
    return Path(LEGACY_TOKEN_FILE)


def _unwrap_data(data):
    return data["data"] if isinstance(data, dict) and "data" in data else data


def _extract_error_body(resp):
    if resp is None:
        return ""
    try:
        return resp.text[:500]
    except requests.RequestException:
        return ""


def _request_once(method, path, token=None, **kwargs):
    headers = kwargs.pop("headers", None) or {}
    if token:
        headers.update(_headers(token))
    if "json" in kwargs:
        headers.setdefault("Content-Type", "application/json")
    try:
        return requests.request(
            method,
            f"{BASE_URL}{path}",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            **kwargs,
        )
    except requests.Timeout as exc:
        raise AppFlowyError(f"AppFlowy request timed out after {REQUEST_TIMEOUT:g}s: {method} {path}") from exc
    except requests.RequestException as exc:
        raise AppFlowyError(f"AppFlowy request failed for {method} {path}: {exc}") from exc


def _request(method, path, token=None, refresh_on_unauthorized=True, **kwargs):
    auth_token = _latest_access_token(token) if token else None
    resp = _request_once(method, path, token=auth_token, **kwargs)
    if resp.status_code == 401 and token and refresh_on_unauthorized:
        auth_token = refresh_access_token()
        resp = _request_once(method, path, token=auth_token, **kwargs)
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        body = _extract_error_body(exc.response)
        raise AppFlowyError(f"AppFlowy API error for {method} {path}: {exc} {body}".strip()) from exc
    return resp


def _response_json(resp, context):
    try:
        return resp.json()
    except ValueError as exc:
        raise AppFlowyError(f"AppFlowy API returned invalid JSON for {context}.") from exc


def _check_api_result(result, context):
    if isinstance(result, dict) and result.get("code", 0) != 0:
        message = result.get("message") or result.get("error") or "Unknown error"
        raise AppFlowyError(f"{context} failed: {message}")
    return result


# ── Auth ──────────────────────────────────────────────────────────────

def request_magic_link():
    if not EMAIL:
        raise AppFlowyError("Set APPFLOWY_EMAIL in .env before running auth.")
    _request("POST", "/gotrue/magiclink", json={"email": EMAIL}, refresh_on_unauthorized=False)
    return EMAIL


def exchange_magic_link(link):
    parsed = urlparse(link)
    all_params = {**parse_qs(parsed.query), **parse_qs(parsed.fragment)}

    if "access_token" in all_params:
        return all_params["access_token"][0], all_params.get("refresh_token", [None])[0]

    token_key = "token_hash" if "token_hash" in all_params else "token" if "token" in all_params else None
    if not token_key:
        raise AppFlowyError("No token found in magic link URL.")

    resp = _request(
        "GET",
        "/gotrue/verify",
        params={token_key: all_params[token_key][0], "type": "magiclink"},
        allow_redirects=False,
        refresh_on_unauthorized=False,
    )
    if resp.status_code in (302, 303):
        redirect_url = resp.headers.get("Location", "")
        rp = parse_qs(urlparse(redirect_url).fragment)
        if "access_token" in rp:
            return rp["access_token"][0], rp.get("refresh_token", [None])[0]

    raise AppFlowyError("Could not extract token from magic link.")


def save_token(access_token, refresh_token=None):
    path = _token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"access_token": access_token, "refresh_token": refresh_token}, f)
    os.chmod(path, 0o600)


def load_token_data():
    for path in (_token_path(), _legacy_token_path()):
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as exc:
                raise AppFlowyError(f"Could not read token file {path}: {exc}") from exc
    return {}


def load_token():
    return load_token_data().get("access_token")


def _latest_access_token(fallback=None):
    return load_token_data().get("access_token") or fallback


def require_token():
    token = load_token()
    if not token:
        raise SystemExit("Not authenticated. Run: appflowy auth")
    return token


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _json_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def refresh_access_token():
    token_data = load_token_data()
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        raise AppFlowyError("Access token expired and no refresh token is saved. Run: appflowy auth")

    resp = _request(
        "POST",
        "/gotrue/token",
        params={"grant_type": "refresh_token"},
        json={"refresh_token": refresh_token},
        refresh_on_unauthorized=False,
    )
    data = _response_json(resp, "token refresh")
    access_token = data.get("access_token")
    new_refresh_token = data.get("refresh_token", refresh_token)
    if not access_token:
        raise AppFlowyError("AppFlowy token refresh response did not include an access token.")
    save_token(access_token, new_refresh_token)
    return access_token


# ── Workspaces ────────────────────────────────────────────────────────

def get_workspaces(token):
    data = _response_json(_request("GET", "/api/workspace", token=token), "get workspaces")
    return _unwrap_data(_check_api_result(data, "Get workspaces"))


# ── Folder / Pages ────────────────────────────────────────────────────

def get_folder(token, workspace_id, root_view_id=None):
    params = {"root_view_id": root_view_id} if root_view_id else {}
    data = _response_json(
        _request("GET", f"/api/workspace/{workspace_id}/folder", token=token, params=params),
        "get workspace folder",
    )
    return _check_api_result(data, "Get workspace folder")


def get_spaces(token, workspace_id):
    folder = get_folder(token, workspace_id)
    root = folder.get("data", folder)
    return [c for c in root.get("children", []) if c.get("is_space")]


def collect_pages(token, workspace_id):
    pages = []
    seen = set()

    def _walk(node):
        view_id = node.get("view_id")
        if view_id:
            if view_id in seen:
                return
            seen.add(view_id)
            pages.append(node)
        for child in node.get("children", []):
            _walk(child)
            child_view_id = child.get("view_id")
            if child_view_id and child.get("has_children"):
                deep = get_folder(token, workspace_id, child_view_id)
                _walk(deep.get("data", deep))

    folder = get_folder(token, workspace_id)
    root = folder.get("data", folder)
    _walk(root)
    return pages


def find_page_in_pages(pages, query, allow_fuzzy=False):
    for p in pages:
        if p.get("view_id") == query:
            return p
    q = query.casefold()
    exact = [p for p in pages if p.get("name", "").casefold() == q]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise AmbiguousPageError(query, exact)
    if not allow_fuzzy:
        return None
    matches = [p for p in pages if q in p.get("name", "").casefold()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise AmbiguousPageError(query, matches)
    return None


def find_page(token, workspace_id, query, allow_fuzzy=False):
    pages = collect_pages(token, workspace_id)
    return find_page_in_pages(pages, query, allow_fuzzy=allow_fuzzy)


# ── Page content (read) ───────────────────────────────────────────────

def get_page_collab(token, workspace_id, view_id):
    resp = _request(
        "GET",
        f"/api/workspace/{workspace_id}/collab/{view_id}",
        token=token,
        json={"workspace_id": workspace_id, "collab_type": 0,
              "inner": {"object_id": view_id, "collab_type": 0}},
    )
    data = _check_api_result(_response_json(resp, "get page collab"), "Get page collab")
    try:
        return data["data"]
    except (KeyError, TypeError) as exc:
        raise AppFlowyError(f"AppFlowy collab response did not include data for {view_id}.") from exc


def get_page_content(token, workspace_id, view_id):
    from .yjs_decoder import decode_document
    data = get_page_collab(token, workspace_id, view_id)
    return decode_document(data["doc_state"])


# ── Page content (write) ──────────────────────────────────────────────

def _encode_collab(doc):
    sv = doc.get_state()
    ds = doc.get_update(b'\x00')
    encoded = struct.pack('<Q', len(sv)) + sv
    encoded += struct.pack('<Q', len(ds)) + ds
    encoded += struct.pack('B', 0)  # EncoderVersion::V1
    encoded += struct.pack('B', 0)  # collab_version = None
    return encoded


def _put_collab(token, workspace_id, view_id, encoded):
    resp = _request(
        "PUT",
        f"/api/workspace/{workspace_id}/collab/{view_id}",
        token=token,
        json={
            "workspace_id": workspace_id,
            "object_id": view_id,
            "collab_type": 0,
            "encoded_collab_v1": list(encoded),
        },
    )
    result = _response_json(resp, "put page collab")
    return _check_api_result(result, "Update page collab")


def _collab_has_block(doc_state, block_id):
    doc = pycrdt.Doc()
    doc.apply_update(bytes(doc_state))
    root = doc.get("data", type=pycrdt.Map)
    document = root["document"]
    blocks = document["blocks"]
    return block_id in blocks


def append_to_page(token, workspace_id, view_id, text, block_type="paragraph"):
    data = get_page_collab(token, workspace_id, view_id)

    doc = pycrdt.Doc()
    doc.apply_update(bytes(data["doc_state"]))

    root = doc.get("data", type=pycrdt.Map)
    document = root["document"]
    meta = document["meta"]
    text_map = meta["text_map"]
    children_map = meta["children_map"]
    blocks = document["blocks"]

    page_block_id = None
    for k in blocks:
        b = blocks[k]
        if isinstance(b, pycrdt.Map) and b.get("ty") == "page":
            page_block_id = k
            break
    if page_block_id is None:
        raise AppFlowyError(f"Could not find page block in collab document {view_id}.")

    page_children_key = blocks[page_block_id]["children"]
    page_children = children_map[page_children_key]

    bid = uuid.uuid4().hex
    tid = uuid.uuid4().hex
    cid = uuid.uuid4().hex

    text_map[tid] = pycrdt.Text(text)
    children_map[cid] = pycrdt.Array()
    blocks[bid] = pycrdt.Map({
        "id": bid, "ty": block_type, "parent": page_block_id,
        "children": cid, "external_id": tid, "external_type": "text",
        "data": json.dumps({"level": 2}) if block_type == "heading" else "{}",
    })
    page_children.append(bid)

    _put_collab(token, workspace_id, view_id, _encode_collab(doc))
    updated = get_page_collab(token, workspace_id, view_id)
    if not _collab_has_block(updated["doc_state"], bid):
        raise AppFlowyError(
            "AppFlowy accepted the page update, but the appended block was not present after reload. "
            "Retry the append after refreshing the page state."
        )
    return bid


# ── Databases ─────────────────────────────────────────────────────────

def get_databases(token, workspace_id):
    data = _response_json(
        _request("GET", f"/api/workspace/{workspace_id}/database", token=token),
        "get databases",
    )
    return _unwrap_data(_check_api_result(data, "Get databases"))


def get_database_fields(token, workspace_id, database_id):
    data = _response_json(
        _request("GET", f"/api/workspace/{workspace_id}/database/{database_id}/fields", token=token),
        "get database fields",
    )
    return _unwrap_data(_check_api_result(data, "Get database fields"))


def get_database_rows(token, workspace_id, database_id):
    data = _response_json(
        _request("GET", f"/api/workspace/{workspace_id}/database/{database_id}/row", token=token),
        "get database rows",
    )
    return _unwrap_data(_check_api_result(data, "Get database rows"))


def get_database_rows_updated(token, workspace_id, database_id):
    data = _response_json(
        _request("GET", f"/api/workspace/{workspace_id}/database/{database_id}/row/updated", token=token),
        "get updated database rows",
    )
    return _unwrap_data(_check_api_result(data, "Get updated database rows"))


def get_database_row_details(token, workspace_id, database_id, row_ids=None, with_doc=False):
    if row_ids is None:
        rows = get_database_rows(token, workspace_id, database_id)
        row_ids = [r["id"] for r in rows]
    if not row_ids:
        return []
    params = {"ids": ",".join(row_ids)}
    if with_doc:
        params["with_doc"] = "true"
    resp = _request(
        "GET",
        f"/api/workspace/{workspace_id}/database/{database_id}/row/detail",
        token=token,
        params=params,
    )
    data = _response_json(resp, "get database row details")
    return _unwrap_data(_check_api_result(data, "Get database row details"))


def create_database_row(token, workspace_id, database_id, cells):
    resp = _request(
        "POST",
        f"/api/workspace/{workspace_id}/database/{database_id}/row",
        token=token,
        json={"cells": cells},
    )
    data = _response_json(resp, "create database row")
    return _check_api_result(data, "Create database row")


def upsert_database_row(token, workspace_id, database_id, row_id, cells, pre_hash=""):
    resp = _request(
        "PUT",
        f"/api/workspace/{workspace_id}/database/{database_id}/row",
        token=token,
        json={"row_id": row_id, "cells": cells, "pre_hash": pre_hash},
    )
    data = _response_json(resp, "upsert database row")
    return _check_api_result(data, "Upsert database row")
