import json
import shutil
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .database import DEFAULT_DATABASE, DEFAULT_SOURCE, ROOT, import_snapshot


SCRIPT_PATH = ROOT / "scripts" / "Invoke-FabricPermissionDiscovery.ps1"


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
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if shell is None:
            raise RuntimeError("PowerShell is not installed on the server.")
        if shutil.which("az") is None:
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

        threading.Thread(target=self._run, args=(command,), daemon=True).start()
        return self.status()

    def _update(self, **values: Any) -> None:
        with self._lock:
            if self._job is not None:
                self._job.update(values)

    def _append_log(self, message: str) -> None:
        with self._lock:
            if self._job is not None:
                self._job["logs"] = [*self._job["logs"], message][-200:]

    def _run(self, command: list[str]) -> None:
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
            )
            assert process.stdout is not None
            for raw_line in process.stdout:
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("FABRIC_PROGRESS "):
                    progress = json.loads(line.removeprefix("FABRIC_PROGRESS "))
                    self._update(progress=progress["percent"], stage=progress["stage"])
                else:
                    self._append_log(line)

            return_code = process.wait()
            if return_code != 0:
                raise RuntimeError(f"Discovery process exited with code {return_code}.")

            self._update(status="importing", progress=96, stage="Importerer nyt snapshot")
            counts = import_snapshot(DEFAULT_SOURCE, DEFAULT_DATABASE)
            self._update(
                status="completed",
                progress=100,
                stage="Scan gennemført",
                completedAtUtc=utc_now(),
                result=counts,
            )
        except Exception as error:
            self._append_log(str(error))
            self._update(status="failed", stage="Scan fejlede", completedAtUtc=utc_now())


scan_manager = ScanManager()