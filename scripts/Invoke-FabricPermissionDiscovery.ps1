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

function Write-ScanProgress {
    param(
        [Parameter(Mandatory)][ValidateRange(0, 100)][int]$Percent,
        [Parameter(Mandatory)][string]$Stage
    )

    Write-Output "FABRIC_PROGRESS $(@{ percent = $Percent; stage = $Stage } | ConvertTo-Json -Compress)"
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

function Invoke-ApiRequest {
    param(
        [Parameter(Mandatory)][ValidateSet('Get', 'Post')][string]$Method,
        [Parameter(Mandatory)][string]$Uri,
        [Parameter(Mandatory)][hashtable]$Headers,
        [object]$Body,
        [int]$MaxRetries = 8
    )

    for ($attempt = 0; $attempt -le $MaxRetries; $attempt++) {
        try {
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
            $statusCode = [int]$_.Exception.Response.StatusCode
            if ($statusCode -ne 429 -or $attempt -eq $MaxRetries) {
                throw
            }

            $retryAfter = $_.Exception.Response.Headers['Retry-After']
            $delaySeconds = if ($retryAfter) { [int]$retryAfter } else { [math]::Min(300, [math]::Pow(2, $attempt + 1)) }
            Write-Warning "API rate limit reached. Retrying in $delaySeconds seconds."
            Start-Sleep -Seconds $delaySeconds
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
        $response = Invoke-ApiRequest -Method Get -Uri $uri -Headers $Headers
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
        [Parameter(Mandatory)][hashtable]$Headers
    )

    $assignments = [System.Collections.Generic.List[object]]::new()
    $failures = [System.Collections.Generic.List[object]]::new()
    $index = 0

    foreach ($workspace in $Workspaces) {
        $index++
        Write-Progress -Activity 'Reading workspace access' -Status "$index of $($Workspaces.Count): $($workspace.name)" -PercentComplete (($index / $Workspaces.Count) * 100)
        Write-ScanProgress -Percent (20 + [math]::Floor(($index / $Workspaces.Count) * 50)) -Stage "Workspace $index af $($Workspaces.Count): $($workspace.name)"
        try {
            $response = Invoke-ApiRequest -Method Get -Uri "$fabricBaseUrl/admin/workspaces/$($workspace.id)/users" -Headers $Headers
            foreach ($access in $response.accessDetails) {
                $principal = $access.principal
                $assignments.Add([pscustomobject]@{
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
                })
            }
        }
        catch {
            $failures.Add([pscustomobject]@{
                WorkspaceId   = $workspace.id
                WorkspaceName = $workspace.name
                Error         = $_.Exception.Message
            })
        }
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
        [Parameter(Mandatory)][string]$ResultPath
    )

    Remove-Item -Path $ResultPath -Force -ErrorAction SilentlyContinue
    $scanCount = 0
    $workspaceIds = @($Workspaces | ForEach-Object { $_.id })
    for ($offset = 0; $offset -lt $workspaceIds.Count; $offset += 100) {
        $end = [math]::Min($offset + 99, $workspaceIds.Count - 1)
        $chunk = @($workspaceIds[$offset..$end])
        $scan = Invoke-ApiRequest -Method Post -Uri "$powerBiBaseUrl/admin/workspaces/getInfo?getArtifactUsers=true" -Headers $Headers -Body @{ workspaces = @($chunk) }
        $statusUri = "$powerBiBaseUrl/admin/workspaces/scanStatus/$($scan.id)"

        do {
            Start-Sleep -Seconds 30
            $status = Invoke-ApiRequest -Method Get -Uri $statusUri -Headers $Headers
        } while ($status.status -in @('NotStarted', 'Running'))

        if ($status.status -ne 'Succeeded') {
            throw "Power BI metadata scan $($scan.id) ended with status '$($status.status)'."
        }

        $scanResult = Invoke-ApiRequest -Method Get -Uri "$powerBiBaseUrl/admin/workspaces/scanResult/$($scan.id)" -Headers $Headers
        $scanResult | ConvertTo-Json -Depth 100 -Compress | Add-Content -Path $ResultPath -Encoding utf8
        $scanCount++
    }

    return $scanCount
}

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw 'Azure CLI (az) is required and was not found in PATH.'
}

New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
$resolvedOutputPath = (Resolve-Path $OutputPath).Path

Write-ScanProgress -Percent 5 -Stage 'Henter Fabric-token'
Write-Host 'Acquiring a delegated Fabric token from Azure CLI...'
$fabricHeaders = @{ Authorization = "Bearer $(Get-AzCliAccessToken -Resource 'https://api.fabric.microsoft.com')" }

Write-ScanProgress -Percent 10 -Stage 'Henter workspaces'
Write-Host 'Reading tenant workspaces...'
$workspaces = @(Get-PagedFabricWorkspaces -Headers $fabricHeaders)
Write-ScanProgress -Percent 20 -Stage "Læser adgang for $($workspaces.Count) workspaces"
$workspaceResult = Get-WorkspaceAssignments -Workspaces $workspaces -Headers $fabricHeaders

$workspaces | ConvertTo-Json -Depth 20 | Set-Content -Path (Join-Path $resolvedOutputPath 'workspaces.json') -Encoding utf8
$workspaceResult.Assignments | Export-Csv -Path (Join-Path $resolvedOutputPath 'workspace-role-assignments.csv') -NoTypeInformation -Encoding utf8
$workspaceResult.Failures | Export-Csv -Path (Join-Path $resolvedOutputPath 'workspace-errors.csv') -NoTypeInformation -Encoding utf8

$artifactScanCount = 0
if ($IncludePowerBIArtifactUsers -and $workspaces.Count -gt 0) {
    Write-ScanProgress -Percent 72 -Stage 'Scanner Power BI artifact-brugere'
    Write-Host 'Running Power BI metadata scans with artifact users enabled...'
    $powerBiHeaders = @{ Authorization = "Bearer $(Get-AzCliAccessToken -Resource 'https://analysis.windows.net/powerbi/api')" }
    $scanResultPath = Join-Path $resolvedOutputPath 'powerbi-artifact-user-scans.ndjson'
    $artifactScanCount = Get-PowerBIArtifactUsers -Workspaces $workspaces -Headers $powerBiHeaders -ResultPath $scanResultPath
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

Write-ScanProgress -Percent 95 -Stage 'Discovery-output er klar'
Write-Host "Discovery completed. Output: $resolvedOutputPath"
Write-Host "Workspaces: $($workspaces.Count); assignments: $($workspaceResult.Assignments.Count); errors: $($workspaceResult.Failures.Count)"