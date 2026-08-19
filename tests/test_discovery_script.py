import json
import os
import subprocess
from pathlib import Path

import pytest

from server.scan_jobs import SCRIPT_PATH, find_powershell


def run_powershell_harness(tmp_path: Path, body: str) -> subprocess.CompletedProcess[str]:
    powershell = find_powershell()
    if powershell is None:
        pytest.skip("PowerShell is not installed")

    quoted_script = str(SCRIPT_PATH).replace("'", "''")
    quoted_output = str(tmp_path).replace("'", "''")
    harness = f"""
$ErrorActionPreference = 'Stop'
$env:FABRIC_DISCOVERY_LOAD_FUNCTIONS_ONLY = '1'
. '{quoted_script}' -TenantId 'test-tenant' -OutputPath '{quoted_output}'
{body}
"""
    environment = os.environ.copy()
    environment.setdefault("DOTNET_SYSTEM_GLOBALIZATION_INVARIANT", "1")
    result = subprocess.run(
        [powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", harness],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def test_workspace_access_resumes_from_checkpoint(tmp_path: Path) -> None:
    result = run_powershell_harness(
        tmp_path,
        r"""
$script:requestCount = 0
function Invoke-ApiRequest {
    param($RateLimitKey, $MinimumIntervalSeconds)
    if ($RateLimitKey -ne 'WorkspaceAccess' -or $MinimumIntervalSeconds -ne 18.1) {
        throw "Workspace access request was not paced correctly."
    }
    $script:requestCount++
    return @{ accessDetails = @() }
}
$workspaces = @(
    [pscustomobject]@{ id = 'one'; name = 'One'; type = 'Workspace' },
    [pscustomobject]@{ id = 'two'; name = 'Two'; type = 'Workspace' },
    [pscustomobject]@{ id = 'three'; name = 'Three'; type = 'Workspace' }
)
$checkpoint = Join-Path $OutputPath 'workspace.checkpoint.ndjson'
$null = Get-WorkspaceAssignments -Workspaces $workspaces -Headers @{} -CheckpointPath $checkpoint
if ($script:requestCount -ne 3) { throw "Expected 3 initial requests, got $script:requestCount." }
$null = Get-WorkspaceAssignments -Workspaces $workspaces -Headers @{} -CheckpointPath $checkpoint
if ($script:requestCount -ne 3) { throw "Resume made unexpected API requests." }
if (@(Get-Content $checkpoint).Count -ne 3) { throw 'Expected one checkpoint per workspace.' }
""",
    )
    progress = [
        json.loads(line.removeprefix("FABRIC_PROGRESS "))
        for line in result.stdout.splitlines()
        if line.startswith("FABRIC_PROGRESS ")
    ]
    assert [(item["current"], item["total"]) for item in progress] == [(1, 3), (2, 3), (3, 3)]


def test_power_bi_scans_batches_of_100_and_resumes(tmp_path: Path) -> None:
    run_powershell_harness(
        tmp_path,
        r"""
$script:batchSizes = [System.Collections.Generic.List[int]]::new()
function Start-Sleep { param([int]$Seconds, [int]$Milliseconds) }
function Invoke-ApiRequest {
    param($Method, $Uri, $Headers, $Body, $RateLimitKey, $MinimumIntervalSeconds)
    if ($RateLimitKey -ne 'PowerBIMetadataScan' -or $MinimumIntervalSeconds -ne 7.3) {
        throw "Power BI metadata request was not paced correctly."
    }
    if ($Method -eq 'Post') {
        [void]$script:batchSizes.Add(@($Body.workspaces).Count)
        return @{ id = "scan-$($script:batchSizes.Count)" }
    }
    if ($Uri -like '*/scanStatus/*') { return @{ status = 'Succeeded' } }
    return @{ workspaces = @() }
}
$workspaces = @(1..205 | ForEach-Object { [pscustomobject]@{ id = "workspace-$_" } })
$resultPath = Join-Path $OutputPath 'results.ndjson'
$checkpoint = Join-Path $OutputPath 'artifacts.checkpoint.ndjson'
$count = Get-PowerBIArtifactUsers -Workspaces $workspaces -Headers @{} -ResultPath $resultPath -CheckpointPath $checkpoint
if ($count -ne 3) { throw "Expected 3 batches, got $count." }
if (($script:batchSizes -join ',') -ne '100,100,5') { throw "Unexpected batch sizes: $($script:batchSizes -join ',')." }
$count = Get-PowerBIArtifactUsers -Workspaces $workspaces -Headers @{} -ResultPath $resultPath -CheckpointPath $checkpoint
if ($count -ne 3 -or $script:batchSizes.Count -ne 3) { throw 'Resume submitted duplicate metadata scans.' }
""",
    )


def test_rate_limiter_waits_for_remaining_interval(tmp_path: Path) -> None:
    result = run_powershell_harness(
        tmp_path,
        r"""
$script:sleptMilliseconds = 0
function Start-Sleep {
    param([int]$Seconds, [int]$Milliseconds)
    $script:sleptMilliseconds += $Milliseconds + ($Seconds * 1000)
}
$lastRequestByLimit['WorkspaceAccess'] = [DateTime]::UtcNow
Wait-ApiRateLimit -Key 'WorkspaceAccess' -MinimumIntervalSeconds 18.1
if ($script:sleptMilliseconds -lt 18000) {
    throw "Expected at least 18 seconds of pacing, got $script:sleptMilliseconds milliseconds."
}
""",
    )
    lines = result.stdout.splitlines()
    wait_line = next(line for line in lines if line.startswith("FABRIC_WAIT "))
    assert "FABRIC_WAIT_END" in lines
    wait = json.loads(wait_line.removeprefix("FABRIC_WAIT "))
    assert wait["reason"] == "rateLimit"
    assert wait["api"] == "WorkspaceAccess"
    assert wait["hourlyLimit"] == 200
    assert wait["seconds"] >= 18
    assert wait["nextCallAtUtc"]


def test_scan_estimate_uses_workspace_limits_and_metadata_batches(tmp_path: Path) -> None:
    result = run_powershell_harness(
        tmp_path,
        "Write-ScanEstimate -WorkspaceCount 205 -IncludeArtifacts $true",
    )
    estimate_line = next(line for line in result.stdout.splitlines() if line.startswith("FABRIC_ESTIMATE "))
    estimate = json.loads(estimate_line.removeprefix("FABRIC_ESTIMATE "))

    assert estimate == {
        "workspaceCount": 205,
        "accessPacingSeconds": 3693.0,
        "metadataBatches": 3.0,
        "minimumSeconds": 3903.0,
        "maximumSeconds": 4293.0,
    }


def test_scan_progress_includes_workspace_position(tmp_path: Path) -> None:
    result = run_powershell_harness(
        tmp_path,
        "Write-ScanProgress -Percent 38 -Stage 'Workspace 5' -Current 5 -Total 14",
    )
    progress_line = next(line for line in result.stdout.splitlines() if line.startswith("FABRIC_PROGRESS "))

    assert json.loads(progress_line.removeprefix("FABRIC_PROGRESS ")) == {
        "percent": 38,
        "stage": "Workspace 5",
        "current": 5,
        "total": 14,
    }