# Fabric Access Atlas

Fabric Access Atlas is a read-only Microsoft Fabric discovery dashboard. It signs in with a personal Microsoft account, scans the tenants available to that account, and stores a normalized permission snapshot in SQLite for fast search and review.

The Docker image includes the application, Python dependencies, Azure CLI, PowerShell, and the discovery script. A user only needs Docker with Docker Compose.

## Quick start

From the repository root, run:

```bash
docker compose up --build -d
```

Open [http://localhost:8080](http://localhost:8080), select **Start scan**, and then:

1. Select **Sign in with Microsoft**, open the Microsoft link shown by the dashboard, and enter the displayed one-time code.
2. Choose one of the tenants available to the signed-in account.
3. Keep the workspace limit at `0` to scan every active workspace, or enter a smaller number for a pilot scan.
4. Choose whether to include Power BI artifact users and personal workspaces.
5. Start the scan.

No snapshot files, local Python installation, Azure CLI installation, or PowerShell installation are required. On first startup, the container creates an empty dashboard database. The first completed scan replaces it with live tenant data.

Check the service:

```bash
docker compose ps
docker compose logs -f app
```

Stop it with:

```bash
docker compose down
```

## Persistent data

Docker Compose creates three named volumes:

| Volume | Contents |
| --- | --- |
| `fabric-data` | The normalized SQLite dashboard database |
| `fabric-artifacts` | Discovery output and resumable scan checkpoints |
| `azure-config` | The Azure CLI login session |

Normal image rebuilds and container restarts preserve all three volumes. To remove all local application data and the saved Microsoft login, run:

```bash
docker compose down --volumes
```

To rebuild the SQLite database from the existing discovery files, run:

```bash
FORCE_SNAPSHOT_IMPORT=true docker compose up -d
```

Then start it normally again so future restarts do not force another import:

```bash
docker compose up -d
```

## Authentication and permissions

Discovery uses delegated Azure CLI authentication. Passwords and access tokens are not sent through the dashboard or written to discovery output.

The signed-in account must have permission to call the Fabric administrator APIs. In most environments this means the account is a Fabric administrator. Power BI metadata scanning must also be enabled in the tenant settings when artifact-user discovery is selected.

The tenant selector lists tenants available to the signed-in Microsoft account. Azure subscriptions are not required.

## What the scan collects

| Security layer | Coverage | Source |
| --- | --- | --- |
| Active workspaces | Included | Fabric Admin `GET /v1/admin/workspaces` |
| Direct workspace roles | Included | Fabric Admin workspace access details preview API |
| Power BI artifact users | Optional | Power BI metadata scanner with `getArtifactUsers=true` |
| Nested Microsoft Entra group inheritance | Not expanded | Requires Microsoft Graph |
| Generic sharing for every Fabric item type | Not fully exposed tenant-wide | Requires additional or item-specific APIs |
| OneLake security roles | Not included | Separate OneLake security model |
| SQL grants, roles, RLS, and object permissions | Not included | Requires SQL discovery per endpoint or database |
| Semantic model RLS and OLS | Not included | Requires Power BI or XMLA-specific discovery |
| KQL database and Eventhouse roles | Not included | Requires KQL or Kusto-specific discovery |
| Gateways, connections, apps, capacities, and tenant admins | Not included | Separate administration APIs |

Workspace roles are a useful migration baseline, but they are not a complete effective-access model. A production migration should combine multiple specialized collectors.

## Large tenant behavior

The scanner is designed for long-running tenant discovery:

- Workspace access calls are paced at 18.1 seconds to remain below the preview API limit of 200 requests per hour.
- Power BI metadata requests contain at most 100 workspace IDs and are paced below 500 requests per hour.
- HTTP 429 responses, temporary network failures, and transient 5xx responses are retried using `Retry-After` or exponential backoff.
- Expired access tokens are refreshed through Azure CLI.
- Workspace and metadata progress is checkpointed after each completed unit of work.
- An interrupted scan resumes from its tenant-specific checkpoints.
- The dashboard shows workspace progress, API waits, and an estimated duration based on workspace count and metadata batches.

Because of the API limit, scanning access details for 1,000 workspaces takes at least about five hours. Keep the container running until the scan completes.

## Discovery output

The `fabric-artifacts` volume contains:

- `workspaces.json`: raw workspace inventory.
- `workspace-role-assignments.csv`: normalized direct workspace roles.
- `workspace-errors.csv`: workspaces that could not be read.
- `powerbi-artifact-user-scans.ndjson`: metadata scanner results, one line per batch.
- `coverage-report.json`: covered and unsupported security layers.
- `*.checkpoint.ndjson`: internal resume data, removed after a successful complete scan.

The importer streams JSON and NDJSON into indexed SQLite tables. The API is paginated and returns at most 100 permissions per request; the dashboard requests 50 at a time.

## Local development

The recommended development environment is the included VS Code dev container. Select **Dev Containers: Reopen in Container**, then run:

```bash
python server/import_snapshot.py
python -m uvicorn server.app:app --host 0.0.0.0 --port 8080 --reload
```

Run tests with:

```bash
python -m pytest
```

For a local scale check with 10,000 users and 100,000 permissions:

```bash
python tests/scale_benchmark.py
```

## Manual discovery

Docker users should normally start scans from the dashboard. To run the collector directly in a prepared PowerShell environment:

```powershell
./scripts/Invoke-FabricPermissionDiscovery.ps1 `
    -TenantId '<TENANT-ID>' `
    -IncludePowerBIArtifactUsers
```

Add `-WorkspaceLimit 5` for a small pilot or `-IncludePersonalWorkspaces` to include My Workspaces. Output defaults to `artifacts/fabric-permission-discovery`.

## API and operational notes

- The dashboard and discovery operations are read-only against Microsoft Fabric.
- Snapshot imports are built in a temporary SQLite database and replace the active database only after a successful import.
- SQLite is suitable for one application instance and millions of permission rows.
- Multiple application instances or many concurrent users should use PostgreSQL or Azure SQL and a separate import worker.
- The health endpoint is available at [http://localhost:8080/api/health](http://localhost:8080/api/health).

## Microsoft documentation

- [List Workspaces](https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-workspaces)
- [List Workspace Access Details](https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-workspace-access-details)
- [Metadata scanning overview](https://learn.microsoft.com/fabric/governance/metadata-scanning-overview)
- [PostWorkspaceInfo](https://learn.microsoft.com/rest/api/power-bi/admin/workspace-info-post-workspace-info)
- [Fabric permission model](https://learn.microsoft.com/fabric/security/permission-model)
- [Service principal authentication for admin APIs](https://learn.microsoft.com/fabric/admin/enable-service-principal-admin-apis)
