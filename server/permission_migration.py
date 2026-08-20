import hashlib
import json
import sqlite3
import subprocess
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from contextlib import closing
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from .azure_auth import find_azure_cli
from .database import ROOT
from .user_mappings import DEFAULT_MAPPING_DATABASE, connect_mapping_database


FABRIC_RESOURCE = "https://api.fabric.microsoft.com"
POWER_BI_RESOURCE = "https://analysis.windows.net/powerbi/api"
FABRIC_API = "https://api.fabric.microsoft.com/v1"
POWER_BI_API = "https://api.powerbi.com/v1.0/myorg"
CHECKPOINT_DIRECTORY = ROOT / "data" / "permission-migrations"
SUPPORTED_WORKSPACE_ROLES = {"Admin", "Member", "Contributor", "Viewer"}
SUPPORTED_DATASET_RIGHTS = {"Read", "ReadReshare", "ReadExplore", "ReadReshareExplore"}
WORKSPACE_ROLE_COVERED_RIGHTS = {
    "Viewer": {"Read"},
    "Contributor": {"Read", "ReadWrite", "ReadWriteExecute", "ReadExplore"},
    "Member": {
        "Read", "ReadWrite", "ReadReshare", "ReadExplore", "ReadReshareExplore",
        "ReadWriteExecute", "ReadWriteReshare", "ReadWriteReshareExecute", "ReadWriteExplore",
        "ReadWriteReshareExplore",
    },
    "Admin": {
        "Read", "ReadWrite", "ReadReshare", "ReadExplore", "ReadCopy", "ReadReshareExplore",
        "ReadWriteExecute", "ReadWriteReshare", "ReadWriteReshareExecute", "ReadWriteExplore",
        "ReadWriteReshareExplore", "Owner",
    },
}
ACTIVE_STATUSES = {"queued", "running", "cancelling"}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def operation_id(operation: dict[str, Any]) -> str:
    identity = "|".join(
        str(operation.get(key) or "")
        for key in ("kind", "tenantId", "sourceUserId", "targetUserId", "workspaceId", "artifactId", "right")
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def build_permission_plan(
    tenant_id: str,
    snapshot: sqlite3.Connection,
    mapping_database_path: Path = DEFAULT_MAPPING_DATABASE,
) -> dict[str, Any]:
    with closing(connect_mapping_database(mapping_database_path)) as mappings:
        mapped_users = mappings.execute(
            """
            SELECT m.source_user_id, m.target_user_id,
                   source.user_principal_name AS source_upn,
                   target.user_principal_name AS target_upn,
                   source.mail AS source_mail,
                   target.mail AS target_mail,
                   source.display_name AS source_name,
                   target.display_name AS target_name
            FROM user_mappings m
            JOIN directory_users source ON source.tenant_id = m.tenant_id AND source.id = m.source_user_id
            JOIN directory_users target ON target.tenant_id = m.tenant_id AND target.id = m.target_user_id
            WHERE m.tenant_id = ?
            ORDER BY source.display_name COLLATE NOCASE
            """,
            (tenant_id,),
        ).fetchall()

    operations: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    covered_by_workspace_role: list[dict[str, Any]] = []
    for mapped_user in mapped_users:
        source_identifiers = {
            value.casefold()
            for value in (mapped_user["source_user_id"], mapped_user["source_upn"], mapped_user["source_mail"])
            if value
        }
        placeholders = ",".join("?" for _ in source_identifiers)
        if not placeholders:
            continue
        parameters = sorted(source_identifiers)
        workspace_roles = snapshot.execute(
            f"""
            SELECT DISTINCT wr.workspace_id, w.name AS workspace_name, wr.role
            FROM workspace_roles wr
            JOIN principals p ON p.id = wr.principal_id
            JOIN workspaces w ON w.id = wr.workspace_id
            WHERE lower(p.id) IN ({placeholders}) OR lower(p.email) IN ({placeholders})
            ORDER BY w.name COLLATE NOCASE, wr.role
            """,
            [*parameters, *parameters],
        ).fetchall()
        roles_by_workspace = {
            role["workspace_id"]: role["role"]
            for role in workspace_roles
            if role["role"] in SUPPORTED_WORKSPACE_ROLES
        }
        for role in workspace_roles:
            operation = {
                "kind": "workspaceRole",
                "tenantId": tenant_id,
                "sourceUserId": mapped_user["source_user_id"],
                "sourceUserName": mapped_user["source_name"],
                "targetUserId": mapped_user["target_user_id"],
                "targetUserName": mapped_user["target_name"],
                "targetUserPrincipalName": mapped_user["target_upn"] or mapped_user["target_mail"],
                "workspaceId": role["workspace_id"],
                "workspaceName": role["workspace_name"],
                "artifactId": None,
                "artifactName": None,
                "artifactType": None,
                "right": role["role"],
            }
            if role["role"] not in SUPPORTED_WORKSPACE_ROLES:
                unsupported.append({
                    **operation,
                    "reason": "This workspace role is not supported by the Fabric role-assignment API.",
                })
                continue
            operation["id"] = operation_id(operation)
            operations.append(operation)

        item_rights = snapshot.execute(
            f"""
            SELECT DISTINCT ip.workspace_id, w.name AS workspace_name,
                   ip.artifact_id, a.name AS artifact_name, a.type AS artifact_type,
                   ip.access_right
            FROM item_permissions ip
            JOIN principals p ON p.id = ip.principal_id
            JOIN workspaces w ON w.id = ip.workspace_id
            JOIN artifacts a ON a.id = ip.artifact_id
            WHERE lower(p.id) IN ({placeholders}) OR lower(p.email) IN ({placeholders})
            ORDER BY w.name COLLATE NOCASE, a.name COLLATE NOCASE, ip.access_right
            """,
            [*parameters, *parameters],
        ).fetchall()
        for item in item_rights:
            base = {
                "tenantId": tenant_id,
                "sourceUserId": mapped_user["source_user_id"],
                "sourceUserName": mapped_user["source_name"],
                "targetUserId": mapped_user["target_user_id"],
                "targetUserName": mapped_user["target_name"],
                "targetUserPrincipalName": mapped_user["target_upn"] or mapped_user["target_mail"],
                "workspaceId": item["workspace_id"],
                "workspaceName": item["workspace_name"],
                "artifactId": item["artifact_id"],
                "artifactName": item["artifact_name"],
                "artifactType": item["artifact_type"],
                "right": item["access_right"],
            }
            workspace_role = roles_by_workspace.get(item["workspace_id"])
            if item["artifact_type"].casefold() == "datasets" and item["access_right"] in SUPPORTED_DATASET_RIGHTS:
                operation = {"kind": "datasetRight", **base}
                operation["id"] = operation_id(operation)
                operations.append(operation)
            elif item["access_right"] in WORKSPACE_ROLE_COVERED_RIGHTS.get(workspace_role, set()):
                covered_by_workspace_role.append({**base, "workspaceRole": workspace_role})
            else:
                unsupported.append({
                    **base,
                    "reason": "The available Microsoft write APIs cannot reproduce this item type and access right exactly.",
                })

    operations.sort(key=lambda item: (item["workspaceName"].casefold(), item["kind"], (item["artifactName"] or "").casefold(), item["sourceUserName"].casefold()))
    return {
        "tenantId": tenant_id,
        "mappedUsers": len(mapped_users),
        "operations": operations,
        "unsupported": unsupported,
        "coveredByWorkspaceRole": covered_by_workspace_role,
        "counts": {
            "workspaceRoles": sum(operation["kind"] == "workspaceRole" for operation in operations),
            "datasetRights": sum(operation["kind"] == "datasetRight" for operation in operations),
            "coveredByWorkspaceRoles": len(covered_by_workspace_role),
            "unsupported": len(unsupported),
            "total": len(operations),
        },
    }


class AccessTokenProvider:
    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id
        self._tokens: dict[str, tuple[str, float]] = {}

    def invalidate(self, resource: str) -> None:
        self._tokens.pop(resource, None)

    def get(self, resource: str) -> str:
        cached = self._tokens.get(resource)
        if cached and cached[1] > time.monotonic() + 300:
            return cached[0]
        cli = find_azure_cli()
        if cli is None:
            raise RuntimeError("Azure CLI is not installed on the server.")
        result = subprocess.run(
            [cli, "account", "get-access-token", "--tenant", self.tenant_id, "--resource", resource, "--output", "json"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"Could not acquire an access token for {resource}.")
        try:
            token = json.loads(result.stdout)["accessToken"]
        except (json.JSONDecodeError, KeyError) as error:
            raise RuntimeError(f"Azure CLI returned an invalid token response for {resource}.") from error
        self._tokens[resource] = (token, time.monotonic() + 2700)
        return token


class PermissionMigrationManager:
    def __init__(self, checkpoint_directory: Path = CHECKPOINT_DIRECTORY, minimum_interval_seconds: float = 1.0) -> None:
        self.checkpoint_directory = checkpoint_directory
        self.minimum_interval_seconds = minimum_interval_seconds
        self._lock = threading.Lock()
        self._job: dict[str, Any] | None = None
        self._cancel = threading.Event()
        self._last_request_at = 0.0

    def status(self) -> dict[str, Any]:
        with self._lock:
            if self._job is None:
                return {"status": "idle", "progress": 0, "stage": "Klar til at anvende mappede rettigheder", "logs": []}
            return {**self._job, "logs": list(self._job["logs"]), "failures": list(self._job["failures"])}

    def start(self, tenant_id: str, plan: dict[str, Any]) -> dict[str, Any]:
        if not plan["operations"]:
            raise RuntimeError("The migration plan has no supported permission operations.")
        if find_azure_cli() is None:
            raise RuntimeError("Azure CLI is not installed on the server.")
        with self._lock:
            if self._job and self._job["status"] in ACTIVE_STATUSES:
                raise RuntimeError("A permission migration is already running.")
            self._cancel.clear()
            self._job = {
                "status": "queued",
                "tenantId": tenant_id,
                "progress": 0,
                "stage": "Forbereder rettighedsmigration",
                "startedAtUtc": utc_now(),
                "completedAtUtc": None,
                "current": 0,
                "total": len(plan["operations"]),
                "logs": [],
                "failures": [],
                "wait": None,
                "planCounts": plan["counts"],
                "result": None,
            }
        threading.Thread(target=self._run, args=(tenant_id, plan), daemon=True).start()
        return self.status()

    def cancel(self) -> dict[str, Any]:
        with self._lock:
            if not self._job or self._job["status"] not in ACTIVE_STATUSES:
                raise RuntimeError("No permission migration is running.")
            self._job["status"] = "cancelling"
            self._job["stage"] = "Anullerer efter nuværende anmodning"
        self._cancel.set()
        return self.status()

    def _update(self, **values: Any) -> None:
        with self._lock:
            if self._job is not None:
                self._job.update(values)

    def _append_log(self, message: str) -> None:
        with self._lock:
            if self._job is not None:
                self._job["logs"] = [*self._job["logs"], message][-200:]

    def _append_failure(self, operation: dict[str, Any], error: Exception) -> None:
        failure = {"operationId": operation["id"], "kind": operation["kind"], "workspaceName": operation["workspaceName"], "artifactName": operation["artifactName"], "targetUserName": operation["targetUserName"], "error": str(error)}
        with self._lock:
            if self._job is not None:
                self._job["failures"] = [*self._job["failures"], failure]

    def _checkpoint_path(self, tenant_id: str) -> Path:
        safe_tenant_id = "".join(character for character in tenant_id if character.isalnum() or character == "-")
        return self.checkpoint_directory / f"{safe_tenant_id}.checkpoint.ndjson"

    def _load_completed(self, tenant_id: str) -> set[str]:
        path = self._checkpoint_path(tenant_id)
        if not path.exists():
            return set()
        completed: set[str] = set()
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
                if record.get("tenantId") == tenant_id and record.get("operationId"):
                    completed.add(record["operationId"])
            except json.JSONDecodeError:
                self._append_log("Ignoring an incomplete checkpoint line.")
        return completed

    def _save_checkpoint(self, tenant_id: str, operation: dict[str, Any], outcome: str) -> None:
        path = self._checkpoint_path(tenant_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"tenantId": tenant_id, "operationId": operation["id"], "outcome": outcome, "completedAtUtc": utc_now()}, separators=(",", ":")) + "\n")
            stream.flush()

    def _retry_after(self, error: urllib.error.HTTPError, attempt: int) -> float:
        value = error.headers.get("Retry-After") if error.headers else None
        if value:
            try:
                return max(1.0, float(value))
            except ValueError:
                try:
                    return max(1.0, (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds())
                except (TypeError, ValueError):
                    pass
        return min(300.0, 2 ** attempt)

    def _wait(self, seconds: float, reason: str) -> None:
        seconds = max(0.0, seconds)
        if seconds <= 0:
            return
        next_call = datetime.fromtimestamp(time.time() + seconds, UTC).isoformat()
        self._update(wait={"reason": reason, "seconds": round(seconds, 1), "nextCallAtUtc": next_call})
        if self._cancel.wait(seconds):
            raise InterruptedError("Permission migration cancelled.")
        self._update(wait=None)

    def _request(self, method: str, url: str, resource: str, token_provider: AccessTokenProvider, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any] | None]:
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        for attempt in range(1, 9):
            elapsed = time.monotonic() - self._last_request_at
            self._wait(max(0.0, self.minimum_interval_seconds - elapsed), "pacing")
            request = urllib.request.Request(
                url,
                data=payload,
                method=method,
                headers={"Authorization": f"Bearer {token_provider.get(resource)}", "Content-Type": "application/json"},
            )
            try:
                self._last_request_at = time.monotonic()
                with urllib.request.urlopen(request, timeout=60) as response:
                    response_body = response.read()
                    return response.status, json.loads(response_body) if response_body else None
            except urllib.error.HTTPError as error:
                if error.code == 401 and attempt < 8:
                    token_provider.invalidate(resource)
                    continue
                if error.code == 409:
                    raise
                if error.code == 429 or 500 <= error.code < 600:
                    if attempt < 8:
                        delay = self._retry_after(error, attempt)
                        self._append_log(f"HTTP {error.code}; retry {attempt}/8 in {delay:.0f}s.")
                        self._wait(delay, "retry")
                        continue
                detail = error.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"HTTP {error.code}: {detail or error.reason}") from error
            except (TimeoutError, urllib.error.URLError) as error:
                if attempt < 8:
                    delay = min(300.0, 2 ** attempt)
                    self._append_log(f"Temporary network error; retry {attempt}/8 in {delay:.0f}s.")
                    self._wait(delay, "retry")
                    continue
                raise RuntimeError(f"Network request failed after 8 attempts: {error}") from error
        raise RuntimeError("Request failed after 8 attempts.")

    def _workspace_role_matches(self, operation: dict[str, Any], token_provider: AccessTokenProvider) -> bool:
        url: str | None = f"{FABRIC_API}/workspaces/{operation['workspaceId']}/roleAssignments"
        while url:
            _, response = self._request("GET", url, FABRIC_RESOURCE, token_provider)
            response = response or {}
            for assignment in response.get("value") or []:
                if assignment.get("principal", {}).get("id") == operation["targetUserId"]:
                    return assignment.get("role") == operation["right"]
            url = response.get("continuationUri")
        return False

    def _execute_operation(self, operation: dict[str, Any], token_provider: AccessTokenProvider) -> str:
        if operation["kind"] == "workspaceRole":
            try:
                self._request(
                    "POST",
                    f"{FABRIC_API}/workspaces/{operation['workspaceId']}/roleAssignments",
                    FABRIC_RESOURCE,
                    token_provider,
                    {"principal": {"id": operation["targetUserId"], "type": "User"}, "role": operation["right"]},
                )
                return "applied"
            except urllib.error.HTTPError as error:
                if error.code == 409 and self._workspace_role_matches(operation, token_provider):
                    return "alreadyApplied"
                raise RuntimeError("The target already has a different workspace role or the assignment conflicts.") from error
        self._request(
            "POST",
            f"{POWER_BI_API}/groups/{operation['workspaceId']}/datasets/{operation['artifactId']}/users",
            POWER_BI_RESOURCE,
            token_provider,
            {"identifier": operation["targetUserPrincipalName"], "principalType": "User", "datasetUserAccessRight": operation["right"]},
        )
        return "applied"

    def _run(self, tenant_id: str, plan: dict[str, Any]) -> None:
        completed = self._load_completed(tenant_id)
        token_provider = AccessTokenProvider(tenant_id)
        applied = 0
        resumed = 0
        failed = 0
        self._update(status="running", stage="Anvender mappede rettigheder")
        try:
            for index, operation in enumerate(plan["operations"], start=1):
                if self._cancel.is_set():
                    raise InterruptedError("Permission migration cancelled.")
                self._update(current=index, progress=int(((index - 1) / len(plan["operations"])) * 100), stage=f"Anvender rettighed {index}/{len(plan['operations'])}: {operation['workspaceName']}")
                if operation["id"] in completed:
                    resumed += 1
                    continue
                try:
                    outcome = self._execute_operation(operation, token_provider)
                    self._save_checkpoint(tenant_id, operation, outcome)
                    applied += outcome == "applied"
                    resumed += outcome == "alreadyApplied"
                    self._append_log(f"{operation['targetUserName']}: {operation['right']} on {operation['artifactName'] or operation['workspaceName']} ({outcome}).")
                except InterruptedError:
                    raise
                except Exception as error:
                    failed += 1
                    self._append_failure(operation, error)
                    self._append_log(f"Failed {operation['targetUserName']} on {operation['artifactName'] or operation['workspaceName']}: {error}")
            result = {"applied": applied, "alreadyApplied": resumed, "failed": failed, "unsupported": len(plan["unsupported"]), "total": len(plan["operations"])}
            report_path = self.checkpoint_directory / f"{tenant_id}.result.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps({"completedAtUtc": utc_now(), "result": result, "failures": self.status()["failures"], "unsupported": plan["unsupported"]}, indent=2), encoding="utf-8")
            self._update(status="completed", progress=100, current=len(plan["operations"]), stage="Rettighedsmigration gennemført", completedAtUtc=utc_now(), result=result, wait=None)
        except InterruptedError:
            self._update(status="cancelled", stage="Rettighedsmigration annulleret", completedAtUtc=utc_now(), wait=None)
        except Exception as error:
            self._append_log(str(error))
            self._update(status="failed", stage="Rettighedsmigration fejlede", completedAtUtc=utc_now(), wait=None)


permission_migration_manager = PermissionMigrationManager()