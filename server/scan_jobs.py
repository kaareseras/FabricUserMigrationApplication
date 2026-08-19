import json
import os
import shutil
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .database import DEFAULT_DATABASE, DEFAULT_SOURCE, ROOT, import_snapshot


SCRIPT_PATH = ROOT / "scripts" / "Invoke-FabricPermissionDiscovery.ps1"


def find_powershell() -> str | None:
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is not None:
        return shell
    local_shell = ROOT / ".venv" / "powershell" / "pwsh"
    return str(local_shell) if local_shell.is_file() else None


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class ScanManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._job: dict[str, Any] | None = None

    def status(self) -> dict[str, Any]:
        with self._lock:
            if self._job is None:
                return {"status": "idle", "progress": 0, "stage": "Klar til scanning", "logs": []}
            return {**self._job, "logs": list(self._job["logs"])}

    def start(self, tenant_id: str, workspace_limit: int, include_personal: bool, include_artifacts: bool) -> dict[str, Any]:
        shell = find_powershell()
        if shell is None:
            raise RuntimeError("PowerShell is not installed on the server.")
        azure_cli = shutil.which("az")
        if azure_cli is None:
            local_cli = ROOT / ".venv" / "bin" / "az"
            azure_cli = str(local_cli) if local_cli.exists() else None
        if azure_cli is None:
            raise RuntimeError("Azure CLI is not installed on the server.")

        with self._lock:
            if self._job and self._job["status"] in {"queued", "running", "importing"}:
                raise RuntimeError("A scan is already running.")
            self._job = {
                "status": "queued",
                "progress": 0,
                "stage": "Forbereder scan",
                "startedAtUtc": utc_now(),
                "completedAtUtc": None,
                "logs": [],
                "result": None,
                "wait": None,
                "estimate": None,
            }

        command = [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(SCRIPT_PATH),
            "-TenantId",
            tenant_id,
            "-OutputPath",
            str(DEFAULT_SOURCE),
            "-WorkspaceLimit",
            str(workspace_limit),
        ]
        if include_personal:
            command.append("-IncludePersonalWorkspaces")
        if include_artifacts:
            command.append("-IncludePowerBIArtifactUsers")

        environment = os.environ.copy()
        environment["PATH"] = f"{Path(azure_cli).parent}{os.pathsep}{environment.get('PATH', '')}"
        environment.setdefault("DOTNET_SYSTEM_GLOBALIZATION_INVARIANT", "1")
        threading.Thread(target=self._run, args=(command, environment), daemon=True).start()
        return self.status()

    def _update(self, **values: Any) -> None:
        with self._lock:
            if self._job is not None:
                self._job.update(values)

    def _append_log(self, message: str) -> None:
        with self._lock:
            if self._job is not None:
                self._job["logs"] = [*self._job["logs"], message][-200:]

    def _handle_protocol_line(self, line: str) -> bool:
        if line.startswith("FABRIC_PROGRESS "):
            progress = json.loads(line.removeprefix("FABRIC_PROGRESS "))
            workspace_progress = None
            if "current" in progress and "total" in progress:
                workspace_progress = {"current": progress["current"], "total": progress["total"]}
            self._update(
                progress=progress["percent"],
                stage=progress["stage"],
                workspaceProgress=workspace_progress,
            )
            return True
        if line.startswith("FABRIC_WAIT "):
            wait = json.loads(line.removeprefix("FABRIC_WAIT "))
            self._update(wait=wait)
            limit = f"; limit {wait['hourlyLimit']}/hour" if wait.get("hourlyLimit") else ""
            self._append_log(
                f"Waiting {wait['seconds']}s before the next {wait.get('api') or 'API'} call "
                f"({wait['reason']}{limit}); resumes at {wait['nextCallAtUtc']}."
            )
            return True
        if line == "FABRIC_WAIT_END":
            self._update(wait=None)
            return True
        if line.startswith("FABRIC_ESTIMATE "):
            estimate = json.loads(line.removeprefix("FABRIC_ESTIMATE "))
            self._update(estimate=estimate)
            return True
        return False

    def _run(self, command: list[str], environment: dict[str, str]) -> None:
        self._update(status="running", stage="Starter discovery")
        try:
            process = subprocess.Popen(
                command,
                cwd=ROOT,
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
                if not self._handle_protocol_line(line):
                    self._append_log(line)

            return_code = process.wait()
            if return_code != 0:
                raise RuntimeError(f"Discovery process exited with code {return_code}.")

            self._update(status="importing", progress=96, stage="Importerer nyt snapshot", wait=None)
            counts = import_snapshot(DEFAULT_SOURCE, DEFAULT_DATABASE)
            self._update(
                status="completed",
                progress=100,
                stage="Scan gennemført",
                completedAtUtc=utc_now(),
                result=counts,
                wait=None,
            )
        except Exception as error:
            self._append_log(str(error))
            self._update(status="failed", stage="Scan fejlede", completedAtUtc=utc_now(), wait=None)


scan_manager = ScanManager()