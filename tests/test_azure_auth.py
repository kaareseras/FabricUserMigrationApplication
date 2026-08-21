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
    assert "--use-device-code" in login_commands[0]
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


def test_service_principal_login_uses_cli_without_exposing_secret(monkeypatch) -> None:
    account = {
        "name": "Tenant without subscription",
        "tenantId": "00000000-0000-0000-0000-000000000000",
        "user": {"name": "11111111-1111-1111-1111-111111111111", "type": "servicePrincipal"},
    }
    commands = []

    def fake_run(command, **kwargs):
        commands.append(list(command))
        return type("Result", (), {"returncode": 0, "stdout": json.dumps(account)})()

    manager = azure_auth.AzureAuthManager()
    monkeypatch.setattr(azure_auth, "find_azure_cli", lambda: "/usr/bin/az")
    monkeypatch.setattr(azure_auth.subprocess, "run", fake_run)
    monkeypatch.setattr(manager, "_list_tenants", lambda cli, current: [{"id": current["tenantId"], "name": "Tenant A", "domain": ""}])

    status = manager.login_service_principal(
        account["tenantId"],
        account["user"]["name"],
        "super-secret-value",
    )

    login_command = commands[0]
    assert "--service-principal" in login_command
    assert login_command[login_command.index("--password") + 1] == "super-secret-value"
    assert status["account"]["authType"] == "servicePrincipal"
    assert "super-secret-value" not in json.dumps(status)


def test_login_uses_device_code() -> None:
    assert azure_auth.login_command("/usr/bin/az")[-1] == "--use-device-code"


def test_failed_service_principal_login_can_be_retried(monkeypatch) -> None:
    manager = azure_auth.AzureAuthManager()
    monkeypatch.setattr(azure_auth, "find_azure_cli", lambda: "/usr/bin/az")
    monkeypatch.setattr(
        azure_auth.subprocess,
        "run",
        lambda *args, **kwargs: type("Result", (), {"returncode": 1, "stdout": "", "stderr": "sensitive"})(),
    )

    try:
        manager.login_service_principal(
            "00000000-0000-0000-0000-000000000000",
            "11111111-1111-1111-1111-111111111111",
            "super-secret-value",
        )
    except RuntimeError:
        pass

    status = manager.status()
    assert status["status"] == "failed"
    assert "super-secret-value" not in json.dumps(status)
    assert "sensitive" not in json.dumps(status)


def test_device_code_is_parsed_from_azure_cli_output() -> None:
    output = "Open https://microsoft.com/devicelogin and enter the code ABCD-EFGH to authenticate."

    match = azure_auth.DEVICE_CODE_PATTERN.search(output)
    assert match is not None
    assert match.group(1) == "ABCD-EFGH"


def test_scan_inventory_groups_workspaces_under_capacities() -> None:
    inventory = azure_auth.build_scan_inventory(
        [
            {"id": "cap-2", "displayName": "Shared", "sku": "F4", "state": "Active"},
            {"id": "cap-1", "displayName": "Finance", "sku": "F8", "state": "Active"},
        ],
        [
            {"id": "ws-2", "name": "Sales", "type": "Workspace", "capacityId": "cap-2"},
            {"id": "ws-1", "name": "Budget", "type": "Workspace", "capacityId": "cap-1"},
            {"id": "ws-3", "name": "My workspace", "type": "Personal"},
        ],
    )

    assert inventory["workspaceCount"] == 3
    assert [capacity["name"] for capacity in inventory["capacities"]] == ["Finance", "Shared", "Unassigned capacity"]
    assert inventory["capacities"][0]["workspaces"] == [{"id": "ws-1", "name": "Budget", "type": "Workspace"}]