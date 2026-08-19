from fastapi.testclient import TestClient

from server.app import app


client = TestClient(app)


def test_health_and_summary() -> None:
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["integrity"] == "ok"

    summary = client.get("/api/summary").json()
    assert summary["counts"] == {
        "workspaces": 5,
        "artifacts": 48,
        "principals": 2,
        "assignments": 81,
        "artifactTypes": 17,
    }


def test_permission_pagination_and_search() -> None:
    first_page = client.get("/api/permissions", params={"pageSize": 10}).json()
    assert first_page["total"] == 75
    assert len(first_page["items"]) == 10
    assert first_page["totalPages"] == 8

    filtered = client.get("/api/permissions", params={"q": "Sheng", "pageSize": 100}).json()
    assert filtered["total"] == 29
    assert all("Sheng" in item["principalName"] for item in filtered["items"])


def test_workspaces_and_details() -> None:
    workspaces = client.get("/api/workspaces", params={"pageSize": 6}).json()
    assert workspaces["total"] == 5
    workspace_id = workspaces["items"][0]["id"]
    detail = client.get(f"/api/workspaces/{workspace_id}")
    assert detail.status_code == 200
    assert detail.json()["workspace"]["id"] == workspace_id