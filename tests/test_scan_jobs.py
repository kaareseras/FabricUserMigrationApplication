import sys
import time
from pathlib import Path

from server import scan_jobs


def test_find_powershell_uses_local_install(monkeypatch, tmp_path: Path) -> None:
    local_shell = tmp_path / ".venv" / "powershell" / "pwsh"
    local_shell.parent.mkdir(parents=True)
    local_shell.touch()
    monkeypatch.setattr(scan_jobs, "ROOT", tmp_path)
    monkeypatch.setattr(scan_jobs.shutil, "which", lambda name: None)

    assert scan_jobs.find_powershell() == str(local_shell)


def test_scan_manager_tracks_progress_and_imports(monkeypatch) -> None:
    class FakeProcess:
        stdout = iter([
            'FABRIC_PROGRESS {"percent":42,"stage":"Scanning","current":5,"total":14}\n',
            "Found workspace\n",
        ])

        @staticmethod
        def wait() -> int:
            return 0

    manager = scan_jobs.ScanManager()
    monkeypatch.setattr(scan_jobs.shutil, "which", lambda name: sys.executable)
    monkeypatch.setattr(scan_jobs.subprocess, "Popen", lambda *args, **kwargs: FakeProcess())
    monkeypatch.setattr(scan_jobs, "import_snapshot", lambda source, database: {"workspaces": 1})

    manager.start("00000000-0000-0000-0000-000000000000", 5, False, True)
    deadline = time.monotonic() + 2
    while manager.status()["status"] not in {"completed", "failed"} and time.monotonic() < deadline:
        time.sleep(0.01)

    status = manager.status()
    assert status["status"] == "completed"
    assert status["progress"] == 100
    assert status["result"] == {"workspaces": 1}
    assert "Found workspace" in status["logs"]


def test_scan_manager_tracks_and_clears_workspace_progress() -> None:
    manager = scan_jobs.ScanManager()
    manager._job = {"status": "running", "logs": [], "workspaceProgress": None}

    assert manager._handle_protocol_line(
        'FABRIC_PROGRESS {"percent":38,"stage":"Workspace 5","current":5,"total":14}'
    )
    assert manager.status()["workspaceProgress"] == {"current": 5, "total": 14}

    assert manager._handle_protocol_line('FABRIC_PROGRESS {"percent":72,"stage":"Scanning artifacts"}')
    assert manager.status()["workspaceProgress"] is None


def test_scan_manager_rejects_parallel_scan(monkeypatch) -> None:
    manager = scan_jobs.ScanManager()
    manager._job = {"status": "running", "logs": []}
    monkeypatch.setattr(scan_jobs.shutil, "which", lambda name: sys.executable)

    try:
        manager.start("tenant", 0, False, False)
    except RuntimeError as error:
        assert str(error) == "A scan is already running."
    else:
        raise AssertionError("Expected a parallel scan to be rejected")


def test_scan_manager_tracks_structured_api_wait() -> None:
    manager = scan_jobs.ScanManager()
    manager._job = {"status": "running", "logs": [], "wait": None}
    wait = {
        "reason": "rateLimit",
        "api": "WorkspaceAccess",
        "seconds": 18,
        "nextCallAtUtc": "2026-08-19T10:30:00Z",
        "hourlyLimit": 200,
    }

    assert manager._handle_protocol_line(f"FABRIC_WAIT {scan_jobs.json.dumps(wait)}")
    assert manager.status()["wait"] == wait
    assert "limit 200/hour" in manager.status()["logs"][-1]

    assert manager._handle_protocol_line("FABRIC_WAIT_END")
    assert manager.status()["wait"] is None


def test_scan_manager_tracks_structured_estimate() -> None:
    manager = scan_jobs.ScanManager()
    manager._job = {"status": "running", "logs": [], "estimate": None}
    estimate = {
        "workspaceCount": 1000,
        "accessPacingSeconds": 18082,
        "metadataBatches": 10,
        "minimumSeconds": 18712,
        "maximumSeconds": 19942,
    }

    assert manager._handle_protocol_line(f"FABRIC_ESTIMATE {scan_jobs.json.dumps(estimate)}")
    assert manager.status()["estimate"] == estimate