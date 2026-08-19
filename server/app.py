import json
import math
import re
import sqlite3
from collections.abc import Generator
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .database import DEFAULT_DATABASE, ROOT, connect
from .scan_jobs import scan_manager


WEB_ROOT = ROOT / "web"
app = FastAPI(title="Fabric Access Atlas API", version="1.0.0")


def get_database() -> Generator[sqlite3.Connection, None, None]:
    if not DEFAULT_DATABASE.exists():
        raise HTTPException(status_code=503, detail="Snapshot database is not available. Run server/import_snapshot.py first.")
    connection = connect(DEFAULT_DATABASE, readonly=True)
    try:
        yield connection
    finally:
        connection.close()


Database = Annotated[sqlite3.Connection, Depends(get_database)]


class ScanRequest(BaseModel):
    tenant_id: str = Field(alias="tenantId", min_length=3, max_length=100, pattern=r"^[0-9a-fA-F-]+$")
    workspace_limit: int = Field(default=0, alias="workspaceLimit", ge=0, le=100000)
    include_personal_workspaces: bool = Field(default=False, alias="includePersonalWorkspaces")
    include_power_bi_artifact_users: bool = Field(default=True, alias="includePowerBIArtifactUsers")


def rows(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    return [dict(row) for row in cursor.fetchall()]


@app.get("/api/scans/current")
def current_scan() -> dict[str, Any]:
    return scan_manager.status()


@app.post("/api/scans", status_code=202)
def start_scan(request: ScanRequest) -> dict[str, Any]:
    try:
        return scan_manager.start(
            request.tenant_id,
            request.workspace_limit,
            request.include_personal_workspaces,
            request.include_power_bi_artifact_users,
        )
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def fts_query(value: str) -> str:
    terms = re.findall(r"[\w@.#-]+", value, flags=re.UNICODE)
    return " AND ".join(f'"{term.replace(chr(34), chr(34) * 2)}"*' for term in terms[:8])


@app.get("/api/health")
def health(database: Database) -> dict[str, Any]:
    return {
        "status": "ok",
        "integrity": database.execute("PRAGMA quick_check").fetchone()[0],
        "snapshotImportedAtUtc": database.execute("SELECT value FROM metadata WHERE key = 'importedAtUtc'").fetchone()[0],
    }


@app.get("/api/summary")
def summary(database: Database) -> dict[str, Any]:
    counts = database.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM workspaces) AS workspaces,
            (SELECT COUNT(*) FROM artifacts) AS artifacts,
            (SELECT COUNT(*) FROM principals) AS principals,
            (SELECT COUNT(*) FROM item_permissions) + (SELECT COUNT(*) FROM workspace_roles) AS assignments,
            (SELECT COUNT(DISTINCT type) FROM artifacts) AS artifactTypes
        """
    ).fetchone()
    principal_counts = rows(database.execute(
        """
        SELECT p.id, p.display_name AS principalName, p.email AS principalEmail, COUNT(*) AS count
        FROM item_permissions ip JOIN principals p ON p.id = ip.principal_id
        GROUP BY p.id ORDER BY count DESC, p.display_name LIMIT 6
        """
    ))
    type_counts = rows(database.execute(
        "SELECT type, COUNT(*) AS count FROM artifacts GROUP BY type ORDER BY count DESC, type LIMIT 7"
    ))
    recent_items = rows(database.execute(
        """
        SELECT a.id, a.name, a.type, a.modified_at AS modified, w.name AS workspaceName
        FROM artifacts a JOIN workspaces w ON w.id = a.workspace_id
        WHERE a.modified_at IS NOT NULL ORDER BY a.modified_at DESC LIMIT 6
        """
    ))
    coverage_row = database.execute("SELECT value FROM metadata WHERE key = 'coverage'").fetchone()
    coverage = json.loads(coverage_row[0]) if coverage_row else {}
    return {"counts": dict(counts), "principalCounts": principal_counts, "typeCounts": type_counts, "recentItems": recent_items, "generatedAtUtc": coverage.get("generatedAtUtc")}


@app.get("/api/facets")
def facets(database: Database) -> dict[str, Any]:
    return {
        "workspaces": rows(database.execute("SELECT id, name FROM workspaces ORDER BY name COLLATE NOCASE")),
        "artifactTypes": [row[0] for row in database.execute("SELECT DISTINCT type FROM artifacts ORDER BY type COLLATE NOCASE")],
        "accessRights": [row[0] for row in database.execute("SELECT DISTINCT access_right FROM item_permissions ORDER BY access_right COLLATE NOCASE")],
    }


@app.get("/api/permissions")
def permissions(
    database: Database,
    q: str = Query(default="", max_length=200),
    workspace_id: str = Query(default="", alias="workspaceId", max_length=50),
    artifact_type: str = Query(default="", alias="artifactType", max_length=100),
    access_right: str = Query(default="", alias="accessRight", max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, alias="pageSize", ge=10, le=100),
) -> dict[str, Any]:
    joins = """
        FROM item_permissions ip
        JOIN artifacts a ON a.id = ip.artifact_id
        JOIN workspaces w ON w.id = ip.workspace_id
        JOIN principals p ON p.id = ip.principal_id
    """
    conditions: list[str] = []
    parameters: list[Any] = []
    search = fts_query(q)
    if search:
        joins += " JOIN permission_search ps ON ps.rowid = ip.id"
        conditions.append("permission_search MATCH ?")
        parameters.append(search)
    if workspace_id:
        conditions.append("ip.workspace_id = ?")
        parameters.append(workspace_id)
    if artifact_type:
        conditions.append("a.type = ?")
        parameters.append(artifact_type)
    if access_right:
        conditions.append("ip.access_right = ?")
        parameters.append(access_right)
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""

    total = database.execute(f"SELECT COUNT(*) {joins}{where}", parameters).fetchone()[0]
    query = f"""
        SELECT ip.id, p.id AS principalId, p.display_name AS principalName, p.email AS principalEmail,
               p.principal_type AS principalType, w.id AS workspaceId, w.name AS workspaceName,
               a.id AS artifactId, a.name AS artifactName, a.type AS artifactType,
               a.state AS artifactState, ip.access_right AS access
        {joins}{where}
        ORDER BY p.display_name COLLATE NOCASE, w.name COLLATE NOCASE, a.name COLLATE NOCASE, ip.id
        LIMIT ? OFFSET ?
    """
    items = rows(database.execute(query, [*parameters, page_size, (page - 1) * page_size]))
    return {"items": items, "page": page, "pageSize": page_size, "total": total, "totalPages": max(1, math.ceil(total / page_size))}


@app.get("/api/workspaces")
def workspaces(
    database: Database,
    q: str = Query(default="", max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, alias="pageSize", ge=6, le=100),
) -> dict[str, Any]:
    where = "WHERE w.name LIKE ? ESCAPE '\\'" if q else ""
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    parameters: list[Any] = [f"%{escaped}%"] if q else []
    total = database.execute(f"SELECT COUNT(*) FROM workspaces w {where}", parameters).fetchone()[0]
    items = rows(database.execute(
        f"""
         SELECT w.id, w.name, w.type, w.state, w.capacity_id AS capacityId,
             (SELECT COUNT(*) FROM artifacts WHERE workspace_id = w.id) AS artifacts,
             (SELECT COUNT(*) FROM (
                  SELECT principal_id FROM item_permissions WHERE workspace_id = w.id
                  UNION SELECT principal_id FROM workspace_roles WHERE workspace_id = w.id
             )) AS principals,
             (SELECT COUNT(*) FROM workspace_roles WHERE workspace_id = w.id) AS roles
        FROM workspaces w
        {where}
         ORDER BY w.name COLLATE NOCASE LIMIT ? OFFSET ?
        """,
        [*parameters, page_size, (page - 1) * page_size],
    ))
    return {"items": items, "page": page, "pageSize": page_size, "total": total, "totalPages": max(1, math.ceil(total / page_size))}


@app.get("/api/workspaces/{workspace_id}")
def workspace_detail(workspace_id: str, database: Database) -> dict[str, Any]:
    workspace = database.execute("SELECT id, name, type, state, capacity_id AS capacityId FROM workspaces WHERE id = ?", (workspace_id,)).fetchone()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    roles = rows(database.execute(
        """
        SELECT p.id AS principalId, p.display_name AS displayName, p.email, p.principal_type AS principalType, wr.role
        FROM workspace_roles wr JOIN principals p ON p.id = wr.principal_id
        WHERE wr.workspace_id = ? ORDER BY p.display_name COLLATE NOCASE
        """,
        (workspace_id,),
    ))
    types = rows(database.execute(
        "SELECT type, COUNT(*) AS count FROM artifacts WHERE workspace_id = ? GROUP BY type ORDER BY count DESC, type",
        (workspace_id,),
    ))
    counts = database.execute(
        """
        SELECT (SELECT COUNT(*) FROM artifacts WHERE workspace_id = ?) AS artifacts,
               (SELECT COUNT(DISTINCT principal_id) FROM item_permissions WHERE workspace_id = ?) AS itemPrincipals,
               (SELECT COUNT(*) FROM workspace_roles WHERE workspace_id = ?) AS roles
        """,
        (workspace_id, workspace_id, workspace_id),
    ).fetchone()
    return {"workspace": dict(workspace), "counts": dict(counts), "roles": roles, "artifactTypes": types}


@app.get("/api/coverage")
def coverage(database: Database) -> dict[str, Any]:
    row = database.execute("SELECT value FROM metadata WHERE key = 'coverage'").fetchone()
    return json.loads(row[0]) if row else {"covered": [], "notCovered": [], "apiNotes": []}


app.mount("/assets", StaticFiles(directory=WEB_ROOT), name="assets")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/web/", include_in_schema=False)
def dashboard_legacy_path() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")