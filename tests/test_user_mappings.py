import io
import json
import sqlite3
import urllib.error
from types import SimpleNamespace

import pytest

from server import user_mappings
from server.database import SCHEMA
from server.user_mappings import connect_mapping_database, mapping_view, set_user_mapping, sync_directory_users


TENANT_ID = "00000000-0000-0000-0000-000000000000"


def _patch_graph_transport(monkeypatch, pages: list[dict], failures: dict[int, object] | None = None) -> dict:
    """Patch Azure CLI token acquisition and the HTTP transport used by _graph_pages."""
    failures = failures or {}
    state = {"calls": 0, "sleeps": []}

    def fake_urlopen(request, timeout=None):
        state["calls"] += 1
        failure = failures.get(state["calls"])
        if failure is not None:
            raise failure(request.full_url)
        return io.BytesIO(json.dumps(pages.pop(0)).encode("utf-8"))

    monkeypatch.setattr(user_mappings, "find_azure_cli", lambda: "/fake/az")
    monkeypatch.setattr(
        user_mappings.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=json.dumps({"accessToken": "test-token"}), stderr=""),
    )
    monkeypatch.setattr(user_mappings.time, "sleep", state["sleeps"].append)
    monkeypatch.setattr(user_mappings.urllib.request, "urlopen", fake_urlopen)
    return state


def test_graph_pages_retries_transient_rate_limit(monkeypatch) -> None:
    pages = [
        {"value": [{"id": "u1", "displayName": "One"}], "@odata.nextLink": "https://graph.microsoft.com/v1.0/users?$skiptoken=2"},
        {"value": [{"id": "u2", "displayName": "Two"}]},
    ]

    def rate_limited(url):
        return urllib.error.HTTPError(url, 429, "Too many requests", {"Retry-After": "3"}, None)

    state = _patch_graph_transport(monkeypatch, pages, failures={1: rate_limited})

    users = list(user_mappings._graph_pages(TENANT_ID))

    assert [user["id"] for user in users] == ["u1", "u2"]
    assert state["calls"] == 3
    assert state["sleeps"] == [3.0]


def test_graph_pages_does_not_retry_permanent_errors(monkeypatch) -> None:
    pages = [{"value": []}]

    def forbidden(url):
        return urllib.error.HTTPError(url, 403, "Forbidden", {}, None)

    state = _patch_graph_transport(monkeypatch, pages, failures={1: forbidden})

    with pytest.raises(RuntimeError, match="user discovery failed"):
        list(user_mappings._graph_pages(TENANT_ID))

    assert state["calls"] == 1
    assert state["sleeps"] == []


def test_graph_pages_gives_up_after_max_retries(monkeypatch) -> None:
    pages = [{"value": []}]

    def unavailable(url):
        return urllib.error.HTTPError(url, 503, "Unavailable", {}, None)

    failures = {call: unavailable for call in range(1, user_mappings.GRAPH_MAX_RETRIES + 2)}
    state = _patch_graph_transport(monkeypatch, pages, failures=failures)

    with pytest.raises(RuntimeError, match="user discovery failed"):
        list(user_mappings._graph_pages(TENANT_ID))

    assert state["calls"] == user_mappings.GRAPH_MAX_RETRIES + 1
    assert state["sleeps"] == [float(min(300.0, 2 ** attempt)) for attempt in range(user_mappings.GRAPH_MAX_RETRIES)]


@pytest.fixture
def snapshot() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    connection.execute("INSERT INTO workspaces(id, name) VALUES ('workspace', 'Workspace')")
    connection.execute("INSERT INTO principals(id, display_name, email, principal_type) VALUES ('source-1', 'Source One', 'source1@example.com', 'User')")
    connection.execute("INSERT INTO principals(id, display_name, email, principal_type) VALUES ('source-2', 'Source Two', 'source2@example.com', 'User')")
    connection.execute("INSERT INTO workspace_roles(workspace_id, principal_id, role) VALUES ('workspace', 'source-1', 'Member')")
    connection.execute("INSERT INTO workspace_roles(workspace_id, principal_id, role) VALUES ('workspace', 'source-2', 'Viewer')")
    yield connection
    connection.close()


@pytest.fixture
def mapping_database(tmp_path):
    path = tmp_path / "mappings.db"
    with connect_mapping_database(path) as connection:
        connection.executemany(
            """
            INSERT INTO directory_users(tenant_id, id, display_name, user_principal_name, mail, user_type, account_enabled)
            VALUES (?, ?, ?, ?, ?, 'Member', 1)
            """,
            [
                (TENANT_ID, "source-1", "Source One", "source1@example.com", "source1@example.com"),
                (TENANT_ID, "source-2", "Source Two", "source2@example.com", "source2@example.com"),
                (TENANT_ID, "target-1", "Target One", "target1@example.com", "target1@example.com"),
                (TENANT_ID, "target-2", "Target Two", "target2@example.com", "target2@example.com"),
            ],
        )
        connection.commit()
    return path


def test_mapping_view_splits_fabric_and_available_users(snapshot, mapping_database) -> None:
    result = mapping_view(TENANT_ID, snapshot, mapping_database)

    assert [user["id"] for user in result["sourceUsers"]] == ["source-1", "source-2"]
    assert [user["id"] for user in result["targetUsers"]] == ["target-1", "target-2"]


def test_target_user_can_only_be_mapped_once(snapshot, mapping_database) -> None:
    set_user_mapping(TENANT_ID, "source-1", "target-1", snapshot, mapping_database)

    with pytest.raises(ValueError, match="already mapped"):
        set_user_mapping(TENANT_ID, "source-2", "target-1", snapshot, mapping_database)


def test_fabric_user_cannot_be_used_as_target(snapshot, mapping_database) -> None:
    with pytest.raises(ValueError, match="without Fabric presence"):
        set_user_mapping(TENANT_ID, "source-1", "source-2", snapshot, mapping_database)


def test_directory_refresh_preserves_mapping_for_existing_users(monkeypatch, snapshot, mapping_database) -> None:
    set_user_mapping(TENANT_ID, "source-1", "target-1", snapshot, mapping_database)
    refreshed_users = [
        {
            "id": user_id,
            "displayName": display_name,
            "userPrincipalName": f"{user_id}@example.com",
            "mail": f"{user_id}@example.com",
            "userType": "Member",
            "accountEnabled": True,
        }
        for user_id, display_name in (
            ("source-1", "Renamed Source"),
            ("source-2", "Source Two"),
            ("target-1", "Target One"),
            ("target-2", "Target Two"),
        )
    ]
    monkeypatch.setattr(user_mappings, "_graph_pages", lambda tenant_id: iter(refreshed_users))

    sync_directory_users(TENANT_ID, mapping_database)

    result = mapping_view(TENANT_ID, snapshot, mapping_database)
    source = next(user for user in result["sourceUsers"] if user["id"] == "source-1")
    assert source["displayName"] == "Renamed Source"
    assert source["targetUserId"] == "target-1"