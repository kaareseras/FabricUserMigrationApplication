import sys
import time

from server import scan_jobs


def test_scan_manager_tracks_progress_and_imports(monkeypatch) -> None:
    class FakeProcess:
        stdout = iter([
            'FABRIC_PROGRESS {"percent":42,"stage":"Scanning"}\n',
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