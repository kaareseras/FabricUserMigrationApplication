import pytest
from fastapi.testclient import TestClient

from server.app import app
from server.security import TOKEN_ENV_VAR


@pytest.fixture(autouse=True)
def clean_token_env(monkeypatch):
    monkeypatch.delenv(TOKEN_ENV_VAR, raising=False)


def test_open_mode_allows_mutating_requests_without_token() -> None:
    response = TestClient(app).delete("/api/permission-migrations/current")

    # No migration is running, so the handler answers 409; the auth gate was not the blocker.
    assert response.status_code == 409


def test_missing_token_is_rejected_when_configured(monkeypatch) -> None:
    monkeypatch.setenv(TOKEN_ENV_VAR, "secret-token")

    response = TestClient(app).delete("/api/permission-migrations/current")

    assert response.status_code == 401
    assert response.headers.get("WWW-Authenticate") == "Bearer"


def test_wrong_token_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv(TOKEN_ENV_VAR, "secret-token")

    response = TestClient(app).delete(
        "/api/permission-migrations/current", headers={"Authorization": "Bearer wrong-token"}
    )

    assert response.status_code == 401


def test_correct_token_passes_the_auth_gate(monkeypatch) -> None:
    monkeypatch.setenv(TOKEN_ENV_VAR, "secret-token")

    response = TestClient(app).delete(
        "/api/permission-migrations/current", headers={"Authorization": "Bearer secret-token"}
    )

    # Reaching the handler (409: no migration running) proves authentication passed.
    assert response.status_code == 409


def test_read_endpoints_stay_open_when_token_configured(monkeypatch) -> None:
    monkeypatch.setenv(TOKEN_ENV_VAR, "secret-token")

    response = TestClient(app).get("/api/auth/current")

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, 401),
        ("", 401),
        ("Bearer", 401),
        ("Token secret-token", 401),
        ("Bearer wrong-token", 401),
        ("bearer secret-token", 409),
    ],
)
def test_token_header_variants(monkeypatch, header: str | None, expected: int) -> None:
    monkeypatch.setenv(TOKEN_ENV_VAR, "secret-token")

    headers = {"Authorization": header} if header is not None else {}
    response = TestClient(app).delete("/api/permission-migrations/current", headers=headers)

    assert response.status_code == expected


def test_lifespan_starts_with_and_without_token(monkeypatch) -> None:
    with TestClient(app):
        pass

    monkeypatch.setenv(TOKEN_ENV_VAR, "secret-token")
    with TestClient(app) as client:
        response = client.get("/api/auth/current")

    assert response.status_code == 200
