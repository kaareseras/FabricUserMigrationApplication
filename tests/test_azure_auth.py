import json
import time

from server import azure_auth


def test_browser_login_tracks_device_code_and_account(monkeypatch) -> None:
    class FakeProcess:
        stdout = iter([
            "A web browser has been opened. Continue the login in the web browser.\n"
        ])

        @staticmethod
        def wait() -> int:
            return 0

    account = {
        "name": "Tenant A",
        "tenantId": "00000000-0000-0000-0000-000000000000",
        "user": {"name": "admin@example.com"},
    }
    tenants = {
        "value": [
            {"tenantId": account["tenantId"], "displayName": "Contoso", "defaultDomain": "contoso.onmicrosoft.com"},
            {"tenantId": "11111111-1111-1111-1111-111111111111", "displayName": "Fabrikam"},
        ]
    }
    commands = []
    login_commands = []
    login_environments = []

    def fake_run(command, **kwargs):
        commands.append(command)
        payload = tenants if "rest" in command else account
        return type("Result", (), {"returncode": 0, "stdout": json.dumps(payload)})()

    def fake_popen(command, **kwargs):
        login_commands.append(command)
        login_environments.append(kwargs["env"])
        return FakeProcess()

    manager = azure_auth.AzureAuthManager()
    monkeypatch.setattr(azure_auth.shutil, "which", lambda name: "/usr/bin/az")
    monkeypatch.setattr(azure_auth.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        azure_auth.subprocess,
        "run",
        fake_run,
    )

    manager.start()
    deadline = time.monotonic() + 2
    while manager.status()["status"] == "waiting" and time.monotonic() < deadline:
        time.sleep(0.01)

    status = manager.status()
    assert status["status"] == "authenticated"
    assert status["account"]["user"] == "admin@example.com"
    assert status["tenants"][0] == {"id": account["tenantId"], "name": "Contoso", "domain": "contoso.onmicrosoft.com"}
    assert "--tenant" not in login_commands[0]
    assert "--use-device-code" not in login_commands[0]
    assert login_environments[0]["AZURE_CORE_LOGIN_EXPERIENCE_V2"] == "off"


def test_browser_login_reports_missing_cli(monkeypatch) -> None:
    manager = azure_auth.AzureAuthManager()
    monkeypatch.setattr(azure_auth, "find_azure_cli", lambda: None)

    try:
        manager.start()
    except RuntimeError as error:
        assert str(error) == "Azure CLI is not installed on the server."
    else:
        raise AssertionError("Expected missing Azure CLI to be rejected")