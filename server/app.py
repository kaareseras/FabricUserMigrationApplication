import json
import logging
import math
import re
import sqlite3
from collections.abc import Generator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, SecretStr

from .azure_auth import azure_auth_manager
from .database import DEFAULT_DATABASE, ROOT, connect
from .permission_migration import ACTIVE_STATUSES, build_permission_plan, permission_migration_manager
from .scan_jobs import scan_manager
from .security import configured_token, require_api_token
from .user_mappings import apply_user_mappings, delete_user_mapping, mapping_view, set_user_mapping, sync_directory_users


WEB_ROOT = ROOT / "web"


@asynccontextmanager
async def lifespan(_: FastAPI) -> Generator[None, None, None]:
    if configured_token() is None:
        logging.getLogger("fabric-access-atlas").warning(
            "%s is not set; mutating API endpoints are unauthenticated. Set it before exposing the app beyond 127.0.0.1.",
            "FABRIC_ATLAS_TOKEN",
        )
    yield


app = FastAPI(title="Fabric Access Atlas API", version="1.0.0", lifespan=lifespan)


def get_database() -> Generator[sqlite3.Connection, None, None]:
    if not DEFAULT_DATABASE.exists():
        raise HTTPException(status_code=503, detail="Snapshot database is not available. Run python -m server.import_snapshot first.")
    connection = connect(DEFAULT_DATABASE, readonly=True)
    try:
        yield connection
    finally:
        connection.close()


Database = Annotated[sqlite3.Connection, Depends(get_database)]
WorkspaceId = Annotated[str, Field(pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")]


class ScanRequest(BaseModel):
    tenant_id: str = Field(alias="tenantId", min_length=3, max_length=100, pattern=r"^[0-9a-fA-F-]+$")
    workspace_limit: int = Field(default=0, alias="workspaceLimit", ge=0, le=100000)
    workspace_ids: list[WorkspaceId] | None = Field(default=None, alias="workspaceIds", max_length=100000)
    include_personal_workspaces: bool = Field(default=False, alias="includePersonalWorkspaces")
    include_power_bi_artifact_users: bool = Field(default=True, alias="includePowerBIArtifactUsers")


class ServicePrincipalLoginRequest(BaseModel):
    tenant_id: str = Field(alias="tenantId", pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
    client_id: str = Field(alias="clientId", pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
    client_secret: SecretStr = Field(alias="clientSecret", min_length=1, max_length=4096)


class UserMappingRequest(BaseModel):
    target_user_id: str = Field(alias="targetUserId", min_length=1, max_length=200)


class UserMappingImportItem(BaseModel):
    source_user_id: str = Field(alias="sourceUserId", min_length=1, max_length=200)
    target_user_id: str | None = Field(default=None, alias="targetUserId", max_length=200)


class UserMappingImportRequest(BaseModel):
    mappings: list[UserMappingImportItem] = Field(max_length=100000)


class PermissionMigrationRequest(BaseModel):
    confirmed: bool


def rows(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    return [dict(row) for row in cursor.fetchall()]


@app.get("/api/auth/current")
def current_auth() -> dict[str, Any]:
    return azure_auth_manager.status()


@app.post("/api/auth/login", status_code=202, dependencies=[Depends(require_api_token)])
def start_login() -> dict[str, Any]:
    try:
        return azure_auth_manager.start()
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/auth/service-principal", dependencies=[Depends(require_api_token)])
def service_principal_login(request: ServicePrincipalLoginRequest) -> dict[str, Any]:
    try:
        return azure_auth_manager.login_service_principal(
            request.tenant_id,
            request.client_id,
            request.client_secret.get_secret_value(),
        )
    except RuntimeError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error


@app.delete("/api/auth/current", dependencies=[Depends(require_api_token)])
def logout() -> dict[str, Any]:
    try:
        return azure_auth_manager.logout()
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.get("/api/scans/current")
def current_scan() -> dict[str, Any]:
    return scan_manager.status()


@app.get("/api/scans/inventory")
def scan_inventory(
    tenant_id: Annotated[str, Query(alias="tenantId", min_length=3, max_length=100, pattern=r"^[0-9a-fA-F-]+$")],
    include_personal: Annotated[bool, Query(alias="includePersonalWorkspaces")] = False,
) -> dict[str, Any]:
    try:
        return azure_auth_manager.scan_inventory(tenant_id, include_personal)
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/scans", status_code=202, dependencies=[Depends(require_api_token)])
def start_scan(request: ScanRequest) -> dict[str, Any]:
    if permission_migration_manager.status()["status"] in ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail="A permission migration is running. Wait for it to finish or cancel it before scanning.")
    try:
        return scan_manager.start(
            request.tenant_id,
            request.workspace_limit,
            request.include_personal_workspaces,
            request.include_power_bi_artifact_users,
            request.workspace_ids,
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
    data = json.loads(row[0]) if row else {}
    return {
        "covered": data.get("covered") or [],
        "notCovered": data.get("notCovered") or [],
        "apiNotes": data.get("apiNotes") or [],
    }


@app.post("/api/tenants/{tenant_id}/directory-users/sync", dependencies=[Depends(require_api_token)])
def sync_tenant_directory(tenant_id: str) -> dict[str, Any]:
    try:
        count = sync_directory_users(tenant_id)
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {"tenantId": tenant_id, "userCount": count}


@app.get("/api/tenants/{tenant_id}/user-mappings")
def user_mappings(tenant_id: str, database: Database) -> dict[str, Any]:
    return mapping_view(tenant_id, database)


@app.put("/api/tenants/{tenant_id}/user-mappings", dependencies=[Depends(require_api_token)])
def import_user_mappings(tenant_id: str, request: UserMappingImportRequest, database: Database) -> dict[str, Any]:
    try:
        apply_user_mappings(
            tenant_id,
            [(mapping.source_user_id, mapping.target_user_id) for mapping in request.mappings],
            database,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return mapping_view(tenant_id, database)


@app.put("/api/tenants/{tenant_id}/user-mappings/{source_user_id}", dependencies=[Depends(require_api_token)])
def update_user_mapping(tenant_id: str, source_user_id: str, request: UserMappingRequest, database: Database) -> dict[str, Any]:
    try:
        set_user_mapping(tenant_id, source_user_id, request.target_user_id, database)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return mapping_view(tenant_id, database)


@app.delete("/api/tenants/{tenant_id}/user-mappings/{source_user_id}", dependencies=[Depends(require_api_token)])
def remove_user_mapping(tenant_id: str, source_user_id: str, database: Database) -> dict[str, Any]:
    delete_user_mapping(tenant_id, source_user_id)
    return mapping_view(tenant_id, database)


@app.get("/api/tenants/{tenant_id}/permission-migration/plan")
def permission_migration_plan(tenant_id: str, database: Database) -> dict[str, Any]:
    return build_permission_plan(tenant_id, database)


@app.get("/api/permission-migrations/current")
def current_permission_migration() -> dict[str, Any]:
    return permission_migration_manager.status()


@app.post("/api/tenants/{tenant_id}/permission-migration", status_code=202, dependencies=[Depends(require_api_token)])
def start_permission_migration(tenant_id: str, request: PermissionMigrationRequest, database: Database) -> dict[str, Any]:
    if not request.confirmed:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required before permissions are written.")
    if scan_manager.status()["status"] in {"queued", "running", "importing"}:
        raise HTTPException(status_code=409, detail="A discovery scan is running. Wait for it to finish before applying permissions.")
    plan = build_permission_plan(tenant_id, database)
    try:
        return permission_migration_manager.start(tenant_id, plan)
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.delete("/api/permission-migrations/current", dependencies=[Depends(require_api_token)])
def cancel_permission_migration() -> dict[str, Any]:
    try:
        return permission_migration_manager.cancel()
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


app.mount("/assets", StaticFiles(directory=WEB_ROOT), name="assets")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/web/", include_in_schema=False)
def dashboard_legacy_path() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")