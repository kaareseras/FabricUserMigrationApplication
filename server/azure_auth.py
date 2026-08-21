import json
import os
import re
import shutil
import subprocess
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


LOGIN_URL = "https://microsoft.com/devicelogin"
FABRIC_RESOURCE = "https://api.fabric.microsoft.com"
FABRIC_API = f"{FABRIC_RESOURCE}/v1"
PROJECT_AZURE_CLI = Path(__file__).resolve().parents[1] / ".venv" / "bin" / "az"
DEVICE_CODE_PATTERN = re.compile(r"\bcode[: ]+([A-Z0-9-]{6,})\b", re.IGNORECASE)


def find_azure_cli() -> str | None:
    cli = shutil.which("az")
    if cli is not None:
        return cli
    return str(PROJECT_AZURE_CLI) if PROJECT_AZURE_CLI.exists() else None


def login_command(cli: str) -> list[str]:
    return [cli, "login", "--allow-no-subscriptions", "--output", "none", "--only-show-errors", "--use-device-code"]


class AzureAuthManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: dict[str, Any] | None = None
        self._login_process: subprocess.Popen[str] | None = None
        self._login_generation = 0

    def status(self) -> dict[str, Any]:
        with self._lock:
            if self._state is not None:
                return {**self._state, "logs": list(self._state["logs"])}

        state = self._existing_session()
        with self._lock:
            if self._state is None:
                self._state = state
            return {**self._state, "logs": list(self._state["logs"])}

    def start(self) -> dict[str, Any]:
        cli = find_azure_cli()
        if cli is None:
            raise RuntimeError("Azure CLI is not installed on the server.")

        with self._lock:
            if self._state and self._state["status"] == "waiting":
                raise RuntimeError("A browser login is already running.")
            self._login_generation += 1
            generation = self._login_generation
            self._state = {
                "status": "waiting",
                "stage": "Starter Microsoft-login",
                "loginUrl": LOGIN_URL,
                "userCode": None,
                "account": None,
                "logs": [],
            }

        command = login_command(cli)
        threading.Thread(target=self._run_login, args=(command, generation), daemon=True).start()
        return self.status()

    def login_service_principal(self, tenant_id: str, client_id: str, client_secret: str) -> dict[str, Any]:
        cli = find_azure_cli()
        if cli is None:
            raise RuntimeError("Azure CLI is not installed on the server.")
        with self._lock:
            if self._state and self._state["status"] == "waiting":
                raise RuntimeError("Another login is already running.")
            self._login_generation += 1
            self._state = {
                "status": "waiting",
                "stage": "Logger ind med service principal",
                "loginUrl": LOGIN_URL,
                "userCode": None,
                "account": None,
                "tenants": [],
                "logs": [],
            }

        command = [
            cli,
            "login",
            "--service-principal",
            "--username",
            client_id,
            "--password",
            client_secret,
            "--tenant",
            tenant_id,
            "--allow-no-subscriptions",
            "--output",
            "none",
            "--only-show-errors",
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
            if result.returncode != 0:
                raise RuntimeError("Service principal login failed. Verify the tenant ID, client ID, secret, and Fabric API permissions.")
            account = self._existing_session()
            if account["status"] != "authenticated":
                raise RuntimeError("Azure CLI could not verify the service principal session.")
            with self._lock:
                self._state = account
            return self.status()
        except subprocess.TimeoutExpired as error:
            with self._lock:
                self._state = self._idle_state("failed", "Service principal-login fik timeout")
            raise RuntimeError("Service principal login timed out.") from error
        except RuntimeError:
            with self._lock:
                self._state = self._idle_state("failed", "Service principal-login fejlede")
            raise
        finally:
            command[command.index("--password") + 1] = ""

    def logout(self) -> dict[str, Any]:
        cli = find_azure_cli()
        if cli is None:
            raise RuntimeError("Azure CLI is not installed on the server.")
        with self._lock:
            self._login_generation += 1
            login_process = self._login_process
            self._login_process = None
        if login_process is not None and login_process.poll() is None:
            login_process.terminate()
        subprocess.run([cli, "logout"], capture_output=True, text=True, timeout=15, check=False)
        with self._lock:
            self._state = self._idle_state()
        return self.status()

    def scan_inventory(self, tenant_id: str, include_personal: bool = False) -> dict[str, Any]:
        cli = find_azure_cli()
        if cli is None:
            raise RuntimeError("Azure CLI is not installed on the server.")
        token_scope = ["--tenant", tenant_id]
        try:
            account_result = subprocess.run(
                [cli, "account", "list", "--all", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if account_result.returncode == 0:
                account = next(
                    (item for item in json.loads(account_result.stdout) if item.get("tenantId") == tenant_id and item.get("id")),
                    None,
                )
                if account is not None:
                    token_scope = ["--subscription", account["id"]]
        except (json.JSONDecodeError, OSError, subprocess.TimeoutExpired):
            pass
        token_result = subprocess.run(
            [cli, "account", "get-access-token", *token_scope, "--resource", FABRIC_RESOURCE, "--query", "accessToken", "-o", "tsv"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        token = token_result.stdout.strip()
        if token_result.returncode != 0 or not token:
            raise RuntimeError("Azure CLI could not acquire a Fabric access token for the selected tenant.")

        capacities = self._fabric_collection(f"{FABRIC_API}/capacities", token, "value")
        workspace_type = "" if include_personal else "&type=workspace"
        workspaces = self._fabric_collection(f"{FABRIC_API}/admin/workspaces?state=active{workspace_type}", token, "workspaces")
        return build_scan_inventory(capacities, workspaces)

    @staticmethod
    def _fabric_collection(url: str, token: str, property_name: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        next_url: str | None = url
        while next_url:
            request = urllib.request.Request(next_url, headers={"Authorization": f"Bearer {token}"})
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    payload = json.load(response)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
                if isinstance(error, urllib.error.HTTPError) and error.code in {401, 403}:
                    raise RuntimeError(
                        "Signed in, but this account is not authorized to read Fabric admin workspaces. "
                        "Use a Fabric administrator account or grant the required Fabric API permissions."
                    ) from error
                detail = getattr(error, "reason", None) or str(error)
                raise RuntimeError(f"Fabric inventory request failed: {detail}") from error
            items.extend(payload.get(property_name) or [])
            next_url = payload.get("continuationUri")
        return items

    @staticmethod
    def _idle_state(status: str = "idle", stage: str = "Ikke logget ind") -> dict[str, Any]:
        return {
            "status": status,
            "stage": stage,
            "loginUrl": LOGIN_URL,
            "userCode": None,
            "account": None,
            "tenants": [],
            "logs": [],
        }

    def _existing_session(self) -> dict[str, Any]:
        cli = find_azure_cli()
        if cli is None:
            return self._idle_state("unavailable", "Azure CLI er ikke installeret")
        try:
            result = subprocess.run(
                [cli, "account", "show", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0:
                account = json.loads(result.stdout)
                return self._authenticated_state(account, self._list_tenants(cli, account))

            result = subprocess.run(
                [cli, "account", "list", "--all", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0:
                accounts = json.loads(result.stdout)
                account = next((item for item in accounts if item.get("isDefault")), accounts[0] if accounts else None)
                if account is not None:
                    return self._authenticated_state(account, self._list_tenants(cli, account))
        except (json.JSONDecodeError, OSError, subprocess.TimeoutExpired):
            pass
        return self._idle_state()

    @staticmethod
    def _list_tenants(cli: str, account: dict[str, Any]) -> list[dict[str, str]]:
        try:
            result = subprocess.run(
                [
                    cli,
                    "rest",
                    "--method",
                    "get",
                    "--url",
                    "https://management.azure.com/tenants?api-version=2020-01-01",
                    "--output",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode == 0:
                tenants = json.loads(result.stdout).get("value") or []
                return sorted(
                    [
                        {
                            "id": tenant["tenantId"],
                            "name": tenant.get("displayName") or tenant.get("defaultDomain") or tenant["tenantId"],
                            "domain": tenant.get("defaultDomain") or "",
                        }
                        for tenant in tenants
                        if tenant.get("tenantId")
                    ],
                    key=lambda tenant: tenant["name"].casefold(),
                )
        except (json.JSONDecodeError, OSError, subprocess.TimeoutExpired):
            pass

        tenant_id = account.get("tenantId") or ""
        return [{"id": tenant_id, "name": tenant_id, "domain": ""}] if tenant_id else []

    @staticmethod
    def _authenticated_state(account: dict[str, Any], tenants: list[dict[str, str]]) -> dict[str, Any]:
        user = account.get("user") or {}
        return {
            "status": "authenticated",
            "stage": "Logget ind",
            "loginUrl": LOGIN_URL,
            "userCode": None,
            "account": {
                "name": account.get("name") or "Tenant uden abonnement",
                "tenantId": account.get("tenantId") or "",
                "user": user.get("name") or "Ukendt bruger",
                "authType": "servicePrincipal" if user.get("type") == "servicePrincipal" else "delegated",
            },
            "tenants": tenants,
            "logs": [],
        }

    def _update(self, **values: Any) -> None:
        with self._lock:
            if self._state is not None:
                self._state.update(values)

    def _append_log(self, message: str) -> None:
        with self._lock:
            if self._state is not None:
                self._state["logs"] = [*self._state["logs"], message][-30:]

    def _run_login(self, command: list[str], generation: int) -> None:
        try:
            environment = os.environ.copy()
            environment["AZURE_CORE_LOGIN_EXPERIENCE_V2"] = "off"
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
            )
            with self._lock:
                if generation != self._login_generation:
                    process.terminate()
                    return
                self._login_process = process
            assert process.stdout is not None
            for raw_line in process.stdout:
                with self._lock:
                    if generation != self._login_generation:
                        process.terminate()
                        return
                line = raw_line.strip()
                if not line:
                    continue
                url_match = re.search(r"https?://[^\s]+", line)
                code_match = DEVICE_CODE_PATTERN.search(line)
                values: dict[str, Any] = {"stage": "Afventer personligt login i browseren"}
                if url_match:
                    values["loginUrl"] = url_match.group(0).rstrip(".,)")
                if code_match:
                    values["userCode"] = code_match.group(1).upper()
                self._update(**values)
                self._append_log(line)

            if process.wait() != 0:
                raise RuntimeError("Microsoft-login blev ikke gennemført.")

            account = self._existing_session()
            if account["status"] != "authenticated":
                raise RuntimeError("Azure CLI kunne ikke bekræfte den valgte konto.")
            with self._lock:
                if generation == self._login_generation:
                    self._state = account
        except Exception as error:
            with self._lock:
                if generation == self._login_generation:
                    if self._state is not None:
                        self._state["logs"] = [*self._state["logs"], str(error)][-30:]
                        self._state.update(status="failed", stage="Login fejlede")
        finally:
            with self._lock:
                if generation == self._login_generation:
                    self._login_process = None


azure_auth_manager = AzureAuthManager()


def build_scan_inventory(capacities: list[dict[str, Any]], workspaces: list[dict[str, Any]]) -> dict[str, Any]:
    capacity_groups = {
        capacity["id"]: {
            "id": capacity["id"],
            "name": capacity.get("displayName") or capacity["id"],
            "sku": capacity.get("sku") or "",
            "state": capacity.get("state") or "",
            "workspaces": [],
        }
        for capacity in capacities
        if capacity.get("id")
    }
    unassigned_id = "unassigned"
    for workspace in workspaces:
        if not workspace.get("id"):
            continue
        capacity_id = workspace.get("capacityId") or unassigned_id
        if capacity_id not in capacity_groups:
            capacity_groups[capacity_id] = {
                "id": capacity_id,
                "name": "Unassigned capacity" if capacity_id == unassigned_id else capacity_id,
                "sku": "",
                "state": "",
                "workspaces": [],
            }
        capacity_groups[capacity_id]["workspaces"].append({
            "id": workspace["id"],
            "name": workspace.get("name") or workspace["id"],
            "type": workspace.get("type") or "",
        })

    groups = list(capacity_groups.values())
    for capacity in groups:
        capacity["workspaces"].sort(key=lambda workspace: workspace["name"].casefold())
    groups.sort(key=lambda capacity: (capacity["id"] == unassigned_id, capacity["name"].casefold()))
    return {"capacities": groups, "workspaceCount": len(workspaces)}