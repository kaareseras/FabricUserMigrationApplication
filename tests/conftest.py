"""Shared fixtures for hermetic API tests.

Builds a small synthetic discovery snapshot in a temporary directory, imports it
into a throwaway database with the real import_snapshot() code path, and points
the FastAPI app at that database. Tests therefore never depend on the gitignored
artifacts/ folder or the data/ database of a developer machine.
"""

import csv
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import server.app as app_module
from server.database import import_snapshot


WORKSPACES = [
    {"id": "ws-1", "name": "Finance", "type": "Common", "state": "Available", "capacityId": "cap-1"},
    {"id": "ws-2", "name": "Sales", "type": "Common", "state": "Available", "capacityId": "cap-1"},
    {"id": "ws-3", "name": "Marketing", "type": "Common", "state": "Available", "capacityId": "cap-2"},
    {"id": "ws-4", "name": "HR", "type": "Personal", "state": "Available"},
    {"id": "ws-5", "name": "Archive", "type": "Common", "state": "Restoring", "capacityId": "cap-2"},
]

USERS = {
    "u-1": ("Astrid Holm", "astrid.holm@example.com"),
    "u-2": ("Bjarne Kold", "bjarne.kold@example.com"),
    "u-3": ("Lars Sheng", "lars.sheng@example.com"),
    "u-4": ("Mette Sorensen", "mette.sorensen@example.com"),
    "u-5": ("Nikolai Vest", "nikolai.vest@example.com"),
    "u-6": ("Olga Brandt", "olga.brandt@example.com"),
    "u-7": ("Peter Dahl", "peter.dahl@example.com"),
    "u-8": ("Rikke Eriksen", "rikke.eriksen@example.com"),
    "u-9": ("Sune Friis", "sune.friis@example.com"),
    "u-10": ("Tina Grove", "tina.grove@example.com"),
    "u-11": ("Uffe Hald", "uffe.hald@example.com"),
    "u-12": ("Vibe Krogh", "vibe.krogh@example.com"),
    "u-13": ("William Lund", "william.lund@example.com"),
}


def _artifact(artifact_id: str, name: str, grants: list[tuple[str, str]], modified: str) -> dict:
    return {
        "id": artifact_id,
        "name": name,
        "state": "Available",
        "lastUpdatedDate": modified,
        "users": [
            {
                "graphId": user_id,
                "displayName": USERS[user_id][0],
                "emailAddress": USERS[user_id][1],
                "principalType": "User",
                "artifactUserAccessRight": access_right,
            }
            for user_id, access_right in grants
        ],
    }


def _workspace(index: int, **artifacts: list[dict]) -> dict:
    workspace = dict(WORKSPACES[index - 1])
    workspace.update(artifacts)
    return workspace


SCAN_WORKSPACES = [
    _workspace(
        1,
        datasets=[
            _artifact("d-1", "Budget model", [("u-1", "Read"), ("u-2", "Admin"), ("u-3", "Read")], "2024-06-05T08:00:00Z"),
            _artifact("d-2", "KPI feed", [("u-1", "Read"), ("u-4", "Read")], "2024-06-02T09:30:00Z"),
        ],
        reports=[_artifact("r-1", "Board deck", [("u-5", "Read"), ("u-6", "Read")], "2024-06-03T10:00:00Z")],
    ),
    _workspace(
        2,
        dashboards=[_artifact("b-1", "Pipeline board", [("u-1", "Read"), ("u-2", "Read"), ("u-3", "Read")], "2024-06-04T11:00:00Z")],
        datasets=[_artifact("d-3", "Deal data", [("u-4", "Admin")], "2024-05-30T12:00:00Z")],
    ),
    _workspace(
        3,
        reports=[_artifact("r-2", "Campaign review", [("u-5", "Read"), ("u-6", "Read"), ("u-7", "Read")], "2024-05-28T13:00:00Z")],
        dashboards=[_artifact("b-2", "Funnel board", [("u-1", "Read")], "2024-05-29T14:00:00Z")],
    ),
    _workspace(
        4,
        datasets=[_artifact("d-4", "Headcount model", [("u-8", "Read"), ("u-9", "Read")], "2024-05-27T15:00:00Z")],
        reports=[_artifact("r-3", "Attrition report", [("u-10", "Read")], "2024-05-26T16:00:00Z")],
    ),
    _workspace(
        5,
        datasets=[_artifact("d-5", "Legacy metrics", [("u-11", "Read"), ("u-12", "Read"), ("u-13", "Read")], "2024-05-25T17:00:00Z")],
    ),
]

ROLE_ASSIGNMENTS = [
    {"WorkspaceId": "ws-1", "PrincipalId": "u-1", "DisplayName": "Astrid Holm", "UserPrincipalName": "astrid.holm@example.com", "PrincipalType": "User", "WorkspaceRole": "Admin"},
    {"WorkspaceId": "ws-1", "PrincipalId": "u-14", "DisplayName": "Camilla Vest", "UserPrincipalName": "camilla.vest@example.com", "PrincipalType": "Group", "WorkspaceRole": "Member"},
    {"WorkspaceId": "ws-2", "PrincipalId": "u-3", "DisplayName": "Lars Sheng", "UserPrincipalName": "lars.sheng@example.com", "PrincipalType": "User", "WorkspaceRole": "Member"},
    {"WorkspaceId": "ws-5", "PrincipalId": "u-15", "DisplayName": "Archive Bot", "UserPrincipalName": "archive.bot@example.com", "PrincipalType": "ServicePrincipal", "WorkspaceRole": "Admin"},
]

COVERAGE = {
    "generatedAtUtc": "2024-06-01T12:00:00Z",
    "covered": ["workspaces", "artifacts"],
    "notCovered": ["personal workspaces"],
    "apiNotes": ["synthetic test fixture"],
}

# Ground truth for the synthetic snapshot above (see import_snapshot counts).
EXPECTED_IMPORT_COUNTS = {
    "workspaces": 5,
    "artifacts": 10,
    "principals": 15,
    "workspaceRoles": 4,
    "itemPermissions": 21,
}


@pytest.fixture(scope="session")
def snapshot_source(tmp_path_factory) -> Path:
    source = tmp_path_factory.mktemp("snapshot") / "fabric-permission-discovery"
    source.mkdir()
    (source / "workspaces.json").write_text(json.dumps(WORKSPACES), encoding="utf-8")
    with (source / "powerbi-artifact-user-scans.ndjson").open("w", encoding="utf-8") as stream:
        for workspace in SCAN_WORKSPACES:
            stream.write(json.dumps({"workspaces": [workspace]}) + "\n")
    fieldnames = ["WorkspaceId", "PrincipalId", "DisplayName", "UserPrincipalName", "PrincipalType", "WorkspaceRole"]
    with (source / "workspace-role-assignments.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ROLE_ASSIGNMENTS)
    (source / "coverage-report.json").write_text(json.dumps(COVERAGE), encoding="utf-8")
    return source


@pytest.fixture()
def api_client(snapshot_source: Path, tmp_path: Path, monkeypatch):
    """TestClient wired to a fresh database imported from the synthetic snapshot."""
    database_path = tmp_path / "fabric-access.db"
    counts = import_snapshot(source=snapshot_source, database_path=database_path)
    assert counts == EXPECTED_IMPORT_COUNTS, f"synthetic fixture drifted: {counts}"
    monkeypatch.setattr(app_module, "DEFAULT_DATABASE", database_path)
    client = TestClient(app_module.app)
    yield SimpleNamespace(client=client, counts=counts)
