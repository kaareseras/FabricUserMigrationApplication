[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string]$TenantId,

    [string]$OutputPath,

    [ValidateRange(0, 100000)]
    [int]$WorkspaceLimit = 0,

    [switch]$IncludePersonalWorkspaces,

    [switch]$IncludePowerBIArtifactUsers
)

$ErrorActionPreference = 'Stop'
$fabricBaseUrl = 'https://api.fabric.microsoft.com/v1'
$powerBiBaseUrl = 'https://api.powerbi.com/v1.0/myorg'
$fabricResource = 'https://api.fabric.microsoft.com'
$powerBiResource = 'https://analysis.windows.net/powerbi/api'
$lastRequestByLimit = @{}

function Write-ScanProgress {
    param(
        [Parameter(Mandatory)][ValidateRange(0, 100)][int]$Percent,
        [Parameter(Mandatory)][string]$Stage,
        [int]$Current = 0,
        [int]$Total = 0
    )

    $progress = [ordered]@{ percent = $Percent; stage = $Stage }
    if ($Total -gt 0) {
        $progress.current = $Current
        $progress.total = $Total
    }
    Write-Host "FABRIC_PROGRESS $($progress | ConvertTo-Json -Compress)"
}

function Write-ScanWait {
    param(
        [Parameter(Mandatory)][ValidateSet('rateLimit', 'retry', 'metadataProcessing')][string]$Reason,
        [Parameter(Mandatory)][double]$Seconds,
        [string]$Api,
        [int]$HourlyLimit = 0
    )

    $waitSeconds = [math]::Max(0, $Seconds)
    Write-Host "FABRIC_WAIT $([ordered]@{
        reason = $Reason
        api = $Api
        seconds = [math]::Ceiling($waitSeconds)
        nextCallAtUtc = [DateTime]::UtcNow.AddSeconds($waitSeconds).ToString('o')
        hourlyLimit = $HourlyLimit
    } | ConvertTo-Json -Compress)"
}

function Write-ScanWaitEnd {
    Write-Host 'FABRIC_WAIT_END'
}

function Write-ScanEstimate {
    param(
        [Parameter(Mandatory)][int]$WorkspaceCount,
        [Parameter(Mandatory)][bool]$IncludeArtifacts
    )

    $accessPacingSeconds = [math]::Ceiling([math]::Max(0, $WorkspaceCount - 1) * 18.1)
    $metadataBatches = if ($IncludeArtifacts -and $WorkspaceCount -gt 0) { [math]::Ceiling($WorkspaceCount / 100) } else { 0 }
    Write-Host "FABRIC_ESTIMATE $([ordered]@{
        workspaceCount = $WorkspaceCount
        accessPacingSeconds = $accessPacingSeconds
        metadataBatches = $metadataBatches
        minimumSeconds = 30 + $accessPacingSeconds + ($metadataBatches * 60)
        maximumSeconds = 60 + $accessPacingSeconds + ($metadataBatches * 180)
    } | ConvertTo-Json -Compress)"
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $PSScriptRoot '..\artifacts\fabric-permission-discovery'
}

function Get-AzCliAccessToken {
    param([Parameter(Mandatory)][string]$Resource)

    $token = az account get-access-token --tenant $TenantId --resource $Resource --query accessToken -o tsv
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($token)) {
        throw "Azure CLI could not acquire a token for $Resource. Run 'az login --tenant $TenantId --allow-no-subscriptions' and try again."
    }

    return $token.Trim()
}

function Wait-ApiRateLimit {
    param(
        [string]$Key,
        [double]$MinimumIntervalSeconds
    )

    if ([string]::IsNullOrWhiteSpace($Key) -or $MinimumIntervalSeconds -le 0) {
        return
    }

    $now = [DateTime]::UtcNow
    if ($lastRequestByLimit.ContainsKey($Key)) {
        $elapsed = ($now - $lastRequestByLimit[$Key]).TotalSeconds
        if ($elapsed -lt $MinimumIntervalSeconds) {
            $waitSeconds = $MinimumIntervalSeconds - $elapsed
            $hourlyLimit = if ($Key -eq 'WorkspaceAccess') { 200 } elseif ($Key -eq 'PowerBIMetadataScan') { 500 } else { 0 }
            Write-ScanWait -Reason rateLimit -Seconds $waitSeconds -Api $Key -HourlyLimit $hourlyLimit
            Start-Sleep -Milliseconds ([math]::Ceiling($waitSeconds * 1000))
            Write-ScanWaitEnd
        }
    }
    $lastRequestByLimit[$Key] = [DateTime]::UtcNow
}

function Get-RetryDelaySeconds {
    param(
        [object]$Response,
        [int]$Attempt
    )

    $retryAfter = if ($null -ne $Response) { $Response.Headers['Retry-After'] } else { $null }
    $delaySeconds = 0
    if ($retryAfter -and [int]::TryParse([string]$retryAfter, [ref]$delaySeconds)) {
        return [math]::Max(1, $delaySeconds)
    }

    $retryAt = [DateTime]::MinValue
    if ($retryAfter -and [DateTime]::TryParse([string]$retryAfter, [ref]$retryAt)) {
        return [math]::Max(1, [math]::Ceiling(($retryAt.ToUniversalTime() - [DateTime]::UtcNow).TotalSeconds))
    }

    return [math]::Min(300, [math]::Pow(2, $Attempt + 1))
}

function Test-TransientApiError {
    param(
        [int]$StatusCode,
        [Exception]$Exception
    )

    if ($StatusCode -in @(408, 429, 500, 502, 503, 504)) {
        return $true
    }

    $currentException = $Exception
    while ($null -ne $currentException) {
        if ($currentException -is [System.Net.Http.HttpRequestException] -or $currentException -is [System.Net.WebException]) {
            return $true
        }
        $currentException = $currentException.InnerException
    }
    return $false
}

function Invoke-ApiRequest {
    param(
        [Parameter(Mandatory)][ValidateSet('Get', 'Post')][string]$Method,
        [Parameter(Mandatory)][string]$Uri,
        [Parameter(Mandatory)][hashtable]$Headers,
        [object]$Body,
        [string]$TokenResource,
        [string]$RateLimitKey,
        [double]$MinimumIntervalSeconds = 0,
        [int]$MaxRetries = 8
    )

    for ($attempt = 0; $attempt -le $MaxRetries; $attempt++) {
        try {
            Wait-ApiRateLimit -Key $RateLimitKey -MinimumIntervalSeconds $MinimumIntervalSeconds
            $parameters = @{
                Method      = $Method
                Uri         = $Uri
                Headers     = $Headers
                ContentType = 'application/json'
            }
            if ($null -ne $Body) {
                $parameters.Body = $Body | ConvertTo-Json -Depth 10
            }

            return Invoke-RestMethod @parameters
        }
        catch {
            $response = $_.Exception.Response
            $statusCode = if ($null -ne $response) { [int]$response.StatusCode } else { 0 }
            if ($statusCode -eq 401 -and $TokenResource -and $attempt -lt $MaxRetries) {
                Write-Warning "Access token expired. Acquiring a new token for $TokenResource."
                $Headers.Authorization = "Bearer $(Get-AzCliAccessToken -Resource $TokenResource)"
                continue
            }

            $isTransient = Test-TransientApiError -StatusCode $statusCode -Exception $_.Exception
            if (-not $isTransient -or $attempt -eq $MaxRetries) {
                throw
            }

            $delaySeconds = Get-RetryDelaySeconds -Response $response -Attempt $attempt
            Write-Warning "API request failed with status $statusCode. Retrying in $delaySeconds seconds (attempt $($attempt + 1) of $MaxRetries)."
            Write-ScanWait -Reason retry -Seconds $delaySeconds -Api $RateLimitKey -HourlyLimit $(if ($RateLimitKey -eq 'WorkspaceAccess') { 200 } elseif ($RateLimitKey -eq 'PowerBIMetadataScan') { 500 } else { 0 })
            Start-Sleep -Seconds $delaySeconds
            Write-ScanWaitEnd
        }
    }
}

function Get-PagedFabricWorkspaces {
    param([Parameter(Mandatory)][hashtable]$Headers)

    $workspaceType = if ($IncludePersonalWorkspaces) { $null } else { 'workspace' }
    $uri = "$fabricBaseUrl/admin/workspaces?state=active"
    if ($workspaceType) {
        $uri += "&type=$workspaceType"
    }

    $workspaces = [System.Collections.Generic.List[object]]::new()
    while ($uri) {
        $response = Invoke-ApiRequest -Method Get -Uri $uri -Headers $Headers -TokenResource $fabricResource
        foreach ($workspace in $response.workspaces) {
            $workspaces.Add($workspace)
            if ($WorkspaceLimit -gt 0 -and $workspaces.Count -ge $WorkspaceLimit) {
                return $workspaces
            }
        }
        $uri = $response.continuationUri
    }

    return $workspaces
}

function Get-WorkspaceAssignments {
    param(
        [Parameter(Mandatory)][object[]]$Workspaces,
        [Parameter(Mandatory)][hashtable]$Headers,
        [Parameter(Mandatory)][string]$CheckpointPath
    )

    $assignments = [System.Collections.Generic.List[object]]::new()
    $failures = [System.Collections.Generic.List[object]]::new()
    $completedWorkspaceIds = [System.Collections.Generic.HashSet[string]]::new()
    if (Test-Path $CheckpointPath) {
        foreach ($line in Get-Content -Path $CheckpointPath) {
            if ([string]::IsNullOrWhiteSpace($line)) { continue }
            try {
                $checkpoint = $line | ConvertFrom-Json
            }
            catch {
                Write-Warning "Ignoring an incomplete workspace checkpoint line; that workspace will be scanned again."
                continue
            }
            if ($checkpoint.TenantId -ne $TenantId) { continue }
            [void]$completedWorkspaceIds.Add([string]$checkpoint.WorkspaceId)
            foreach ($assignment in @($checkpoint.Assignments)) { $assignments.Add($assignment) }
            if ($null -ne $checkpoint.Failure) { $failures.Add($checkpoint.Failure) }
        }
        if ($completedWorkspaceIds.Count -gt 0) {
            Write-Host "Resuming workspace access discovery with $($completedWorkspaceIds.Count) completed workspaces."
        }
        else {
            Remove-Item -Path $CheckpointPath -Force
        }
    }
    $index = 0

    foreach ($workspace in $Workspaces) {
        $index++
        if ($completedWorkspaceIds.Contains([string]$workspace.id)) { continue }
        Write-Progress -Activity 'Reading workspace access' -Status "$index of $($Workspaces.Count): $($workspace.name)" -PercentComplete (($index / $Workspaces.Count) * 100)
        Write-ScanProgress -Percent (20 + [math]::Floor(($index / $Workspaces.Count) * 50)) -Stage "Workspace $index af $($Workspaces.Count): $($workspace.name)" -Current $index -Total $Workspaces.Count
        $workspaceAssignments = [System.Collections.Generic.List[object]]::new()
        $failure = $null
        try {
            $response = Invoke-ApiRequest -Method Get -Uri "$fabricBaseUrl/admin/workspaces/$($workspace.id)/users" -Headers $Headers -TokenResource $fabricResource -RateLimitKey 'WorkspaceAccess' -MinimumIntervalSeconds 18.1
            foreach ($access in $response.accessDetails) {
                $principal = $access.principal
                $assignment = [pscustomobject]@{
                    WorkspaceId      = $workspace.id
                    WorkspaceName    = $workspace.name
                    WorkspaceType    = $workspace.type
                    PrincipalId      = $principal.id
                    DisplayName      = $principal.displayName
                    PrincipalType    = $principal.type
                    UserPrincipalName = $principal.userDetails.userPrincipalName
                    GroupType        = $principal.groupDetails.groupType
                    AadAppId         = $principal.servicePrincipalDetails.aadAppId
                    WorkspaceRole    = $access.workspaceAccessDetails.workspaceRole
                }
                $workspaceAssignments.Add($assignment)
                $assignments.Add($assignment)
            }
        }
        catch {
            $response = $_.Exception.Response
            $statusCode = if ($null -ne $response) { [int]$response.StatusCode } else { 0 }
            if (Test-TransientApiError -StatusCode $statusCode -Exception $_.Exception) {
                throw
            }
            $failure = [pscustomobject]@{
                WorkspaceId   = $workspace.id
                WorkspaceName = $workspace.name
                Error         = $_.Exception.Message
            }
            $failures.Add($failure)
        }
        [ordered]@{
            TenantId    = $TenantId
            WorkspaceId = $workspace.id
            Assignments = @($workspaceAssignments)
            Failure     = $failure
        } | ConvertTo-Json -Depth 20 -Compress | Add-Content -Path $CheckpointPath -Encoding utf8
    }
    Write-Progress -Activity 'Reading workspace access' -Completed

    return @{
        Assignments = $assignments
        Failures    = $failures
    }
}

function Get-PowerBIArtifactUsers {
    param(
        [Parameter(Mandatory)][object[]]$Workspaces,
        [Parameter(Mandatory)][hashtable]$Headers,
        [Parameter(Mandatory)][string]$ResultPath,
        [Parameter(Mandatory)][string]$CheckpointPath
    )

    $completedWorkspaceIds = [System.Collections.Generic.HashSet[string]]::new()
    $scanCount = 0
    if (Test-Path $CheckpointPath) {
        foreach ($line in Get-Content -Path $CheckpointPath) {
            if ([string]::IsNullOrWhiteSpace($line)) { continue }
            try {
                $checkpoint = $line | ConvertFrom-Json
            }
            catch {
                Write-Warning "Ignoring an incomplete metadata checkpoint line; that batch will be scanned again."
                continue
            }
            if ($checkpoint.TenantId -ne $TenantId) { continue }
            foreach ($workspaceId in @($checkpoint.WorkspaceIds)) { [void]$completedWorkspaceIds.Add([string]$workspaceId) }
            $scanCount++
        }
        if ($completedWorkspaceIds.Count -gt 0) {
            Write-Host "Resuming Power BI metadata discovery with $($completedWorkspaceIds.Count) completed workspaces."
        }
        else {
            Remove-Item -Path $CheckpointPath -Force
            Remove-Item -Path $ResultPath -Force -ErrorAction SilentlyContinue
        }
    }
    else {
        Remove-Item -Path $ResultPath -Force -ErrorAction SilentlyContinue
    }

    $workspaceIds = @($Workspaces | ForEach-Object { $_.id })
    $pendingWorkspaceIds = @($workspaceIds | Where-Object { -not $completedWorkspaceIds.Contains([string]$_) })
    for ($offset = 0; $offset -lt $pendingWorkspaceIds.Count; $offset += 100) {
        $end = [math]::Min($offset + 99, $pendingWorkspaceIds.Count - 1)
        $chunk = @($pendingWorkspaceIds[$offset..$end])
        $scan = Invoke-ApiRequest -Method Post -Uri "$powerBiBaseUrl/admin/workspaces/getInfo?getArtifactUsers=true" -Headers $Headers -Body @{ workspaces = @($chunk) } -TokenResource $powerBiResource -RateLimitKey 'PowerBIMetadataScan' -MinimumIntervalSeconds 7.3
        $statusUri = "$powerBiBaseUrl/admin/workspaces/scanStatus/$($scan.id)"

        do {
            Write-ScanWait -Reason metadataProcessing -Seconds 30 -Api 'PowerBIMetadataScan' -HourlyLimit 500
            Start-Sleep -Seconds 30
            Write-ScanWaitEnd
            $status = Invoke-ApiRequest -Method Get -Uri $statusUri -Headers $Headers -TokenResource $powerBiResource -RateLimitKey 'PowerBIMetadataScan' -MinimumIntervalSeconds 7.3
        } while ($status.status -in @('NotStarted', 'Running'))

        if ($status.status -ne 'Succeeded') {
            throw "Power BI metadata scan $($scan.id) ended with status '$($status.status)'."
        }

        $scanResult = Invoke-ApiRequest -Method Get -Uri "$powerBiBaseUrl/admin/workspaces/scanResult/$($scan.id)" -Headers $Headers -TokenResource $powerBiResource -RateLimitKey 'PowerBIMetadataScan' -MinimumIntervalSeconds 7.3
        $scanResult | ConvertTo-Json -Depth 100 -Compress | Add-Content -Path $ResultPath -Encoding utf8
        [ordered]@{ TenantId = $TenantId; WorkspaceIds = $chunk } | ConvertTo-Json -Compress | Add-Content -Path $CheckpointPath -Encoding utf8
        $scanCount++
    }

    return $scanCount
}

if ($env:FABRIC_DISCOVERY_LOAD_FUNCTIONS_ONLY -eq '1') {
    return
}

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw 'Azure CLI (az) is required and was not found in PATH.'
}

New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
$resolvedOutputPath = (Resolve-Path $OutputPath).Path

Write-ScanProgress -Percent 5 -Stage 'Henter Fabric-token'
Write-Host 'Acquiring a delegated Fabric token from Azure CLI...'
$fabricHeaders = @{ Authorization = "Bearer $(Get-AzCliAccessToken -Resource $fabricResource)" }

Write-ScanProgress -Percent 10 -Stage 'Henter workspaces'
Write-Host 'Reading tenant workspaces...'
$workspaces = @(Get-PagedFabricWorkspaces -Headers $fabricHeaders)
Write-ScanEstimate -WorkspaceCount $workspaces.Count -IncludeArtifacts $IncludePowerBIArtifactUsers.IsPresent
Write-ScanProgress -Percent 20 -Stage "Læser adgang for $($workspaces.Count) workspaces"
$workspaceCheckpointPath = Join-Path $resolvedOutputPath 'workspace-access.checkpoint.ndjson'
$workspaceResult = Get-WorkspaceAssignments -Workspaces $workspaces -Headers $fabricHeaders -CheckpointPath $workspaceCheckpointPath

ConvertTo-Json -InputObject @($workspaces) -Depth 20 | Set-Content -Path (Join-Path $resolvedOutputPath 'workspaces.json') -Encoding utf8
$assignmentsPath = Join-Path $resolvedOutputPath 'workspace-role-assignments.csv'
if ($workspaceResult.Assignments.Count -gt 0) {
    $workspaceResult.Assignments | Export-Csv -Path $assignmentsPath -NoTypeInformation -Encoding utf8
}
else {
    '"WorkspaceId","WorkspaceName","WorkspaceType","PrincipalId","DisplayName","PrincipalType","UserPrincipalName","GroupType","AadAppId","WorkspaceRole"' | Set-Content -Path $assignmentsPath -Encoding utf8
}

$failuresPath = Join-Path $resolvedOutputPath 'workspace-errors.csv'
if ($workspaceResult.Failures.Count -gt 0) {
    $workspaceResult.Failures | Export-Csv -Path $failuresPath -NoTypeInformation -Encoding utf8
}
else {
    '"WorkspaceId","WorkspaceName","Error"' | Set-Content -Path $failuresPath -Encoding utf8
}

$artifactScanCount = 0
if ($IncludePowerBIArtifactUsers -and $workspaces.Count -gt 0) {
    Write-ScanProgress -Percent 72 -Stage 'Scanner Power BI artifact-brugere'
    Write-Host 'Running Power BI metadata scans with artifact users enabled...'
    $powerBiHeaders = @{ Authorization = "Bearer $(Get-AzCliAccessToken -Resource $powerBiResource)" }
    $scanResultPath = Join-Path $resolvedOutputPath 'powerbi-artifact-user-scans.ndjson'
    $artifactCheckpointPath = Join-Path $resolvedOutputPath 'powerbi-artifact-users.checkpoint.ndjson'
    $artifactScanCount = Get-PowerBIArtifactUsers -Workspaces $workspaces -Headers $powerBiHeaders -ResultPath $scanResultPath -CheckpointPath $artifactCheckpointPath
}

$coverage = [ordered]@{
    generatedAtUtc = [DateTime]::UtcNow.ToString('o')
    tenantId = $TenantId
    readOnly = $true
    counts = [ordered]@{
        workspaces = $workspaces.Count
        workspaceRoleAssignments = $workspaceResult.Assignments.Count
        workspaceErrors = $workspaceResult.Failures.Count
        powerBiArtifactScanBatches = $artifactScanCount
    }
    covered = @(
        'Active Fabric workspaces returned by the Fabric Admin API'
        'Direct workspace role assignments for users, groups, service principals, profiles, and entire-tenant principals'
        'Power BI artifact users returned by metadata scanning when IncludePowerBIArtifactUsers is enabled'
    )
    notCovered = @(
        'Effective access inherited through nested Microsoft Entra groups'
        'Generic Fabric item-level sharing outside the Power BI artifact users exposed by scanner APIs'
        'OneLake security role definitions and members'
        'Warehouse, SQL analytics endpoint, and SQL database GRANT, DENY, roles, RLS, and object permissions'
        'Semantic model RLS and OLS role membership'
        'KQL database and Eventhouse security roles'
        'Gateway, connection, app audience, capacity, and tenant administrator assignments'
    )
    apiNotes = @(
        'List Workspace Access Details is a preview API and is limited to 200 requests per hour.'
        'Power BI metadata scanning supports at most 100 workspace IDs per scan request and 500 scan requests per hour.'
    )
}
$coverage | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $resolvedOutputPath 'coverage-report.json') -Encoding utf8

Remove-Item -Path $workspaceCheckpointPath -Force -ErrorAction SilentlyContinue
if ($artifactCheckpointPath) {
    Remove-Item -Path $artifactCheckpointPath -Force -ErrorAction SilentlyContinue
}

Write-ScanProgress -Percent 95 -Stage 'Discovery-output er klar'
Write-Host "Discovery completed. Output: $resolvedOutputPath"
Write-Host "Workspaces: $($workspaces.Count); assignments: $($workspaceResult.Assignments.Count); errors: $($workspaceResult.Failures.Count)"