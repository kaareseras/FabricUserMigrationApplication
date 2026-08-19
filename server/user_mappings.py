import json
import sqlite3
import subprocess
import urllib.parse
import urllib.request
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Any

from .azure_auth import find_azure_cli
from .database import ROOT


DEFAULT_MAPPING_DATABASE = ROOT / "data" / "user-mappings.db"
GRAPH_USERS_URL = "https://graph.microsoft.com/v1.0/users"
MAPPING_SCHEMA = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS directory_users (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    user_principal_name TEXT NOT NULL,
    mail TEXT,
    user_type TEXT,
    account_enabled INTEGER NOT NULL,
    PRIMARY KEY (tenant_id, id)
);

CREATE TABLE IF NOT EXISTS user_mappings (
    tenant_id TEXT NOT NULL,
    source_user_id TEXT NOT NULL,
    target_user_id TEXT NOT NULL,
    created_at_utc TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (tenant_id, source_user_id),
    UNIQUE (tenant_id, target_user_id),
    FOREIGN KEY (tenant_id, source_user_id) REFERENCES directory_users(tenant_id, id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id, target_user_id) REFERENCES directory_users(tenant_id, id) ON DELETE CASCADE,
    CHECK (source_user_id <> target_user_id)
);

CREATE INDEX IF NOT EXISTS idx_directory_users_name
ON directory_users(tenant_id, display_name COLLATE NOCASE);
"""


def connect_mapping_database(database_path: Path = DEFAULT_MAPPING_DATABASE) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.executescript(MAPPING_SCHEMA)
    return connection


def _graph_pages(tenant_id: str) -> Iterator[dict[str, Any]]:
    cli = find_azure_cli()
    if cli is None:
        raise RuntimeError("Azure CLI is not installed on the server.")
    result = subprocess.run(
        [cli, "account", "get-access-token", "--tenant", tenant_id, "--resource-type", "ms-graph", "--output", "json"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Could not acquire a Microsoft Graph token for the tenant.")
    try:
        token = json.loads(result.stdout)["accessToken"]
    except (json.JSONDecodeError, KeyError) as error:
        raise RuntimeError("Azure CLI returned an invalid Microsoft Graph token response.") from error

    query = urllib.parse.urlencode({"$select": "id,displayName,userPrincipalName,mail,userType,accountEnabled", "$top": "999"})
    url: str | None = f"{GRAPH_USERS_URL}?{query}"
    while url:
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                page = json.load(response)
        except Exception as error:
            raise RuntimeError(f"Microsoft Graph user discovery failed: {error}") from error
        yield from page.get("value") or []
        url = page.get("@odata.nextLink")


def sync_directory_users(tenant_id: str, database_path: Path = DEFAULT_MAPPING_DATABASE) -> int:
    users = [user for user in _graph_pages(tenant_id) if user.get("id")]
    current_user_ids = {user["id"] for user in users}
    with closing(connect_mapping_database(database_path)) as connection:
        connection.execute("BEGIN")
        connection.executemany(
            """
            INSERT INTO directory_users(
                tenant_id, id, display_name, user_principal_name, mail, user_type, account_enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tenant_id, id) DO UPDATE SET
                display_name = excluded.display_name,
                user_principal_name = excluded.user_principal_name,
                mail = excluded.mail,
                user_type = excluded.user_type,
                account_enabled = excluded.account_enabled
            """,
            [
                (
                    tenant_id,
                    user["id"],
                    user.get("displayName") or user.get("userPrincipalName") or "Unknown user",
                    user.get("userPrincipalName") or "",
                    user.get("mail") or "",
                    user.get("userType") or "",
                    int(user.get("accountEnabled", True)),
                )
                for user in users
            ],
        )
        stored_user_ids = {
            row[0]
            for row in connection.execute("SELECT id FROM directory_users WHERE tenant_id = ?", (tenant_id,))
        }
        connection.executemany(
            "DELETE FROM directory_users WHERE tenant_id = ? AND id = ?",
            [(tenant_id, user_id) for user_id in stored_user_ids - current_user_ids],
        )
        connection.commit()
    return len(users)


def fabric_user_ids(snapshot: sqlite3.Connection, directory_users: list[sqlite3.Row]) -> set[str]:
    principals = snapshot.execute(
        """
        SELECT DISTINCT p.id, lower(p.email) AS email
        FROM principals p
        WHERE p.principal_type = 'User'
          AND (EXISTS (SELECT 1 FROM item_permissions ip WHERE ip.principal_id = p.id)
               OR EXISTS (SELECT 1 FROM workspace_roles wr WHERE wr.principal_id = p.id))
        """
    ).fetchall()
    principal_ids = {row["id"].casefold() for row in principals if row["id"]}
    principal_emails = {row["email"] for row in principals if row["email"]}
    return {
        user["id"]
        for user in directory_users
        if user["id"].casefold() in principal_ids
        or user["user_principal_name"].casefold() in principal_emails
        or (user["mail"] and user["mail"].casefold() in principal_emails)
    }


def mapping_view(tenant_id: str, snapshot: sqlite3.Connection, database_path: Path = DEFAULT_MAPPING_DATABASE) -> dict[str, Any]:
    with closing(connect_mapping_database(database_path)) as connection:
        directory_users = connection.execute(
            "SELECT * FROM directory_users WHERE tenant_id = ? ORDER BY display_name COLLATE NOCASE, user_principal_name COLLATE NOCASE",
            (tenant_id,),
        ).fetchall()
        presence_ids = fabric_user_ids(snapshot, directory_users)
        mappings = {
            row["source_user_id"]: row["target_user_id"]
            for row in connection.execute("SELECT source_user_id, target_user_id FROM user_mappings WHERE tenant_id = ?", (tenant_id,))
        }
        target_owners = {target_id: source_id for source_id, target_id in mappings.items()}

    def user_payload(user: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": user["id"],
            "displayName": user["display_name"],
            "userPrincipalName": user["user_principal_name"],
            "mail": user["mail"],
            "userType": user["user_type"],
            "accountEnabled": bool(user["account_enabled"]),
        }

    return {
        "tenantId": tenant_id,
        "directoryUserCount": len(directory_users),
        "sourceUsers": [{**user_payload(user), "targetUserId": mappings.get(user["id"])} for user in directory_users if user["id"] in presence_ids],
        "targetUsers": [
            {**user_payload(user), "mappedSourceUserId": target_owners.get(user["id"])}
            for user in directory_users
            if user["id"] not in presence_ids
        ],
    }


def set_user_mapping(
    tenant_id: str,
    source_user_id: str,
    target_user_id: str,
    snapshot: sqlite3.Connection,
    database_path: Path = DEFAULT_MAPPING_DATABASE,
) -> None:
    view = mapping_view(tenant_id, snapshot, database_path)
    source_ids = {user["id"] for user in view["sourceUsers"]}
    target_ids = {user["id"] for user in view["targetUsers"]}
    if source_user_id not in source_ids:
        raise ValueError("Source user is not a tenant user with Fabric presence.")
    if target_user_id not in target_ids:
        raise ValueError("Target user is not a tenant user without Fabric presence.")
    try:
        with closing(connect_mapping_database(database_path)) as connection:
            connection.execute(
                """
                INSERT INTO user_mappings(tenant_id, source_user_id, target_user_id)
                VALUES (?, ?, ?)
                ON CONFLICT(tenant_id, source_user_id) DO UPDATE SET target_user_id = excluded.target_user_id, created_at_utc = datetime('now')
                """,
                (tenant_id, source_user_id, target_user_id),
            )
            connection.commit()
    except sqlite3.IntegrityError as error:
        raise ValueError("Target user is already mapped to another source user.") from error


def delete_user_mapping(tenant_id: str, source_user_id: str, database_path: Path = DEFAULT_MAPPING_DATABASE) -> None:
    with closing(connect_mapping_database(database_path)) as connection:
        connection.execute("DELETE FROM user_mappings WHERE tenant_id = ? AND source_user_id = ?", (tenant_id, source_user_id))
        connection.commit()