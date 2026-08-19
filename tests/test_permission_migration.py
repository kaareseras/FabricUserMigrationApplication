import io
import json
import sqlite3
import urllib.error
from unittest.mock import ANY

import pytest

from server.database import SCHEMA
from server.permission_migration import PermissionMigrationManager, build_permission_plan
from server.user_mappings import connect_mapping_database


TENANT_ID = "00000000-0000-0000-0000-000000000000"


def create_snapshot() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    connection.execute("INSERT INTO workspaces(id, name) VALUES ('workspace-1', 'Finance')")
    connection.execute("INSERT INTO workspaces(id, name) VALUES ('workspace-2', 'Shared reports')")
    connection.execute("INSERT INTO workspaces(id, name) VALUES ('workspace-3', 'Unknown role')")
    connection.execute("INSERT INTO principals(id, display_name, email, principal_type) VALUES ('source-1', 'Source', 'source@example.com', 'User')")
    connection.execute("INSERT INTO workspace_roles(workspace_id, principal_id, role) VALUES ('workspace-1', 'source-1', 'Member')")
    connection.execute("INSERT INTO workspace_roles(workspace_id, principal_id, role) VALUES ('workspace-3', 'source-1', 'CustomRole')")
    connection.execute("INSERT INTO artifacts(id, workspace_id, name, type) VALUES ('covered-report', 'workspace-1', 'Covered report', 'reports')")
    connection.execute("INSERT INTO artifacts(id, workspace_id, name, type) VALUES ('covered-notebook', 'workspace-1', 'Covered notebook', 'Notebook')")
    connection.execute("INSERT INTO artifacts(id, workspace_id, name, type) VALUES ('explicit-dataset', 'workspace-1', 'Explicit model', 'datasets')")
    connection.execute("INSERT INTO artifacts(id, workspace_id, name, type) VALUES ('dataset-1', 'workspace-2', 'Model', 'datasets')")
    connection.execute("INSERT INTO artifacts(id, workspace_id, name, type) VALUES ('report-1', 'workspace-2', 'Report', 'reports')")
    connection.execute("INSERT INTO item_permissions(artifact_id, workspace_id, principal_id, access_right) VALUES ('covered-report', 'workspace-1', 'source-1', 'Read')")
    connection.execute("INSERT INTO item_permissions(artifact_id, workspace_id, principal_id, access_right) VALUES ('covered-notebook', 'workspace-1', 'source-1', 'ReadWriteReshareExecute')")
    connection.execute("INSERT INTO item_permissions(artifact_id, workspace_id, principal_id, access_right) VALUES ('explicit-dataset', 'workspace-1', 'source-1', 'Read')")
    connection.execute("INSERT INTO item_permissions(artifact_id, workspace_id, principal_id, access_right) VALUES ('dataset-1', 'workspace-2', 'source-1', 'ReadExplore')")
    connection.execute("INSERT INTO item_permissions(artifact_id, workspace_id, principal_id, access_right) VALUES ('report-1', 'workspace-2', 'source-1', 'Read')")
    return connection


def create_mappings(path) -> None:
    with connect_mapping_database(path) as connection:
        connection.executemany(
            """
            INSERT INTO directory_users(tenant_id, id, display_name, user_principal_name, mail, user_type, account_enabled)
            VALUES (?, ?, ?, ?, ?, 'Member', 1)
            """,
            [
                (TENANT_ID, "source-1", "Source", "source@example.com", "source@example.com"),
                (TENANT_ID, "target-1", "Target", "target@example.com", "target@example.com"),
            ],
        )
        connection.execute("INSERT INTO user_mappings(tenant_id, source_user_id, target_user_id) VALUES (?, 'source-1', 'target-1')", (TENANT_ID,))
        connection.commit()


def test_plan_copies_exact_supported_rights_and_reports_unsupported(tmp_path) -> None:
    mapping_database = tmp_path / "mappings.db"
    create_mappings(mapping_database)
    snapshot = create_snapshot()

    plan = build_permission_plan(TENANT_ID, snapshot, mapping_database)

    assert plan["counts"] == {"workspaceRoles": 1, "datasetRights": 2, "coveredByWorkspaceRoles": 2, "unsupported": 2, "total": 3}
    assert [(item["kind"], item["right"]) for item in plan["operations"]] == [("datasetRight", "Read"), ("workspaceRole", "Member"), ("datasetRight", "ReadExplore")]
    assert {item["right"] for item in plan["unsupported"]} == {"CustomRole", "Read"}
    assert {item["right"] for item in plan["coveredByWorkspaceRole"]} == {"Read", "ReadWriteReshareExecute"}
    snapshot.close()


def test_completed_operations_resume_from_checkpoint(tmp_path, monkeypatch) -> None:
    checkpoint_directory = tmp_path / "jobs"
    manager = PermissionMigrationManager(checkpoint_directory, minimum_interval_seconds=0)
    operations = [
        {"id": "one", "kind": "workspaceRole", "workspaceName": "One", "artifactName": None, "targetUserName": "Target", "right": "Member"},
        {"id": "two", "kind": "datasetRight", "workspaceName": "One", "artifactName": "Model", "targetUserName": "Target", "right": "Read"},
    ]
    checkpoint_directory.mkdir()
    (checkpoint_directory / f"{TENANT_ID}.checkpoint.ndjson").write_text(json.dumps({"tenantId": TENANT_ID, "operationId": "one"}) + "\n", encoding="utf-8")
    executed = []
    monkeypatch.setattr(manager, "_execute_operation", lambda operation, provider: executed.append(operation["id"]) or "applied")
    manager._job = {"status": "running", "logs": [], "failures": []}

    manager._run(TENANT_ID, {"operations": operations, "unsupported": [], "counts": {}})

    assert executed == ["two"]
    assert manager.status()["result"] == {"applied": 1, "alreadyApplied": 1, "failed": 0, "unsupported": 0, "total": 2}


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None

    @staticmethod
    def read() -> bytes:
        return b"{}"


class FakeTokenProvider:
    def __init__(self) -> None:
        self.invalidated = []

    def get(self, resource: str) -> str:
        return "token"

    def invalidate(self, resource: str) -> None:
        self.invalidated.append(resource)


def test_request_honors_retry_after_and_refreshes_expired_token(tmp_path, monkeypatch) -> None:
    manager = PermissionMigrationManager(tmp_path, minimum_interval_seconds=0)
    manager._job = {"status": "running", "logs": [], "failures": []}
    responses = iter([
        urllib.error.HTTPError("https://example.test", 429, "limited", {"Retry-After": "7"}, io.BytesIO(b"")),
        urllib.error.HTTPError("https://example.test", 401, "expired", {}, io.BytesIO(b"")),
        FakeResponse(),
    ])
    waits = []
    provider = FakeTokenProvider()

    def fake_urlopen(request, timeout):
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr("server.permission_migration.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr(manager, "_wait", lambda seconds, reason: waits.append((seconds, reason)))

    status, body = manager._request("GET", "https://example.test", "resource", provider)

    assert (status, body) == (200, {})
    assert (7.0, "retry") in waits
    assert provider.invalidated == ["resource"]


def test_cancel_interrupts_wait(tmp_path) -> None:
    manager = PermissionMigrationManager(tmp_path, minimum_interval_seconds=0)
    manager._job = {"status": "running", "logs": [], "failures": []}
    manager._cancel.set()

    with pytest.raises(InterruptedError, match="cancelled"):
        manager._wait(60, "retry")


def test_dataset_operation_uses_additive_power_bi_grant(tmp_path, monkeypatch) -> None:
    manager = PermissionMigrationManager(tmp_path, minimum_interval_seconds=0)
    requests = []
    monkeypatch.setattr(manager, "_request", lambda *args: requests.append(args) or (200, None))
    operation = {
        "kind": "datasetRight",
        "workspaceId": "workspace-1",
        "artifactId": "dataset-1",
        "targetUserPrincipalName": "target@example.com",
        "right": "Read",
    }

    assert manager._execute_operation(operation, FakeTokenProvider()) == "applied"
    assert requests == [(
        "POST",
        "https://api.powerbi.com/v1.0/myorg/groups/workspace-1/datasets/dataset-1/users",
        "https://analysis.windows.net/powerbi/api",
        ANY,
        {"identifier": "target@example.com", "principalType": "User", "datasetUserAccessRight": "Read"},
    )]