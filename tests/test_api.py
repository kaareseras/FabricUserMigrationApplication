"""API tests against a synthetic snapshot (see conftest.api_client).

These tests are hermetic: they import the fixture snapshot into a throwaway
database and never touch the gitignored artifacts/ folder or data/ database.
"""


def test_health_and_summary(api_client) -> None:
    health = api_client.client.get("/api/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ok"
    assert body["integrity"] == "ok"
    assert body["snapshotImportedAtUtc"]

    summary = api_client.client.get("/api/summary").json()
    assert summary["counts"] == {
        "workspaces": 5,
        "artifacts": 10,
        "principals": 15,
        "assignments": 25,  # 21 item permissions + 4 workspace roles
        "artifactTypes": 3,
    }

    principal_counts = summary["principalCounts"]
    assert [entry["principalName"] for entry in principal_counts] == [
        "Astrid Holm", "Bjarne Kold", "Lars Sheng", "Mette Sorensen", "Nikolai Vest", "Olga Brandt"
    ]
    assert principal_counts[0]["count"] == 4

    assert summary["typeCounts"] == [
        {"type": "datasets", "count": 5},
        {"type": "reports", "count": 3},
        {"type": "dashboards", "count": 2},
    ]

    recent = summary["recentItems"]
    assert len(recent) == 6
    assert recent[0]["id"] == "d-1"
    assert recent[0]["name"] == "Budget model"
    assert recent[0]["workspaceName"] == "Finance"

    assert summary["generatedAtUtc"] == "2024-06-01T12:00:00Z"


def test_permission_pagination_and_search(api_client) -> None:
    client = api_client.client

    first_page = client.get("/api/permissions", params={"pageSize": 10}).json()
    assert first_page["total"] == 21
    assert len(first_page["items"]) == 10
    assert first_page["page"] == 1
    assert first_page["totalPages"] == 3

    last_page = client.get("/api/permissions", params={"pageSize": 10, "page": 3}).json()
    assert len(last_page["items"]) == 1

    searched = client.get("/api/permissions", params={"q": "Sheng"}).json()
    assert searched["total"] == 2
    assert all("Sheng" in item["principalName"] for item in searched["items"])
    assert {item["artifactId"] for item in searched["items"]} == {"d-1", "b-1"}

    admins = client.get("/api/permissions", params={"accessRight": "Admin"}).json()
    assert admins["total"] == 2

    finance = client.get("/api/permissions", params={"workspaceId": "ws-1"}).json()
    assert finance["total"] == 7


def test_workspaces_and_details(api_client) -> None:
    client = api_client.client

    listing = client.get("/api/workspaces", params={"pageSize": 6}).json()
    assert listing["total"] == 5
    assert [item["name"] for item in listing["items"]] == ["Archive", "Finance", "HR", "Marketing", "Sales"]

    finance_row = next(item for item in listing["items"] if item["id"] == "ws-1")
    assert finance_row["artifacts"] == 3
    assert finance_row["principals"] == 7  # 6 artifact users + Camilla (role only)
    assert finance_row["roles"] == 2

    detail = client.get("/api/workspaces/ws-1").json()
    assert detail["workspace"]["name"] == "Finance"
    assert detail["counts"] == {"artifacts": 3, "itemPrincipals": 6, "roles": 2}
    assert detail["artifactTypes"] == [
        {"type": "datasets", "count": 2},
        {"type": "reports", "count": 1},
    ]
    assert [(role["displayName"], role["role"]) for role in detail["roles"]] == [
        ("Astrid Holm", "Admin"),
        ("Camilla Vest", "Member"),
    ]

    missing = client.get("/api/workspaces/does-not-exist")
    assert missing.status_code == 404


def test_facets_and_coverage(api_client) -> None:
    facets = api_client.client.get("/api/facets").json()
    assert [item["name"] for item in facets["workspaces"]] == ["Archive", "Finance", "HR", "Marketing", "Sales"]
    assert facets["artifactTypes"] == ["dashboards", "datasets", "reports"]
    assert facets["accessRights"] == ["Admin", "Read"]

    coverage = api_client.client.get("/api/coverage").json()
    assert coverage["covered"] == ["workspaces", "artifacts"]
    assert coverage["notCovered"] == ["personal workspaces"]
    assert coverage["apiNotes"] == ["synthetic test fixture"]
