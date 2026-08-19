from pathlib import Path

from server.database import import_snapshot


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_image_packages_scan_dependencies() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "azure-cli powershell" in dockerfile
    assert "python -m pip install -r requirements.txt" in dockerfile
    assert "COPY --chown=app:app scripts ./scripts" in dockerfile
    assert "AZURE_CONFIG_DIR=/app/.azure" in dockerfile
    assert 'VOLUME ["/app/data", "/app/artifacts/fabric-permission-discovery", "/app/.azure"]' in dockerfile


def test_compose_persists_writable_application_state() -> None:
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")

    assert "fabric-artifacts:/app/artifacts/fabric-permission-discovery" in compose
    assert "fabric-data:/app/data" in compose
    assert "azure-config:/app/.azure" in compose
    assert "AZURE_LOGIN_USE_DEVICE_CODE: \"true\"" in compose
    assert ":ro" not in compose


def test_empty_discovery_source_creates_first_run_database(tmp_path: Path) -> None:
    source = tmp_path / "artifacts"
    source.mkdir()
    database = tmp_path / "data" / "fabric-access.db"

    counts = import_snapshot(source, database)

    assert database.is_file()
    assert counts == {
        "workspaces": 0,
        "artifacts": 0,
        "principals": 0,
        "workspaceRoles": 0,
        "itemPermissions": 0,
    }
