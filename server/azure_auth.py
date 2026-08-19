import json
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any


LOGIN_URL = "https://microsoft.com/devicelogin"
PROJECT_AZURE_CLI = Path(__file__).resolve().parents[1] / ".venv" / "bin" / "az"


def find_azure_cli() -> str | None:
    cli = shutil.which("az")
    if cli is not None:
        return cli
    return str(PROJECT_AZURE_CLI) if PROJECT_AZURE_CLI.exists() else None


class AzureAuthManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: dict[str, Any] | None = None

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
            self._state = {
                "status": "waiting",
                "stage": "Starter Microsoft-login",
                "loginUrl": LOGIN_URL,
                "userCode": None,
                "account": None,
                "logs": [],
            }

        command = [
            cli,
            "login",
            "--allow-no-subscriptions",
            "--output",
            "none",
            "--only-show-errors",
        ]
        threading.Thread(target=self._run_login, args=(command,), daemon=True).start()
        return self.status()

    def logout(self) -> dict[str, Any]:
        cli = find_azure_cli()
        if cli is None:
            raise RuntimeError("Azure CLI is not installed on the server.")
        with self._lock:
            if self._state and self._state["status"] == "waiting":
                raise RuntimeError("Browser login is still running.")
        subprocess.run([cli, "logout"], capture_output=True, text=True, timeout=15, check=False)
        with self._lock:
            self._state = self._idle_state()
        return self.status()

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

    def _run_login(self, command: list[str]) -> None:
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
            assert process.stdout is not None
            for raw_line in process.stdout:
                line = raw_line.strip()
                if not line:
                    continue
                url_match = re.search(r"https?://[^\s]+", line)
                values: dict[str, Any] = {"stage": "Afventer personligt login i browseren"}
                if url_match:
                    values["loginUrl"] = url_match.group(0).rstrip(".,)")
                self._update(**values)
                self._append_log(line)

            if process.wait() != 0:
                raise RuntimeError("Microsoft-login blev ikke gennemført.")

            account = self._existing_session()
            if account["status"] != "authenticated":
                raise RuntimeError("Azure CLI kunne ikke bekræfte den valgte konto.")
            with self._lock:
                self._state = account
        except Exception as error:
            self._append_log(str(error))
            self._update(status="failed", stage="Login fejlede")


azure_auth_manager = AzureAuthManager()