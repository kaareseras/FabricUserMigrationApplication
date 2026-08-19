import csv
import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Any

import ijson


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "artifacts" / "fabric-permission-discovery"
DEFAULT_DATABASE = ROOT / "data" / "fabric-access.db"

META_FIELDS = {
    "id",
    "name",
    "type",
    "state",
    "capacityId",
    "domainId",
    "tags",
    "isOnDedicatedCapacity",
    "defaultDatasetStorageFormat",
    "description",
}

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT,
    state TEXT,
    capacity_id TEXT
);

CREATE TABLE principals (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    email TEXT,
    principal_type TEXT,
    user_type TEXT
);

CREATE TABLE artifacts (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    state TEXT,
    modified_at TEXT
);

CREATE TABLE workspace_roles (
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    principal_id TEXT NOT NULL REFERENCES principals(id),
    role TEXT NOT NULL,
    PRIMARY KEY (workspace_id, principal_id, role)
);

CREATE TABLE item_permissions (
    id INTEGER PRIMARY KEY,
    artifact_id TEXT NOT NULL REFERENCES artifacts(id),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    principal_id TEXT NOT NULL REFERENCES principals(id),
    access_right TEXT NOT NULL,
    UNIQUE (artifact_id, principal_id, access_right)
);

CREATE VIRTUAL TABLE permission_search USING fts5(
    principal_name,
    principal_email,
    workspace_name,
    artifact_name,
    artifact_type,
    access_right,
    tokenize = 'unicode61'
);

CREATE INDEX idx_artifacts_workspace ON artifacts(workspace_id);
CREATE INDEX idx_artifacts_type ON artifacts(type);
CREATE INDEX idx_artifacts_modified ON artifacts(modified_at DESC);
CREATE INDEX idx_permissions_workspace ON item_permissions(workspace_id);
CREATE INDEX idx_permissions_principal ON item_permissions(principal_id);
CREATE INDEX idx_permissions_artifact ON item_permissions(artifact_id);
CREATE INDEX idx_workspace_roles_principal ON workspace_roles(principal_id);
CREATE INDEX idx_principals_name ON principals(display_name COLLATE NOCASE);
CREATE INDEX idx_workspaces_name ON workspaces(name COLLATE NOCASE);
"""


def connect(database_path: Path = DEFAULT_DATABASE, readonly: bool = False) -> sqlite3.Connection:
    if readonly:
        connection = sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True, check_same_thread=False)
    else:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def iter_scan_workspaces(source: Path) -> Iterator[dict[str, Any]]:
    ndjson_path = source / "powerbi-artifact-user-scans.ndjson"
    if ndjson_path.exists():
        with ndjson_path.open("r", encoding="utf-8-sig") as stream:
            for line in stream:
                if not line.strip():
                    continue
                result = json.loads(line)
                yield from result.get("workspaces", [])
        return

    json_path = source / "powerbi-artifact-user-scans.json"
    if not json_path.exists():
        return
    with json_path.open("r", encoding="utf-8-sig") as stream:
        yield from ijson.items(stream, "item.workspaces.item")


def principal_from_user(user: dict[str, Any]) -> tuple[str, str, str, str, str]:
    principal_id = user.get("graphId") or user.get("identifier") or user.get("emailAddress")
    display_name = user.get("displayName") or user.get("emailAddress") or user.get("identifier") or "Unknown principal"
    email = user.get("emailAddress") or user.get("identifier") or ""
    return principal_id, display_name, email, user.get("principalType", "Unknown"), user.get("userType", "")


def import_snapshot(source: Path = DEFAULT_SOURCE, database_path: Path = DEFAULT_DATABASE) -> dict[str, int]:
    if not source.exists():
        raise FileNotFoundError(f"Discovery source does not exist: {source}")

    temporary_path = database_path.with_suffix(".importing.db")
    temporary_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path.unlink(missing_ok=True)

    counts = {"workspaces": 0, "artifacts": 0, "principals": 0, "workspaceRoles": 0, "itemPermissions": 0}
    with closing(connect(temporary_path)) as connection:
        connection.executescript(SCHEMA)
        coverage_path = source / "coverage-report.json"
        coverage = json.loads(coverage_path.read_text(encoding="utf-8-sig")) if coverage_path.exists() else {}
        connection.execute("INSERT INTO metadata(key, value) VALUES (?, ?)", ("coverage", json.dumps(coverage)))

        workspace_path = source / "workspaces.json"
        if workspace_path.exists():
            with workspace_path.open("r", encoding="utf-8-sig") as stream:
                for workspace in ijson.items(stream, "item"):
                    connection.execute(
                        "INSERT OR REPLACE INTO workspaces(id, name, type, state, capacity_id) VALUES (?, ?, ?, ?, ?)",
                        (workspace["id"], workspace.get("name", "Unnamed"), workspace.get("type"), workspace.get("state"), workspace.get("capacityId")),
                    )

        for workspace in iter_scan_workspaces(source):
            connection.execute(
                "INSERT OR REPLACE INTO workspaces(id, name, type, state, capacity_id) VALUES (?, ?, ?, ?, ?)",
                (workspace["id"], workspace.get("name", "Unnamed"), workspace.get("type"), workspace.get("state"), workspace.get("capacityId")),
            )
            for artifact_type, items in workspace.items():
                if artifact_type in META_FIELDS or not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict) or not item.get("id"):
                        continue
                    connection.execute(
                        "INSERT OR REPLACE INTO artifacts(id, workspace_id, name, type, state, modified_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            item["id"],
                            workspace["id"],
                            item.get("name", "Unnamed item"),
                            artifact_type,
                            item.get("state", "Unknown"),
                            item.get("lastUpdatedDate") or item.get("modifiedDateTime") or item.get("createdDate"),
                        ),
                    )
                    for user in item.get("users") or []:
                        principal = principal_from_user(user)
                        if not principal[0]:
                            continue
                        connection.execute(
                            "INSERT OR REPLACE INTO principals(id, display_name, email, principal_type, user_type) VALUES (?, ?, ?, ?, ?)",
                            principal,
                        )
                        connection.execute(
                            "INSERT OR IGNORE INTO item_permissions(artifact_id, workspace_id, principal_id, access_right) VALUES (?, ?, ?, ?)",
                            (item["id"], workspace["id"], principal[0], user.get("artifactUserAccessRight", "Read")),
                        )

        roles_path = source / "workspace-role-assignments.csv"
        if roles_path.exists():
            with roles_path.open("r", encoding="utf-8-sig", newline="") as stream:
                for role in csv.DictReader(stream):
                    principal_id = role.get("PrincipalId")
                    if not principal_id:
                        continue
                    connection.execute(
                        "INSERT OR REPLACE INTO principals(id, display_name, email, principal_type, user_type) VALUES (?, ?, ?, ?, ?)",
                        (principal_id, role.get("DisplayName") or "Unknown principal", role.get("UserPrincipalName") or "", role.get("PrincipalType") or "Unknown", ""),
                    )
                    connection.execute(
                        "INSERT OR IGNORE INTO workspace_roles(workspace_id, principal_id, role) VALUES (?, ?, ?)",
                        (role["WorkspaceId"], principal_id, role.get("WorkspaceRole") or "Unknown"),
                    )

        connection.execute(
            """
            INSERT INTO permission_search(rowid, principal_name, principal_email, workspace_name, artifact_name, artifact_type, access_right)
            SELECT ip.id, p.display_name, p.email, w.name, a.name, a.type, ip.access_right
            FROM item_permissions ip
            JOIN principals p ON p.id = ip.principal_id
            JOIN workspaces w ON w.id = ip.workspace_id
            JOIN artifacts a ON a.id = ip.artifact_id
            """
        )
        connection.execute("INSERT INTO metadata(key, value) VALUES (?, datetime('now'))", ("importedAtUtc",))
        connection.execute("ANALYZE")
        connection.commit()

        for key, table in (
            ("workspaces", "workspaces"),
            ("artifacts", "artifacts"),
            ("principals", "principals"),
            ("workspaceRoles", "workspace_roles"),
            ("itemPermissions", "item_permissions"),
        ):
            counts[key] = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    database_path.unlink(missing_ok=True)
    temporary_path.replace(database_path)
    return counts