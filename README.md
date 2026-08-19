# Fabric User Migration Application

Dette repository starter med en read-only discovery-spike mod **Tenant A**. Formaalet er at validere, hvilke bruger- og adgangsdata Microsoft Fabric faktisk udstiller, foer vi designer selve webapplikationen og skrivefasen mod Tenant B.

## Foreloebig konklusion

API'erne kan hente en vaesentlig del af grundlaget, men ikke alle effektive Fabric-rettigheder gennem et enkelt API:

| Sikkerhedslag | Kan laeses tenant-wide? | API/status |
| --- | --- | --- |
| Workspaces | Ja | Fabric Admin `GET /v1/admin/workspaces` |
| Direkte workspace-roller | Ja | Fabric Admin `GET /v1/admin/workspaces/{id}/users`, preview |
| Power BI artifact users | Delvist | Power BI scanner API med `getArtifactUsers=true` |
| Generisk item sharing for alle Fabric item-typer | Ikke dokumenteret som et samlet tenant-wide read API | Kraever yderligere afklaring eller item-specifikke API'er |
| Entra-gruppemedlemskab og effektiv arv | Ja, men via Microsoft Graph | Ikke en del af Fabric API'et |
| OneLake security-roller | Separat sikkerhedsmodel | Ikke daekket af denne spike |
| SQL grants, database-roller og SQL RLS | Separat SQL-sikkerhedsmodel | Skal udlaeses gennem SQL pr. endpoint/database |
| Semantic model RLS/OLS | Separat model-sikkerhed | Kraever Power BI/XMLA-specifik discovery |
| KQL/Eventhouse-roller | Separat Kusto-sikkerhed | Kraever KQL/Kusto-specifik discovery |
| Gateways, connections, apps og capacity admins | Separate administrationsflader | Kraever egne API'er |

Det betyder, at en produktionsloesning boer opbygge et samlet rettighedskatalog fra flere collectors. Workspace-roller er et godt og testbart foerste trin, men de er ikke lig med en komplet effektiv adgangsmodel.

## Forudsaetninger i Tenant A

1. Installer [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli-windows).
2. Brugeren, der logger ind, skal vaere Fabric administrator.
3. Ved scanner-test skal de relevante admin API-indstillinger for metadata scanning vaere aktiveret.
4. Log ind i Tenant A uden krav om et Azure-abonnement:

```powershell
az login --tenant <TENANT-A-ID> --allow-no-subscriptions
```

Spiken bruger delegated user authentication. Der gemmes ingen access tokens i outputtet.

## Koer discovery

Koer foerst en lille pilot paa fem workspaces:

```powershell
.\scripts\Invoke-FabricPermissionDiscovery.ps1 `
    -TenantId '<TENANT-A-ID>' `
    -WorkspaceLimit 5
```

Koer derefter alle aktive, delte workspaces og inkluder Power BI artifact users:

```powershell
.\scripts\Invoke-FabricPermissionDiscovery.ps1 `
    -TenantId '<TENANT-A-ID>' `
    -IncludePowerBIArtifactUsers
```

Tilfoej `-IncludePersonalWorkspaces`, hvis My Workspaces ogsaa skal med. Scriptet holder mindst 18,1 sekunder mellem workspace access-kald og mindst 7,3 sekunder mellem Power BI metadata-kald. Det holder koerslen under graenserne paa henholdsvis 200 og 500 requests i timen med en lille sikkerhedsmargin. En scan af 1.000 workspace access-detaljer tager derfor mindst cirka fem timer.

Ved 429, midlertidige netvaerksfejl og 5xx-svar respekterer scriptet `Retry-After` og bruger ellers eksponentiel backoff. Udlobne access tokens fornyes gennem Azure CLI. Efter hvert workspace og hver metadata-batch skrives et tenant-specifikt checkpoint. Hvis processen stoppes, fortsaetter naeste scan fra seneste checkpoint; checkpoints slettes efter en fuldt gennemfoert discovery, saa efterfoelgende planlagte scans stadig henter friske data.

## Output

Filer skrives som standard under `artifacts/fabric-permission-discovery`:

- `workspaces.json`: ra workspace-inventarliste.
- `workspace-role-assignments.csv`: normaliserede direkte workspace-roller.
- `workspace-errors.csv`: workspaces der ikke kunne laeses.
- `powerbi-artifact-user-scans.ndjson`: raa scanner-resultater, en linje pr. batch paa hoejst 100 workspaces.
- `coverage-report.json`: optaelling og eksplicit liste over daekkede og ikke-daekkede sikkerhedslag.

Start med at kontrollere, at antal workspaces matcher Fabric Admin-portalen, og stikproev derefter rollelisten mod **Manage access** i 2-3 workspaces. Den kontrol afgør, om preview-endpointet er stabilt nok i kundens tenant til naeste fase.

## Indekseret dashboard

Dashboardet bruger en normaliseret SQLite-database og paginerede FastAPI-endpoints. Browseren indlaeser derfor aldrig hele tenant-snapshot'et. Importer det seneste discovery-output og start serveren fra repository-roden:

```powershell
python -m pip install -r requirements.txt
python server\import_snapshot.py
python -m uvicorn server.app:app --host 127.0.0.1 --port 8080
```

Aabn derefter `http://localhost:8080/` eller `http://localhost:8080/web/`. Dashboardet og API'et er read-only. En ny import bygges i en midlertidig database og erstatter foerst den aktive database, naar importen er gennemfoert.

Et nyt scan kan startes fra dashboardets **Start scan**-visning. Vaelg **Log ind med Microsoft**, gennemfoer det personlige Microsoft-login i browservinduet, og vaelg derefter en tenant fra listen over tenants, kontoen har adgang til. Azure CLI-sessionen bruges af discovery-scriptet; adgangskoder og access tokens sendes ikke gennem dashboardet.

### Skalering

- Discovery skriver scannerresultater batchvist som NDJSON, saa hele tenant-resultatet ikke holdes i PowerShell-hukommelsen.
- Workspace access scannes sekventielt med 18,1 sekunders pacing og genoptages fra `workspace-access.checkpoint.ndjson` efter en afbrydelse.
- Power BI metadata opdeles i batches paa hoejst 100 workspace-ID'er, paces til 500 API-kald i timen og genoptages fra `powerbi-artifact-users.checkpoint.ndjson`.
- Checkpoint-filerne er kun interne arbejdsfiler og fjernes automatisk efter en gennemfoert discovery.
- Importeren streamer JSON/NDJSON ind i normaliserede SQLite-tabeller med indeks og FTS5-soegning.
- API'et returnerer maksimalt 100 permissions ad gangen; dashboardet bruger 50.
- Soegning er debounced, og tidligere requests annulleres i browseren.
- Koer `python tests\scale_benchmark.py` for en lokal benchmark med 10.000 users og 100.000 permissions.

SQLite er velegnet til en enkelt read-only applikationsinstans og mange millioner rettighedsrækker. Hvis loesningen senere skal betjene mange samtidige dashboard-brugere eller flere app-instanser, boer samme normaliserede model flyttes til Azure SQL eller PostgreSQL, og snapshot-importen koeres som et separat job.

## Docker

Byg og start applikationen med Docker Compose fra repository-roden:

```powershell
docker compose up --build -d
docker compose ps
```

Compose monterer `artifacts/fabric-permission-discovery` read-only og gemmer den importerede SQLite-database i volume `fabric-data`. Aabn `http://localhost:8080/`. Naar discovery-snapshottet er opdateret, kan databasen genimporteres ved naeste start:

```powershell
$env:FORCE_SNAPSHOT_IMPORT = 'true'
docker compose up --build -d
Remove-Item Env:FORCE_SNAPSHOT_IMPORT
```

Stop applikationen med `docker compose down`. Tilfoej `--volumes`, hvis den importerede database ogsaa skal slettes.

## Dev container

Repository'et indeholder en VS Code dev container baseret paa development-targetet i `Dockerfile`. Koer **Dev Containers: Reopen in Container**, og start derefter serveren i container-terminalen:

```bash
python server/import_snapshot.py
python -m uvicorn server.app:app --host 0.0.0.0 --port 8080 --reload
```

Port `8080` viderestilles automatisk. Tests kan koeres med `python -m pytest`.

## Officiel dokumentation

- [List Workspaces](https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-workspaces)
- [List Workspace Access Details](https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-workspace-access-details)
- [Metadata scanning overview](https://learn.microsoft.com/fabric/governance/metadata-scanning-overview)
- [PostWorkspaceInfo](https://learn.microsoft.com/rest/api/power-bi/admin/workspace-info-post-workspace-info)
- [Fabric permission model](https://learn.microsoft.com/fabric/security/permission-model)
- [Service principal authentication for admin APIs](https://learn.microsoft.com/fabric/admin/enable-service-principal-admin-apis)