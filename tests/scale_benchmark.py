import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient

import server.app as app_module
from server.database import SCHEMA, connect


USERS = 10_000
WORKSPACES = 100
ARTIFACTS = 10_000
PERMISSIONS_PER_USER = 10


def build_database(path: Path) -> None:
    connection = connect(path)
    connection.executescript(SCHEMA)
    connection.execute("INSERT INTO metadata(key, value) VALUES ('coverage', '{}')")
    connection.execute("INSERT INTO metadata(key, value) VALUES ('importedAtUtc', datetime('now'))")

    connection.executemany(
        "INSERT INTO workspaces(id, name, type, state) VALUES (?, ?, 'Workspace', 'Active')",
        ((f"workspace-{index:04}", f"Workspace {index:04}") for index in range(WORKSPACES)),
    )
    connection.executemany(
        "INSERT INTO principals(id, display_name, email, principal_type, user_type) VALUES (?, ?, ?, 'User', 'Member')",
        ((f"user-{index:05}", f"User {index:05}", f"user{index:05}@example.com") for index in range(USERS)),
    )
    connection.executemany(
        "INSERT INTO artifacts(id, workspace_id, name, type, state, modified_at) VALUES (?, ?, ?, ?, 'Active', '2026-01-01T00:00:00Z')",
        (
            (f"artifact-{index:05}", f"workspace-{index % WORKSPACES:04}", f"Artifact {index:05}", "Notebook" if index % 2 else "Lakehouse")
            for index in range(ARTIFACTS)
        ),
    )

    permission_rows = []
    for user_index in range(USERS):
        for offset in range(PERMISSIONS_PER_USER):
            artifact_index = (user_index * PERMISSIONS_PER_USER + offset) % ARTIFACTS
            permission_rows.append(
                (f"artifact-{artifact_index:05}", f"workspace-{artifact_index % WORKSPACES:04}", f"user-{user_index:05}", "Read")
            )
        if len(permission_rows) >= 10_000:
            connection.executemany(
                "INSERT INTO item_permissions(artifact_id, workspace_id, principal_id, access_right) VALUES (?, ?, ?, ?)",
                permission_rows,
            )
            permission_rows.clear()
    if permission_rows:
        connection.executemany(
            "INSERT INTO item_permissions(artifact_id, workspace_id, principal_id, access_right) VALUES (?, ?, ?, ?)",
            permission_rows,
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
    connection.execute("ANALYZE")
    connection.commit()
    connection.close()


def timed_get(client: TestClient, path: str) -> tuple[float, dict]:
    started = time.perf_counter()
    response = client.get(path)
    elapsed = time.perf_counter() - started
    response.raise_for_status()
    return elapsed, response.json()


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="fabric-access-benchmark-") as directory:
        database_path = Path(directory) / "benchmark.db"
        started = time.perf_counter()
        build_database(database_path)
        build_seconds = time.perf_counter() - started

        original_database = app_module.DEFAULT_DATABASE
        app_module.DEFAULT_DATABASE = database_path
        try:
            client = TestClient(app_module.app)
            summary_seconds, summary = timed_get(client, "/api/summary")
            first_seconds, first = timed_get(client, "/api/permissions?page=1&pageSize=50")
            last_seconds, last = timed_get(client, "/api/permissions?page=2000&pageSize=50")
            search_seconds, search = timed_get(client, "/api/permissions?q=user09999&pageSize=50")
        finally:
            app_module.DEFAULT_DATABASE = original_database

        assert summary["counts"]["principals"] == USERS
        assert summary["counts"]["assignments"] == USERS * PERMISSIONS_PER_USER
        assert first["total"] == USERS * PERMISSIONS_PER_USER and len(first["items"]) == 50
        assert last["page"] == 2000 and len(last["items"]) == 50
        assert search["total"] == PERMISSIONS_PER_USER and len(search["items"]) == PERMISSIONS_PER_USER

        print(f"Built {USERS:,} users and {USERS * PERMISSIONS_PER_USER:,} permissions in {build_seconds:.2f}s")
        print(f"Summary: {summary_seconds * 1000:.1f}ms")
        print(f"First page: {first_seconds * 1000:.1f}ms")
        print(f"Last page: {last_seconds * 1000:.1f}ms")
        print(f"FTS user search: {search_seconds * 1000:.1f}ms")
        print("Maximum permission payload: 50 rows")


if __name__ == "__main__":
    main()