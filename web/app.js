const API_ROOT = "/api";
const LANGUAGE_STORAGE_KEY = "fabric-access-atlas-language";
const TOKEN_STORAGE_KEY = "fabric-access-atlas-token";
const LOCALES = { da: "da-DK", en: "en-US", pt: "pt-PT" };
const translations = {
  da: {
    Language: "Sprog", "Select language": "Vælg sprog", Principals: "Identiteter", "Read-only discovery": "Skrivebeskyttet discovery",
    "ITEM LANDSCAPE": "ITEMLANDSKAB", "DISCOVERY STATUS": "DISCOVERY-STATUS", "TENANT DISCOVERY": "TENANT-DISCOVERY", "LIVE STATUS": "LIVE-STATUS",
    "Active Fabric workspaces returned by the Fabric Admin API": "Aktive Fabric-workspaces returneret af Fabric Admin API'et",
    "Direct workspace role assignments for users, groups, service principals, profiles, and entire-tenant principals": "Direkte workspace-roller for brugere, grupper, service principals, profiler og hele tenant-principals",
    "Power BI artifact users returned by metadata scanning when IncludePowerBIArtifactUsers is enabled": "Power BI artifact-brugere returneret af metadata-scanning",
    "Effective access inherited through nested Microsoft Entra groups": "Effektiv adgang nedarvet gennem indlejrede Microsoft Entra-grupper",
    "Generic Fabric item-level sharing outside the Power BI artifact users exposed by scanner APIs": "Generisk deling på Fabric-itemniveau uden for scanner-API'ets Power BI artifact-brugere",
    "OneLake security role definitions and members": "OneLake-sikkerhedsroller og medlemmer",
    "Warehouse, SQL analytics endpoint, and SQL database GRANT, DENY, roles, RLS, and object permissions": "Warehouse-, SQL analytics endpoint- og SQL database-rettigheder, roller og RLS",
    "Semantic model RLS and OLS role membership": "Semantisk model RLS- og OLS-rollemedlemskab",
    "KQL database and Eventhouse security roles": "KQL database- og Eventhouse-sikkerhedsroller",
    "Gateway, connection, app audience, capacity, and tenant administrator assignments": "Gateway-, forbindelse-, app audience-, capacity- og tenantadministrator-tildelinger",
    "List Workspace Access Details is a preview API and is limited to 200 requests per hour.": "List Workspace Access Details er et preview-API begrænset til 200 kald i timen.",
    "Power BI metadata scanning supports at most 100 workspace IDs per scan request and 500 scan requests per hour.": "Power BI metadata-scanning understøtter højst 100 workspace-ID'er pr. scan og 500 scan-kald i timen.",
    workspaces: "workspaces", artifacts: "artifacts", principals: "principals", workspaceRoles: "workspace-roller", itemPermissions: "item-rettigheder",
    "Næste API-kald om {seconds} sek.": "Næste API-kald om {seconds} sek.", "Næste API-kald nu": "Næste API-kald nu", "Forventet fortsættelse kl. {time}": "Forventet fortsættelse kl. {time}",
    "Throttle-beskyttelse": "Throttle-beskyttelse", "Midlertidig API-fejl": "Midlertidig API-fejl", "Power BI behandler metadata": "Power BI behandler metadata",
    "Venter mellem kald til {api} for at holde sig under grænsen på {limit} kald i timen.": "Venter mellem kald til {api} for at holde sig under grænsen på {limit} kald i timen.",
    "Kaldet forsøges automatisk igen. Microsofts Retry-After eller eksponentiel backoff respekteres.": "Kaldet forsøges automatisk igen. Microsofts Retry-After eller eksponentiel backoff respekteres.",
    "Power BI forbereder batchresultatet. Status kontrolleres hvert 30. sekund.": "Power BI forbereder batchresultatet. Status kontrolleres hvert 30. sekund.",
    "Fabric workspace access API": "Fabric workspace access API", "Power BI metadata API": "Power BI metadata API"
    , "Estimeret scannertid": "Estimeret scannertid", "Ca. {minimum}–{maximum}": "Ca. {minimum}–{maximum}", "under 1 min.": "under 1 min.", "{hours} t. {minutes} min.": "{hours} t. {minutes} min.", "{minutes} min.": "{minutes} min.",
    "Scanner workspace {current}/{total}": "Scanner workspace {current}/{total}",
    "Åbn Microsoft-login og indtast koden": "Åbn Microsoft-login og indtast koden", "Åbn Microsoft-login": "Åbn Microsoft-login",
    "Baseret på {count} workspaces fundet i tenant": "Baseret på {count} workspaces fundet i tenant", "Baseret på en grænse på op til {count} workspaces": "Baseret på en grænse på op til {count} workspaces", "Baseret på {count} workspaces i seneste snapshot": "Baseret på {count} workspaces i seneste snapshot",
    "API-pacing: {duration} · {batches} metadata-batch": "API-pacing: {duration} · {batches} metadata-batch", "API-pacing: {duration} · {batches} metadata-batches": "API-pacing: {duration} · {batches} metadata-batches", "API-pacing: {duration} · uden metadata-scan": "API-pacing: {duration} · uden metadata-scan", "Personlige workspaces kan øge det faktiske antal.": "Personlige workspaces kan øge det faktiske antal.", "Retries og Microsoft-behandlingstid kan forlænge scanningen.": "Retries og Microsoft-behandlingstid kan forlænge scanningen."
  },
  en: {
    "Primær navigation": "Primary navigation", "Overblik": "Overview", "Rettigheder": "Permissions", "API-dækning": "API coverage", "Start scan": "Start scan", "Skift tema": "Change theme", "Åbn menu": "Open menu", "Adgangsoverblik": "Access overview", "Snapshot": "Snapshot", "Indlæser...": "Loading...", "Indlæser Fabric-rettigheder": "Loading Fabric permissions", "Normaliserer workspaces, items og principals": "Normalizing workspaces, items and principals", "Data kunne ikke indlæses": "Data could not be loaded", "Start siden via den lokale webserver, så JSON-filerne kan læses.": "Open the page through the local web server so the JSON files can be read.",
    "aktive i snapshot": "active in snapshot", "unikke identiteter": "unique identities", "Tildelinger": "Assignments", "workspace + item": "workspace + item", "FORDELING": "DISTRIBUTION", "Adgang pr. principal": "Access by principal", "Item-tildelinger": "Item assignments", "Største kategorier": "Largest categories", "SENEST ÆNDRET": "RECENTLY MODIFIED", "Se alle rettigheder →": "View all permissions →", "Søg item, workspace eller bruger...": "Search item, workspace or user...", "Alle workspaces": "All workspaces", "Alle item-typer": "All item types", "Alle adgangstyper": "All access types", "Eksportér side": "Export page", "rettighedstildelinger": "permission assignments", "Adgang": "Access", "Ingen rettigheder matcher filtrene.": "No permissions match the filters.", "Søg workspace...": "Search workspace...", "Visning": "View",
    "Hvad kan API’erne se?": "What can the APIs see?", "Snapshot’et kombinerer Fabric Admin API og Power BI metadata scanning. Det er et stærkt udgangspunkt, men ikke hele den effektive sikkerhedsmodel.": "The snapshot combines the Fabric Admin API and Power BI metadata scanning. It is a strong starting point, but not the complete effective security model.", "datakilder valideret": "data sources validated", "Dækket nu": "Covered now", "Indgår i dette snapshot": "Included in this snapshot", "Kræver collector": "Requires collector", "Separate sikkerhedsmodeller": "Separate security models", "DRIFTSNOTER": "OPERATIONAL NOTES", "API-begrænsninger": "API limitations",
    "Nyt rettighedsscan": "New permission scan", "Klar": "Ready", "Microsoft-konto": "Microsoft account", "Kontrollerer login...": "Checking sign-in...", "Kontrollerer": "Checking", "Log ind med Microsoft": "Sign in with Microsoft", "Log ud": "Sign out", "Log ind for at hente tenants": "Sign in to load tenants", "Listen viser de tenants, Microsoft-kontoen har adgang til.": "The list shows the tenants available to the Microsoft account.", "Maks. antal workspaces": "Maximum workspaces", "0 scanner alle aktive workspaces.": "0 scans all active workspaces.", "Power BI artifact-brugere": "Power BI artifact users", "Medtag item-adgang fra metadata-scanneren": "Include item access from the metadata scanner", "Personlige workspaces": "Personal workspaces", "Medtag My Workspaces i discovery": "Include My Workspaces in discovery", "LIVE STATUS": "LIVE STATUS", "Klar til scanning": "Ready to scan", "Scan-fremdrift": "Scan progress", "Ikke startet": "Not started", "Proceslog": "Process log", "Seneste 200 linjer": "Latest 200 lines", "Ingen aktivitet endnu.": "No activity yet.", "WORKSPACE DETALJER": "WORKSPACE DETAILS", "Luk": "Close",
    "Items": "Items", "Principals": "Principals", "Roller": "Roles", "Workspace-adgang": "Workspace access", "Item-fordeling": "Item distribution", "Ingen direkte roller": "No direct roles", "Artifact-kategori": "Artifact category", "Ingen items i scanner-resultatet": "No items in the scanner result", "Ingen item-rettigheder fundet.": "No item permissions found.", "Ingen datooplysninger fundet.": "No date information found.", "Side {page} af {total}": "Page {page} of {total}", "Ukendt": "Unknown", "item-typer": "item types", "Start discovery-scan": "Start discovery scan", "Vælg tenant": "Select tenant", "Ingen tilgængelige tenants": "No available tenants", "Afventer Microsoft...": "Waiting for Microsoft...", "Kræver container-rebuild": "Requires container rebuild", "Skift konto": "Switch account", "Scan kører...": "Scan running...", "Log ind for at scanne": "Sign in to scan", "Vælg en tenant": "Select a tenant", "Startet {date}": "Started {date}", "Afsluttet {date}": "Completed {date}", "Ikke logget ind": "Not signed in", "Afventer": "Waiting", "Logget ind": "Signed in", "Fejlet": "Failed", "Utilgængelig": "Unavailable", "I kø": "Queued", "Kører": "Running", "Importerer": "Importing", "Fuldført": "Completed"
  },
  pt: {
    "Primær navigation": "Navegação principal", "Overblik": "Visão geral", "Rettigheder": "Permissões", "API-dækning": "Cobertura da API", "Start scan": "Iniciar análise", "Skift tema": "Alterar tema", "Åbn menu": "Abrir menu", "Adgangsoverblik": "Visão geral de acessos", "Snapshot": "Snapshot", "Indlæser...": "A carregar...", "Indlæser Fabric-rettigheder": "A carregar permissões do Fabric", "Normaliserer workspaces, items og principals": "A normalizar espaços de trabalho, itens e identidades", "Data kunne ikke indlæses": "Não foi possível carregar os dados", "Start siden via den lokale webserver, så JSON-filerne kan læses.": "Abra a página através do servidor Web local para ler os ficheiros JSON.",
    "aktive i snapshot": "ativos no snapshot", "unikke identiteter": "identidades únicas", "Tildelinger": "Atribuições", "workspace + item": "espaço de trabalho + item", "FORDELING": "DISTRIBUIÇÃO", "Adgang pr. principal": "Acesso por identidade", "Item-tildelinger": "Atribuições de itens", "Største kategorier": "Maiores categorias", "SENEST ÆNDRET": "ALTERADOS RECENTEMENTE", "Se alle rettigheder →": "Ver todas as permissões →", "Søg item, workspace eller bruger...": "Pesquisar item, espaço de trabalho ou utilizador...", "Alle workspaces": "Todos os espaços de trabalho", "Alle item-typer": "Todos os tipos de item", "Alle adgangstyper": "Todos os tipos de acesso", "Eksportér side": "Exportar página", "rettighedstildelinger": "atribuições de permissões", "Adgang": "Acesso", "Ingen rettigheder matcher filtrene.": "Nenhuma permissão corresponde aos filtros.", "Søg workspace...": "Pesquisar espaço de trabalho...", "Visning": "Vista",
    "Hvad kan API’erne se?": "O que podem ver as APIs?", "Snapshot’et kombinerer Fabric Admin API og Power BI metadata scanning. Det er et stærkt udgangspunkt, men ikke hele den effektive sikkerhedsmodel.": "O snapshot combina a API de Administração do Fabric e a análise de metadados do Power BI. É um ponto de partida sólido, mas não representa todo o modelo de segurança efetivo.", "datakilder valideret": "fontes de dados validadas", "Dækket nu": "Coberto agora", "Indgår i dette snapshot": "Incluído neste snapshot", "Kræver collector": "Requer coletor", "Separate sikkerhedsmodeller": "Modelos de segurança separados", "DRIFTSNOTER": "NOTAS OPERACIONAIS", "API-begrænsninger": "Limitações da API",
    "Nyt rettighedsscan": "Nova análise de permissões", "Klar": "Pronto", "Microsoft-konto": "Conta Microsoft", "Kontrollerer login...": "A verificar início de sessão...", "Kontrollerer": "A verificar", "Log ind med Microsoft": "Iniciar sessão com a Microsoft", "Log ud": "Terminar sessão", "Log ind for at hente tenants": "Inicie sessão para carregar os tenants", "Listen viser de tenants, Microsoft-kontoen har adgang til.": "A lista mostra os tenants disponíveis para a conta Microsoft.", "Maks. antal workspaces": "Máximo de espaços de trabalho", "0 scanner alle aktive workspaces.": "0 analisa todos os espaços de trabalho ativos.", "Power BI artifact-brugere": "Utilizadores de artefactos do Power BI", "Medtag item-adgang fra metadata-scanneren": "Incluir acesso a itens do analisador de metadados", "Personlige workspaces": "Espaços de trabalho pessoais", "Medtag My Workspaces i discovery": "Incluir Os Meus Espaços de Trabalho na descoberta", "Klar til scanning": "Pronto para analisar", "Scan-fremdrift": "Progresso da análise", "Ikke startet": "Não iniciado", "Proceslog": "Registo do processo", "Seneste 200 linjer": "Últimas 200 linhas", "Ingen aktivitet endnu.": "Ainda sem atividade.", "WORKSPACE DETALJER": "DETALHES DO ESPAÇO DE TRABALHO", "Luk": "Fechar",
    "Items": "Itens", "Principals": "Identidades", "Roller": "Funções", "Workspace-adgang": "Acesso ao espaço de trabalho", "Item-fordeling": "Distribuição de itens", "Ingen direkte roller": "Sem funções diretas", "Artifact-kategori": "Categoria do artefacto", "Ingen items i scanner-resultatet": "Sem itens no resultado da análise", "Ingen item-rettigheder fundet.": "Não foram encontradas permissões de itens.", "Ingen datooplysninger fundet.": "Não foram encontradas informações de data.", "Side {page} af {total}": "Página {page} de {total}", "Ukendt": "Desconhecido", "item-typer": "tipos de item", "Start discovery-scan": "Iniciar análise de descoberta", "Vælg tenant": "Selecionar tenant", "Ingen tilgængelige tenants": "Nenhum tenant disponível", "Afventer Microsoft...": "A aguardar a Microsoft...", "Kræver container-rebuild": "Requer reconstrução do contentor", "Skift konto": "Mudar conta", "Scan kører...": "Análise em execução...", "Log ind for at scanne": "Inicie sessão para analisar", "Vælg en tenant": "Selecione um tenant", "Startet {date}": "Iniciado em {date}", "Afsluttet {date}": "Concluído em {date}", "Ikke logget ind": "Sessão não iniciada", "Afventer": "A aguardar", "Logget ind": "Sessão iniciada", "Fejlet": "Falhou", "Utilgængelig": "Indisponível", "I kø": "Na fila", "Kører": "Em execução", "Importerer": "A importar", "Fuldført": "Concluído"
  }
};
Object.assign(translations.en, {
  Language: "Language", "Select language": "Select language", Principal: "Principal", Workspace: "Workspace", Item: "Item", Type: "Type", Status: "Status", Tenant: "Tenant",
  "Filtrer workspace": "Filter workspace", "Filtrer item-type": "Filter item type", "Filtrer adgang": "Filter access",
  "Starter Microsoft-login": "Starting Microsoft sign-in", "Logget ind": "Signed in", "Afventer personligt login i browseren": "Waiting for personal sign-in in the browser", "Login fejlede": "Sign-in failed",
  "Forbereder scan": "Preparing scan", "Starter discovery": "Starting discovery", "Importerer nyt snapshot": "Importing new snapshot", "Scan gennemført": "Scan completed", "Scan fejlede": "Scan failed",
  "Næste API-kald om {seconds} sek.": "Next API call in {seconds}s", "Næste API-kald nu": "Next API call now", "Forventet fortsættelse kl. {time}": "Expected to continue at {time}",
  "Throttle-beskyttelse": "Throttle protection", "Midlertidig API-fejl": "Temporary API error", "Power BI behandler metadata": "Power BI is processing metadata",
  "Venter mellem kald til {api} for at holde sig under grænsen på {limit} kald i timen.": "Waiting between {api} calls to stay below the limit of {limit} requests per hour.",
  "Kaldet forsøges automatisk igen. Microsofts Retry-After eller eksponentiel backoff respekteres.": "The request will retry automatically using Microsoft's Retry-After value or exponential backoff.",
  "Power BI forbereder batchresultatet. Status kontrolleres hvert 30. sekund.": "Power BI is preparing the batch result. Status is checked every 30 seconds.",
  "Fabric workspace access API": "Fabric workspace access API", "Power BI metadata API": "Power BI metadata API"
  , "Estimeret scannertid": "Estimated scan time", "Ca. {minimum}–{maximum}": "About {minimum}–{maximum}", "under 1 min.": "under 1 min", "{hours} t. {minutes} min.": "{hours}h {minutes}m", "{minutes} min.": "{minutes} min",
  "Scanner workspace {current}/{total}": "Scanning workspace {current}/{total}",
  "Åbn Microsoft-login og indtast koden": "Open Microsoft sign-in and enter the code", "Åbn Microsoft-login": "Open Microsoft sign-in",
  "Baseret på {count} workspaces fundet i tenant": "Based on {count} workspaces found in the tenant", "Baseret på en grænse på op til {count} workspaces": "Based on a limit of up to {count} workspaces", "Baseret på {count} workspaces i seneste snapshot": "Based on {count} workspaces in the latest snapshot",
  "API-pacing: {duration} · {batches} metadata-batch": "API pacing: {duration} · {batches} metadata batch", "API-pacing: {duration} · {batches} metadata-batches": "API pacing: {duration} · {batches} metadata batches", "API-pacing: {duration} · uden metadata-scan": "API pacing: {duration} · without metadata scanning", "Personlige workspaces kan øge det faktiske antal.": "Personal workspaces may increase the actual count.", "Retries og Microsoft-behandlingstid kan forlænge scanningen.": "Retries and Microsoft processing time may extend the scan."
});
Object.assign(translations.pt, {
  Language: "Idioma", "Select language": "Selecionar idioma", Workspaces: "Espaços de trabalho", Principal: "Identidade", Workspace: "Espaço de trabalho", Item: "Item", Type: "Tipo", Status: "Estado", Tenant: "Tenant",
  "Fabric-items": "Itens do Fabric", "ITEM LANDSCAPE": "PANORAMA DE ITENS", "DISCOVERY STATUS": "ESTADO DA DESCOBERTA", "TENANT DISCOVERY": "DESCOBERTA DO TENANT", "LIVE STATUS": "ESTADO EM DIRETO", "Read-only discovery": "Descoberta só de leitura",
  "Filtrer workspace": "Filtrar espaço de trabalho", "Filtrer item-type": "Filtrar tipo de item", "Filtrer adgang": "Filtrar acesso",
  "Starter Microsoft-login": "A iniciar sessão Microsoft", "Logget ind": "Sessão iniciada", "Afventer personligt login i browseren": "A aguardar o início de sessão pessoal no navegador", "Login fejlede": "O início de sessão falhou",
  "Forbereder scan": "A preparar análise", "Starter discovery": "A iniciar descoberta", "Importerer nyt snapshot": "A importar novo snapshot", "Scan gennemført": "Análise concluída", "Scan fejlede": "A análise falhou",
  "Active Fabric workspaces returned by the Fabric Admin API": "Espaços de trabalho ativos devolvidos pela API de Administração do Fabric",
  "Direct workspace role assignments for users, groups, service principals, profiles, and entire-tenant principals": "Funções diretas de espaços de trabalho para utilizadores, grupos, principais de serviço, perfis e identidades de todo o tenant",
  "Power BI artifact users returned by metadata scanning when IncludePowerBIArtifactUsers is enabled": "Utilizadores de artefactos do Power BI devolvidos pela análise de metadados",
  "Effective access inherited through nested Microsoft Entra groups": "Acesso efetivo herdado através de grupos Microsoft Entra aninhados",
  "Generic Fabric item-level sharing outside the Power BI artifact users exposed by scanner APIs": "Partilha genérica ao nível de itens do Fabric fora dos utilizadores expostos pelas APIs de análise",
  "OneLake security role definitions and members": "Definições e membros de funções de segurança do OneLake",
  "Warehouse, SQL analytics endpoint, and SQL database GRANT, DENY, roles, RLS, and object permissions": "Permissões, funções e RLS de Warehouse, endpoint de análise SQL e base de dados SQL",
  "Semantic model RLS and OLS role membership": "Associação a funções RLS e OLS do modelo semântico",
  "KQL database and Eventhouse security roles": "Funções de segurança de bases de dados KQL e Eventhouse",
  "Gateway, connection, app audience, capacity, and tenant administrator assignments": "Atribuições de gateway, ligação, público da aplicação, capacidade e administrador do tenant",
  "List Workspace Access Details is a preview API and is limited to 200 requests per hour.": "List Workspace Access Details é uma API de pré-visualização limitada a 200 pedidos por hora.",
  "Power BI metadata scanning supports at most 100 workspace IDs per scan request and 500 scan requests per hour.": "A análise de metadados do Power BI suporta até 100 IDs por pedido e 500 pedidos de análise por hora.",
  workspaces: "espaços de trabalho", artifacts: "artefactos", principals: "identidades", workspaceRoles: "funções de espaço de trabalho", itemPermissions: "permissões de item"
});
Object.assign(translations.pt, {
  "Næste API-kald om {seconds} sek.": "Próxima chamada à API em {seconds} s", "Næste API-kald nu": "Próxima chamada à API agora", "Forventet fortsættelse kl. {time}": "Continuação prevista às {time}",
  "Throttle-beskyttelse": "Proteção contra limitação", "Midlertidig API-fejl": "Erro temporário da API", "Power BI behandler metadata": "O Power BI está a processar metadados",
  "Venter mellem kald til {api} for at holde sig under grænsen på {limit} kald i timen.": "A aguardar entre chamadas à {api} para permanecer abaixo do limite de {limit} pedidos por hora.",
  "Kaldet forsøges automatisk igen. Microsofts Retry-After eller eksponentiel backoff respekteres.": "O pedido será repetido automaticamente usando Retry-After da Microsoft ou espera exponencial.",
  "Power BI forbereder batchresultatet. Status kontrolleres hvert 30. sekund.": "O Power BI está a preparar o resultado do lote. O estado é verificado a cada 30 segundos.",
  "Fabric workspace access API": "API de acesso a espaços de trabalho do Fabric", "Power BI metadata API": "API de metadados do Power BI"
  , "Estimeret scannertid": "Tempo estimado da análise", "Ca. {minimum}–{maximum}": "Cerca de {minimum}–{maximum}", "under 1 min.": "menos de 1 min", "{hours} t. {minutes} min.": "{hours} h {minutes} min", "{minutes} min.": "{minutes} min",
  "Scanner workspace {current}/{total}": "A analisar espaço de trabalho {current}/{total}",
  "Åbn Microsoft-login og indtast koden": "Abra o início de sessão da Microsoft e introduza o código", "Åbn Microsoft-login": "Abrir início de sessão da Microsoft",
  "Baseret på {count} workspaces fundet i tenant": "Com base em {count} espaços de trabalho encontrados no tenant", "Baseret på en grænse på op til {count} workspaces": "Com base num limite de até {count} espaços de trabalho", "Baseret på {count} workspaces i seneste snapshot": "Com base em {count} espaços de trabalho no snapshot mais recente",
  "API-pacing: {duration} · {batches} metadata-batch": "Ritmo da API: {duration} · {batches} lote de metadados", "API-pacing: {duration} · {batches} metadata-batches": "Ritmo da API: {duration} · {batches} lotes de metadados", "API-pacing: {duration} · uden metadata-scan": "Ritmo da API: {duration} · sem análise de metadados", "Personlige workspaces kan øge det faktiske antal.": "Os espaços de trabalho pessoais podem aumentar o total real.", "Retries og Microsoft-behandlingstid kan forlænge scanningen.": "As repetições e o tempo de processamento da Microsoft podem prolongar a análise."
});

Object.assign(translations.en, {
  "Brugermapping": "User mapping", "Brugermapping for migration": "Migration user mapping", "Map nuværende brugere til nye brugere": "Map current users to new users",
  "Listen viser tenant-brugere med Fabric-adgang. Hver kan kun mappes til én tenant-bruger uden Fabric-adgang, og samme målbruger kan ikke genbruges.": "The list shows tenant users with Fabric access. Each can only map to one tenant user without Fabric access, and the same target user cannot be reused.",
  "Hent tenant-brugere": "Load tenant users", "Nuværende Fabric-bruger": "Current Fabric user", "Ny bruger uden Fabric-adgang": "New user without Fabric access",
  "Vælg en tenant og hent tenant-brugerne.": "Select a tenant and load its users.", "Vælg ny bruger": "Select new user", "Ikke mappet": "Not mapped", "Mappet": "Mapped",
  "{sources} Fabric-brugere · {targets} mulige mål · {mapped} mappet": "{sources} Fabric users · {targets} possible targets · {mapped} mapped",
  "Ingen tenant-brugere med Fabric-adgang blev fundet.": "No tenant users with Fabric access were found.", "Henter brugere...": "Loading users..."
});
Object.assign(translations.pt, {
  "Brugermapping": "Mapeamento de utilizadores", "Brugermapping for migration": "Mapeamento de utilizadores para migração", "Map nuværende brugere til nye brugere": "Mapear utilizadores atuais para novos utilizadores",
  "Listen viser tenant-brugere med Fabric-adgang. Hver kan kun mappes til én tenant-bruger uden Fabric-adgang, og samme målbruger kan ikke genbruges.": "A lista mostra utilizadores do tenant com acesso ao Fabric. Cada um só pode ser mapeado para um utilizador sem acesso ao Fabric, e o mesmo destino não pode ser reutilizado.",
  "Hent tenant-brugere": "Carregar utilizadores do tenant", "Nuværende Fabric-bruger": "Utilizador atual do Fabric", "Ny bruger uden Fabric-adgang": "Novo utilizador sem acesso ao Fabric",
  "Vælg en tenant og hent tenant-brugerne.": "Selecione um tenant e carregue os utilizadores.", "Vælg ny bruger": "Selecionar novo utilizador", "Ikke mappet": "Não mapeado", "Mappet": "Mapeado",
  "{sources} Fabric-brugere · {targets} mulige mål · {mapped} mappet": "{sources} utilizadores do Fabric · {targets} destinos possíveis · {mapped} mapeados",
  "Ingen tenant-brugere med Fabric-adgang blev fundet.": "Não foram encontrados utilizadores do tenant com acesso ao Fabric.", "Henter brugere...": "A carregar utilizadores..."
});
Object.assign(translations.en, {
  "PERMISSION MIGRATION": "PERMISSION MIGRATION", "Anvend de mappede rettigheder": "Apply mapped permissions", "Rettigheder tilføjes til de nye brugere. De oprindelige brugeres rettigheder ændres ikke.": "Permissions are added to new users. The original users' permissions are not changed.",
  "Gennemgå plan": "Review plan", "Indlæser plan...": "Loading plan...", "Workspace-roller": "Workspace roles", "Semantic model-rettigheder": "Semantic model permissions", "Dækket af workspace-rolle": "Covered by workspace role", "Kan ikke kopieres præcist": "Cannot be copied exactly", "Kun rettigheder, som Microsofts API'er kan kopiere præcist, bliver anvendt. Ikke-understøttede rettigheder registreres i resultatrapporten.": "Only permissions that Microsoft's APIs can reproduce exactly are applied. Unsupported permissions are recorded in the result report.",
  "Ikke-understøttede rettigheder": "Unsupported permissions", "{count} rettigheder kan ikke kopieres præcist": "{count} permissions cannot be copied exactly", "{count} workspace-roller anvendes": "{count} workspace roles will be applied", "{count} semantic model-rettigheder anvendes": "{count} semantic model permissions will be applied", "{count} rettigheder dækkes af workspace-roller": "{count} permissions are covered by workspace roles", "Kildebruger": "Source user", "Målbruger": "Target user", "Detalje": "Detail", "Anvendes præcist": "Applied exactly", "Dækket af workspace-rollen {role}": "Covered by workspace role {role}",
  "Jeg har gennemgået planen": "I have reviewed the plan", "Dette starter en skriveoperation mod den valgte tenant.": "This starts a write operation against the selected tenant.", "Anvend rettigheder": "Apply permissions", "Klar til rettighedsmigration": "Ready for permission migration", "Rettighedsmigration": "Permission migration", "Annuller job": "Cancel job",
  "Klar til at anvende mappede rettigheder": "Ready to apply mapped permissions", "Forbereder rettighedsmigration": "Preparing permission migration", "Anvender mappede rettigheder": "Applying mapped permissions", "Anullerer efter nuværende anmodning": "Cancelling after the current request", "Rettighedsmigration gennemført": "Permission migration completed", "Rettighedsmigration annulleret": "Permission migration cancelled", "Rettighedsmigration fejlede": "Permission migration failed",
  "Anvender rettighed {current}/{total}: {workspace}": "Applying permission {current}/{total}: {workspace}", "Læser adgang for {count} workspaces": "Reading access for {count} workspaces",
  "Rettighed {current}/{total}": "Permission {current}/{total}", "Venter {seconds} sek. før næste API-kald": "Waiting {seconds}s before the next API call", "Kontrolleret og klar": "Reviewed and ready", "Fejl under migration": "Migration failures", applied: "applied", alreadyApplied: "already applied", failed: "failed", unsupported: "unsupported", total: "total"
});
Object.assign(translations.pt, {
  "PERMISSION MIGRATION": "MIGRAÇÃO DE PERMISSÕES", "Anvend de mappede rettigheder": "Aplicar permissões mapeadas", "Rettigheder tilføjes til de nye brugere. De oprindelige brugeres rettigheder ændres ikke.": "As permissões são adicionadas aos novos utilizadores. As permissões dos utilizadores originais não são alteradas.",
  "Gennemgå plan": "Rever plano", "Indlæser plan...": "A carregar plano...", "Workspace-roller": "Funções do espaço de trabalho", "Semantic model-rettigheder": "Permissões do modelo semântico", "Dækket af workspace-rolle": "Coberto pela função do espaço de trabalho", "Kan ikke kopieres præcist": "Não é possível copiar exatamente", "Kun rettigheder, som Microsofts API'er kan kopiere præcist, bliver anvendt. Ikke-understøttede rettigheder registreres i resultatrapporten.": "Apenas são aplicadas permissões que as APIs da Microsoft conseguem reproduzir exatamente. As permissões não suportadas são registadas no relatório.",
  "Ikke-understøttede rettigheder": "Permissões não suportadas", "{count} rettigheder kan ikke kopieres præcist": "Não é possível copiar exatamente {count} permissões", "{count} workspace-roller anvendes": "Serão aplicadas {count} funções do espaço de trabalho", "{count} semantic model-rettigheder anvendes": "Serão aplicadas {count} permissões de modelo semântico", "{count} rettigheder dækkes af workspace-roller": "{count} permissões são cobertas por funções do espaço de trabalho", "Kildebruger": "Utilizador de origem", "Målbruger": "Utilizador de destino", "Detalje": "Detalhe", "Anvendes præcist": "Aplicada exatamente", "Dækket af workspace-rollen {role}": "Coberta pela função do espaço de trabalho {role}",
  "Jeg har gennemgået planen": "Revi o plano", "Dette starter en skriveoperation mod den valgte tenant.": "Isto inicia uma operação de escrita no tenant selecionado.", "Anvend rettigheder": "Aplicar permissões", "Klar til rettighedsmigration": "Pronto para migrar permissões", "Rettighedsmigration": "Migração de permissões", "Annuller job": "Cancelar tarefa",
  "Klar til at anvende mappede rettigheder": "Pronto para aplicar permissões mapeadas", "Forbereder rettighedsmigration": "A preparar migração de permissões", "Anvender mappede rettigheder": "A aplicar permissões mapeadas", "Anullerer efter nuværende anmodning": "A cancelar após o pedido atual", "Rettighedsmigration gennemført": "Migração de permissões concluída", "Rettighedsmigration annulleret": "Migração de permissões cancelada", "Rettighedsmigration fejlede": "A migração de permissões falhou",
  "Anvender rettighed {current}/{total}: {workspace}": "A aplicar permissão {current}/{total}: {workspace}", "Læser adgang for {count} workspaces": "A ler acesso para {count} espaços de trabalho",
  "Rettighed {current}/{total}": "Permissão {current}/{total}", "Venter {seconds} sek. før næste API-kald": "A aguardar {seconds} s antes da próxima chamada à API", "Kontrolleret og klar": "Revisto e pronto", "Fejl under migration": "Falhas na migração", applied: "aplicadas", alreadyApplied: "já aplicadas", failed: "falharam", unsupported: "não suportadas", total: "total"
});
Object.assign(translations.da, {
  "The available Microsoft write APIs cannot reproduce this item type and access right exactly.": "De tilgængelige Microsoft-skrive-API'er kan ikke genskabe denne item-type og rettighed præcist.",
  "This workspace role is not supported by the Fabric role-assignment API.": "Denne workspace-rolle understøttes ikke af Fabrics API til rolletildeling.",
  Authentication: "Godkendelse", "AZURE AUTHENTICATION": "AZURE-GODKENDELSE", "Connect to Microsoft Fabric": "Opret forbindelse til Microsoft Fabric", "Choose delegated Microsoft sign-in for interactive use or a service principal for unattended operation.": "Vælg delegeret Microsoft-login til interaktiv brug eller en service principal til automatiseret drift.",
  DELEGATED: "DELEGERET", "Microsoft account": "Microsoft-konto", "Current session": "Aktuel session", AUTOMATION: "AUTOMATISERING", "Service principal": "Service principal", "Tenant ID": "Tenant-ID", "Client ID": "Klient-ID", "Client secret": "Klienthemmelighed", "Client secret value": "Værdi for klienthemmelighed", "The secret is used only for this Azure CLI login and is not stored by the application.": "Hemmeligheden bruges kun til dette Azure CLI-login og gemmes ikke af applikationen.", "Sign in with service principal": "Log ind med service principal", "Application API token": "Applikationens API-token", "Required for sign-in and other changes when FABRIC_ATLAS_TOKEN is configured.": "Kræves til login og andre ændringer, når FABRIC_ATLAS_TOKEN er konfigureret.", "Not signed in": "Ikke logget ind"
});
Object.assign(translations.pt, {
  "The available Microsoft write APIs cannot reproduce this item type and access right exactly.": "As APIs de escrita disponíveis da Microsoft não conseguem reproduzir exatamente este tipo de item e direito de acesso.",
  "This workspace role is not supported by the Fabric role-assignment API.": "Esta função do espaço de trabalho não é suportada pela API de atribuição de funções do Fabric.",
  Authentication: "Autenticação", "AZURE AUTHENTICATION": "AUTENTICAÇÃO DO AZURE", "Connect to Microsoft Fabric": "Ligar ao Microsoft Fabric", "Choose delegated Microsoft sign-in for interactive use or a service principal for unattended operation.": "Escolha o início de sessão Microsoft delegado para utilização interativa ou um principal de serviço para operação automática.",
  DELEGATED: "DELEGADO", "Microsoft account": "Conta Microsoft", "Current session": "Sessão atual", AUTOMATION: "AUTOMAÇÃO", "Service principal": "Principal de serviço", "Tenant ID": "ID do tenant", "Client ID": "ID do cliente", "Client secret": "Segredo do cliente", "Client secret value": "Valor do segredo do cliente", "The secret is used only for this Azure CLI login and is not stored by the application.": "O segredo é usado apenas neste início de sessão da CLI do Azure e não é armazenado pela aplicação.", "Sign in with service principal": "Iniciar sessão com principal de serviço", "Application API token": "Token da API da aplicação", "Required for sign-in and other changes when FABRIC_ATLAS_TOKEN is configured.": "Necessário para iniciar sessão e fazer outras alterações quando FABRIC_ATLAS_TOKEN está configurado.", "Not signed in": "Sessão não iniciada"
});
Object.assign(translations.en, {
  "API-token": "API token",
  "Indtast token (FABRIC_ATLAS_TOKEN)": "Enter the token from FABRIC_ATLAS_TOKEN",
  "Gem": "Save",
  "Gemmes kun i denne browser og bruges, når serveren kræver et token.": "Stored only in this browser; used when the server requires a token.",
  "API-token mangler eller er ugyldig": "Missing or invalid API token"
  , "Kapaciteter og workspaces": "Capacities and workspaces", "Vælg en tenant for at hente workspaces.": "Select a tenant to load workspaces.", "Vælg en kapacitet for at vælge eller fravælge alle dens workspaces.": "Select a capacity to select or clear all of its workspaces.",
  "{count} valgt": "{count} selected", "Henter kapaciteter og workspaces...": "Loading capacities and workspaces...", "Ingen kapaciteter eller workspaces blev fundet.": "No capacities or workspaces were found.", "Ingen workspaces": "No workspaces", "Vælg alle workspaces i {capacity}": "Select all workspaces in {capacity}", "Vælg mindst ét workspace": "Select at least one workspace", "Baseret på {count} valgte workspaces": "Based on {count} selected workspaces",
  "SCAN SELECTION": "SCAN SELECTION", "SENESTE SNAPSHOT": "LATEST SNAPSHOT", "Workspace-detaljer": "Workspace details", "Gå til scan": "Go to scan", "{count} workspaces valgt": "{count} workspaces selected", "Administrer valget under Workspaces.": "Manage the selection under Workspaces.", "Vælg workspaces": "Select workspaces"
});
Object.assign(translations.pt, {
  "API-token": "Token da API",
  "Indtast token (FABRIC_ATLAS_TOKEN)": "Insira o token de FABRIC_ATLAS_TOKEN",
  "Gem": "Guardar",
  "Gemmes kun i denne browser og bruges, når serveren kræver et token.": "Guardado apenas neste navegador; usado quando o servidor exige um token.",
  "API-token mangler eller er ugyldig": "Token da API em falta ou inválido"
  , "Kapaciteter og workspaces": "Capacidades e espaços de trabalho", "Vælg en tenant for at hente workspaces.": "Selecione um tenant para carregar os espaços de trabalho.", "Vælg en kapacitet for at vælge eller fravælge alle dens workspaces.": "Selecione uma capacidade para selecionar ou desmarcar todos os seus espaços de trabalho.",
  "{count} valgt": "{count} selecionados", "Henter kapaciteter og workspaces...": "A carregar capacidades e espaços de trabalho...", "Ingen kapaciteter eller workspaces blev fundet.": "Não foram encontradas capacidades ou espaços de trabalho.", "Ingen workspaces": "Sem espaços de trabalho", "Vælg alle workspaces i {capacity}": "Selecionar todos os espaços de trabalho em {capacity}", "Vælg mindst ét workspace": "Selecione pelo menos um espaço de trabalho", "Baseret på {count} valgte workspaces": "Com base em {count} espaços de trabalho selecionados",
  "SCAN SELECTION": "SELEÇÃO DA ANÁLISE", "SENESTE SNAPSHOT": "SNAPSHOT MAIS RECENTE", "Workspace-detaljer": "Detalhes dos espaços de trabalho", "Gå til scan": "Ir para análise", "{count} workspaces valgt": "{count} espaços de trabalho selecionados", "Administrer valget under Workspaces.": "Gira a seleção em Espaços de trabalho.", "Vælg workspaces": "Selecionar espaços de trabalho"
});

function detectLanguage() {
  const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY);
  if (LOCALES[stored]) return stored;
  for (const language of navigator.languages || [navigator.language]) {
    const base = language.toLowerCase().split("-")[0];
    if (LOCALES[base]) return base;
  }
  return "en";
}

const state = {
  locale: detectLanguage(),
  activeView: "overview",
  summary: null,
  coverage: null,
  facets: null,
  permissions: { items: [], page: 1, pageSize: 50, total: 0, totalPages: 1 },
  workspaces: { items: [], page: 1, pageSize: 24, total: 0, totalPages: 1 },
  userMappings: null,
  mappingBusy: false,
  migrationPlan: null,
  migrationPlanLoading: false,
  migrationPlanDetail: "unsupported",
  migrationJob: null,
  migrationTimer: null,
  permissionRequest: null,
  workspaceRequest: null,
  auth: null,
  authTimer: null,
  scanInventory: null,
  scanInventoryTenant: null,
  scanInventoryLoading: false,
  scan: null,
  scanTimer: null,
  scanWasActive: false
};

const byId = (id) => document.getElementById(id);
const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
})[char]);
const t = (source, values = {}) => {
  const translated = translations[state.locale]?.[source] || source;
  return Object.entries(values).reduce((text, [key, value]) => text.replaceAll(`{${key}}`, value), translated);
};
const localeName = () => LOCALES[state.locale];

function applyStaticTranslations() {
  document.documentElement.lang = state.locale;
  document.querySelectorAll("body *:not(script):not(style)").forEach((element) => {
    for (const attribute of ["placeholder", "aria-label", "title"]) {
      if (!element.hasAttribute(attribute)) continue;
      const sourceKey = `i18n${attribute.replace("-", "")}`;
      element.dataset[sourceKey] ||= element.getAttribute(attribute);
      element.setAttribute(attribute, t(element.dataset[sourceKey]));
    }
    element.childNodes.forEach((node) => {
      if (node.nodeType !== Node.TEXT_NODE || !node.textContent.trim()) return;
      node.i18nSource ||= node.textContent.trim();
      const translated = t(node.i18nSource);
      node.textContent = node.textContent.replace(node.textContent.trim(), translated);
    });
  });
}

function setLanguage(language, persist = true) {
  state.locale = LOCALES[language] ? language : "en";
  if (persist) localStorage.setItem(LANGUAGE_STORAGE_KEY, state.locale);
  byId("language-select").value = state.locale;
  applyStaticTranslations();
  switchView(state.activeView);
  if (state.summary) renderOverview();
  if (state.facets) renderFilters();
  if (state.coverage) renderCoverage();
  if (state.permissions) renderPermissions();
  if (state.workspaces) renderWorkspaces();
  renderUserMappings();
  renderPermissionMigration();
  renderAuth();
  renderScan();
  if (state.summary) byId("snapshot-date").textContent = formatDate(state.summary.generatedAtUtc, true);
}

async function api(path, options = {}) {
  const headers = options.body ? { "Content-Type": "application/json" } : {};
  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_ROOT}${path}`, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
    signal: options.signal
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(response.status === 401 ? t("API-token mangler eller er ugyldig") : (detail.detail || `${path}: HTTP ${response.status}`));
  }
  return response.json();
}

function saveApiToken() {
  const value = byId("api-token").value.trim();
  if (value) localStorage.setItem(TOKEN_STORAGE_KEY, value);
  else localStorage.removeItem(TOKEN_STORAGE_KEY);
}

function formatDate(value, withTime = false) {
  if (!value) return t("Ukendt");
  return new Intl.DateTimeFormat(localeName(), withTime ? { dateStyle: "medium", timeStyle: "short" } : { dateStyle: "medium" }).format(new Date(value));
}

function formatTime(value) {
  return new Intl.DateTimeFormat(localeName(), { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date(value));
}

function calculateScanEstimate(workspaceCount, includeArtifacts) {
  const accessPacingSeconds = Math.ceil(Math.max(0, workspaceCount - 1) * 18.1);
  const metadataBatches = includeArtifacts && workspaceCount > 0 ? Math.ceil(workspaceCount / 100) : 0;
  return {
    workspaceCount,
    accessPacingSeconds,
    metadataBatches,
    minimumSeconds: 30 + accessPacingSeconds + (metadataBatches * 60),
    maximumSeconds: 60 + accessPacingSeconds + (metadataBatches * 180)
  };
}

function formatDuration(seconds) {
  const minutes = Math.ceil(seconds / 60);
  if (minutes < 1) return t("under 1 min.");
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return hours > 0
    ? t("{hours} t. {minutes} min.", { hours: hours.toLocaleString(localeName()), minutes: remainingMinutes.toLocaleString(localeName()) })
    : t("{minutes} min.", { minutes: minutes.toLocaleString(localeName()) });
}

function renderScanEstimate() {
  const active = ["queued", "running", "importing"].includes(state.scan?.status);
  const stageWorkspaceCount = Number(state.scan?.stage?.match(/for\s+(\d+)\s+workspaces/i)?.[1]) || 0;
  const actualEstimate = active
    ? state.scan?.estimate || (stageWorkspaceCount ? calculateScanEstimate(stageWorkspaceCount, byId("scan-artifacts").checked) : null)
    : null;
  const selectedCount = selectedWorkspaceIds().length;
  const workspaceCount = actualEstimate?.workspaceCount ?? selectedCount;
  const estimate = actualEstimate || calculateScanEstimate(workspaceCount, byId("scan-artifacts").checked);
  const count = workspaceCount.toLocaleString(localeName());
  const basis = actualEstimate
    ? t("Baseret på {count} workspaces fundet i tenant", { count })
    : t("Baseret på {count} valgte workspaces", { count });
  const pacing = formatDuration(estimate.accessPacingSeconds);

  byId("scan-estimate-duration").textContent = t("Ca. {minimum}–{maximum}", {
    minimum: formatDuration(estimate.minimumSeconds),
    maximum: formatDuration(estimate.maximumSeconds)
  });
  byId("scan-estimate-basis").textContent = `${basis}.`;
  const metadataBatchKey = estimate.metadataBatches === 1 ? "API-pacing: {duration} · {batches} metadata-batch" : "API-pacing: {duration} · {batches} metadata-batches";
  byId("scan-estimate-breakdown").textContent = `${estimate.metadataBatches
    ? t(metadataBatchKey, { duration: pacing, batches: estimate.metadataBatches.toLocaleString(localeName()) })
    : t("API-pacing: {duration} · uden metadata-scan", { duration: pacing })}. ${t("Retries og Microsoft-behandlingstid kan forlænge scanningen.")}`;
}

function selectedWorkspaceIds() {
  return [...document.querySelectorAll("#scan-workspace-tree input[data-workspace-id]:checked")].map((input) => input.dataset.workspaceId);
}

function updateCapacityCheckboxes() {
  document.querySelectorAll("#scan-workspace-tree input[data-capacity-id]").forEach((capacityInput) => {
    const children = [...document.querySelectorAll(`#scan-workspace-tree input[data-parent-capacity="${capacityInput.dataset.capacityId}"]`)];
    const selected = children.filter((input) => input.checked).length;
    capacityInput.checked = children.length > 0 && selected === children.length;
    capacityInput.indeterminate = selected > 0 && selected < children.length;
  });
  const selectedCount = selectedWorkspaceIds().length;
  byId("scan-selection-count").textContent = t("{count} valgt", { count: selectedCount.toLocaleString(localeName()) });
  byId("scan-selection-summary").textContent = t("{count} workspaces valgt", { count: selectedCount.toLocaleString(localeName()) });
  renderScanEstimate();
  renderScan();
}

function renderScanInventory() {
  const tree = byId("scan-workspace-tree");
  if (state.scanInventoryLoading) {
    tree.innerHTML = `<p class="workspace-tree-message">${t("Henter kapaciteter og workspaces...")}</p>`;
    return;
  }
  if (!state.scanInventory) {
    tree.innerHTML = `<p class="workspace-tree-message">${t("Vælg en tenant for at hente workspaces.")}</p>`;
    byId("scan-selection-count").textContent = t("{count} valgt", { count: "0" });
    return;
  }
  if (!state.scanInventory.capacities.length) {
    tree.innerHTML = `<p class="workspace-tree-message">${t("Ingen kapaciteter eller workspaces blev fundet.")}</p>`;
    return;
  }
  tree.innerHTML = state.scanInventory.capacities.map((capacity) => `
    <details class="capacity-node" open>
      <summary class="capacity-row">
        <input type="checkbox" data-capacity-id="${escapeHtml(capacity.id)}" aria-label="${escapeHtml(t("Vælg alle workspaces i {capacity}", { capacity: capacity.name }))}" ${capacity.workspaces.length ? "" : "disabled"}>
        <span class="capacity-name"><strong>${escapeHtml(capacity.name)}</strong><small>${escapeHtml([capacity.sku, capacity.state].filter(Boolean).join(" · "))}</small></span>
        <span class="capacity-count">${capacity.workspaces.length.toLocaleString(localeName())}</span>
      </summary>
      <div class="workspace-children">
        ${capacity.workspaces.length ? capacity.workspaces.map((workspace) => `
          <label class="workspace-tree-row">
            <input type="checkbox" data-workspace-id="${escapeHtml(workspace.id)}" data-parent-capacity="${escapeHtml(capacity.id)}">
            <span><strong>${escapeHtml(workspace.name)}</strong><small>${escapeHtml(workspace.type)}</small></span>
          </label>`).join("") : `<p class="workspace-tree-empty">${t("Ingen workspaces")}</p>`}
      </div>
    </details>`).join("");
  updateCapacityCheckboxes();
}

async function loadScanInventory() {
  const tenantId = byId("scan-tenant").value.trim();
  state.scanInventory = null;
  state.scanInventoryTenant = null;
  if (!tenantId) {
    renderScanInventory();
    renderScan();
    return;
  }
  state.scanInventoryLoading = true;
  renderScanInventory();
  try {
    const includePersonal = byId("scan-personal").checked;
    state.scanInventory = await api(`/scans/inventory?tenantId=${encodeURIComponent(tenantId)}&includePersonalWorkspaces=${includePersonal}`);
    state.scanInventoryTenant = tenantId;
  } catch (error) {
    byId("scan-form-error").textContent = error.message;
    byId("scan-form-error").classList.remove("hidden");
  } finally {
    state.scanInventoryLoading = false;
    renderScanInventory();
    renderScan();
  }
}

function renderOverview() {
  const { counts, principalCounts, typeCounts, recentItems } = state.summary;
  byId("metric-workspaces").textContent = counts.workspaces.toLocaleString(localeName());
  byId("metric-artifacts").textContent = counts.artifacts.toLocaleString(localeName());
  byId("metric-principals").textContent = counts.principals.toLocaleString(localeName());
  byId("metric-assignments").textContent = counts.assignments.toLocaleString(localeName());
  byId("metric-types").textContent = `${counts.artifactTypes.toLocaleString(localeName())} ${t("item-typer")}`;

  const maxCount = principalCounts[0]?.count || 1;
  byId("principal-bars").innerHTML = principalCounts.map((principal) => `
    <div class="bar-row"><div class="bar-person"><strong>${escapeHtml(principal.principalName)}</strong><small>${escapeHtml(principal.principalEmail)}</small></div>
    <div class="bar-track"><div class="bar-fill" style="width:${(principal.count / maxCount) * 100}%"></div></div><div class="bar-count">${principal.count.toLocaleString(localeName())}</div></div>
  `).join("") || `<div class="empty-state">${t("Ingen item-rettigheder fundet.")}</div>`;

  byId("type-list").innerHTML = typeCounts.map((item) => `
    <div class="type-row"><span class="type-glyph">${escapeHtml(item.type.slice(0, 2).toUpperCase())}</span><strong>${escapeHtml(item.type)}</strong><span>${item.count.toLocaleString(localeName())}</span></div>
  `).join("");
  byId("recent-items").innerHTML = recentItems.map((item) => `
    <div class="recent-item"><strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(item.type)} · ${escapeHtml(item.workspaceName)}</span><span>${formatDate(item.modified, true)}</span></div>
  `).join("") || `<div class="empty-state">${t("Ingen datooplysninger fundet.")}</div>`;
}

function fillSelect(id, values, label, getValue = (value) => value, getLabel = (value) => value) {
  byId(id).innerHTML = `<option value="">${label}</option>` + values.map((value) => `<option value="${escapeHtml(getValue(value))}">${escapeHtml(getLabel(value))}</option>`).join("");
}

function renderFilters() {
  fillSelect("workspace-filter", state.facets.workspaces, t("Alle workspaces"), (item) => item.id, (item) => item.name);
  fillSelect("type-filter", state.facets.artifactTypes, t("Alle item-typer"));
  fillSelect("access-filter", state.facets.accessRights, t("Alle adgangstyper"));
}

function permissionQuery() {
  const parameters = new URLSearchParams({ page: state.permissions.page, pageSize: state.permissions.pageSize });
  const values = {
    q: byId("permission-search").value.trim(),
    workspaceId: byId("workspace-filter").value,
    artifactType: byId("type-filter").value,
    accessRight: byId("access-filter").value
  };
  Object.entries(values).forEach(([key, value]) => { if (value) parameters.set(key, value); });
  return parameters;
}

async function loadPermissions(resetPage = false) {
  if (resetPage) state.permissions.page = 1;
  state.permissionRequest?.abort();
  state.permissionRequest = new AbortController();
  try {
    state.permissions = await api(`/permissions?${permissionQuery()}`, { signal: state.permissionRequest.signal });
    renderPermissions();
  } catch (error) {
    if (error.name !== "AbortError") throw error;
  }
}

function renderPermissions() {
  byId("permission-count").textContent = state.permissions.total.toLocaleString(localeName());
  byId("permissions-empty").classList.toggle("hidden", state.permissions.items.length > 0);
  byId("permissions-body").innerHTML = state.permissions.items.map((row) => `
    <tr><td class="person-cell"><strong>${escapeHtml(row.principalName)}</strong><span>${escapeHtml(row.principalEmail)}</span></td>
    <td>${escapeHtml(row.workspaceName)}</td><td>${escapeHtml(row.artifactName)}</td><td><span class="badge">${escapeHtml(row.artifactType)}</span></td>
    <td><span class="badge access-badge">${escapeHtml(row.access)}</span></td><td><span class="status">${escapeHtml(row.artifactState)}</span></td></tr>
  `).join("");
  renderPagination("permissions-pagination", state.permissions, (page) => { state.permissions.page = page; loadPermissions(); });
}

function renderPagination(id, result, onPage) {
  if (result.totalPages <= 1) { byId(id).innerHTML = ""; return; }
  byId(id).innerHTML = `<button data-page="${result.page - 1}" ${result.page === 1 ? "disabled" : ""}>←</button><span>${t("Side {page} af {total}", { page: result.page.toLocaleString(localeName()), total: result.totalPages.toLocaleString(localeName()) })}</span><button data-page="${result.page + 1}" ${result.page === result.totalPages ? "disabled" : ""}>→</button>`;
  byId(id).querySelectorAll("button:not(:disabled)").forEach((button) => button.addEventListener("click", () => onPage(Number(button.dataset.page))));
}

function workspaceQuery() {
  const parameters = new URLSearchParams({ page: state.workspaces.page, pageSize: state.workspaces.pageSize });
  const query = byId("workspace-search").value.trim();
  if (query) parameters.set("q", query);
  return parameters;
}

async function loadWorkspaces(resetPage = false) {
  if (resetPage) state.workspaces.page = 1;
  state.workspaceRequest?.abort();
  state.workspaceRequest = new AbortController();
  try {
    state.workspaces = await api(`/workspaces?${workspaceQuery()}`, { signal: state.workspaceRequest.signal });
    renderWorkspaces();
  } catch (error) {
    if (error.name !== "AbortError") throw error;
  }
}

function renderWorkspaces() {
  byId("workspace-grid").innerHTML = state.workspaces.items.map((workspace) => `
    <button class="workspace-card" data-workspace-id="${escapeHtml(workspace.id)}"><div class="workspace-card-head"><div><h3>${escapeHtml(workspace.name)}</h3><span class="status">${escapeHtml(workspace.state || "Active")}</span></div><p>${escapeHtml(workspace.id)}</p></div>
    <div class="workspace-card-stats"><div><span>${t("Items")}</span><strong>${workspace.artifacts.toLocaleString(localeName())}</strong></div><div><span>${t("Principals")}</span><strong>${workspace.principals.toLocaleString(localeName())}</strong></div><div><span>${t("Roller")}</span><strong>${workspace.roles.toLocaleString(localeName())}</strong></div></div></button>
  `).join("");
  document.querySelectorAll("#workspace-grid [data-workspace-id]").forEach((button) => button.addEventListener("click", () => openWorkspace(button.dataset.workspaceId)));
  renderPagination("workspaces-pagination", state.workspaces, (page) => { state.workspaces.page = page; loadWorkspaces(); });
}

async function loadUserMappings() {
  const tenantId = byId("mapping-tenant").value;
  if (!tenantId) { state.userMappings = null; renderUserMappings(); renderPermissionMigration(); return; }
  try {
    state.userMappings = await api(`/tenants/${encodeURIComponent(tenantId)}/user-mappings`);
    byId("mapping-error").classList.add("hidden");
    renderUserMappings();
    renderPermissionMigration();
  } catch (error) {
    showMappingError(error);
  }
}

function invalidateMigrationPlan() {
  state.migrationPlan = null;
  byId("migration-confirm").checked = false;
  renderPermissionMigration();
}

async function syncDirectoryUsers() {
  const tenantId = byId("mapping-tenant").value;
  if (!tenantId) return;
  state.mappingBusy = true;
  invalidateMigrationPlan();
  renderUserMappings();
  try {
    await api(`/tenants/${encodeURIComponent(tenantId)}/directory-users/sync`, { method: "POST" });
    await loadUserMappings();
  } catch (error) {
    showMappingError(error);
  } finally {
    state.mappingBusy = false;
    renderUserMappings();
  }
}

function showMappingError(error) {
  byId("mapping-error").textContent = error.message;
  byId("mapping-error").classList.remove("hidden");
}

function renderUserMappings() {
  if (!byId("mapping-body")) return;
  const data = state.userMappings;
  const hasUsers = Boolean(data?.sourceUsers.length);
  const mappedCount = data?.sourceUsers.filter((user) => user.targetUserId).length || 0;
  byId("mapping-table").classList.toggle("hidden", !hasUsers);
  byId("mapping-empty").classList.toggle("hidden", hasUsers);
  byId("mapping-empty").textContent = data?.directoryUserCount
    ? t("Ingen tenant-brugere med Fabric-adgang blev fundet.")
    : t("Vælg en tenant og hent tenant-brugerne.");
  byId("mapping-summary").textContent = data ? t("{sources} Fabric-brugere · {targets} mulige mål · {mapped} mappet", {
    sources: data.sourceUsers.length.toLocaleString(localeName()),
    targets: data.targetUsers.length.toLocaleString(localeName()),
    mapped: mappedCount.toLocaleString(localeName())
  }) : "";
  byId("mapping-sync").disabled = state.mappingBusy || !byId("mapping-tenant").value;
  byId("mapping-sync").textContent = t(state.mappingBusy ? "Henter brugere..." : "Hent tenant-brugere");
  if (!hasUsers) { byId("mapping-body").innerHTML = ""; return; }
  byId("mapping-body").innerHTML = data.sourceUsers.map((source) => `
    <tr><td class="person-cell"><strong>${escapeHtml(source.displayName)}</strong><span>${escapeHtml(source.userPrincipalName || source.mail)}</span></td>
    <td><select class="mapping-select" data-source-user-id="${escapeHtml(source.id)}" ${state.mappingBusy ? "disabled" : ""}>
      <option value="">${t("Vælg ny bruger")}</option>
      ${data.targetUsers.map((target) => `<option value="${escapeHtml(target.id)}" ${target.id === source.targetUserId ? "selected" : ""} ${target.mappedSourceUserId && target.mappedSourceUserId !== source.id ? "disabled" : ""}>${escapeHtml(target.displayName)} · ${escapeHtml(target.userPrincipalName || target.mail)}</option>`).join("")}
    </select></td><td><span class="status-chip" data-status="${source.targetUserId ? "completed" : "idle"}">${t(source.targetUserId ? "Mappet" : "Ikke mappet")}</span></td></tr>
  `).join("");
  document.querySelectorAll(".mapping-select").forEach((select) => select.addEventListener("change", saveUserMapping));
}

async function saveUserMapping(event) {
  const tenantId = byId("mapping-tenant").value;
  const sourceUserId = event.target.dataset.sourceUserId;
  const targetUserId = event.target.value;
  state.mappingBusy = true;
  renderUserMappings();
  try {
    state.userMappings = await api(`/tenants/${encodeURIComponent(tenantId)}/user-mappings/${encodeURIComponent(sourceUserId)}`, targetUserId
      ? { method: "PUT", body: { targetUserId } }
      : { method: "DELETE" });
    invalidateMigrationPlan();
    byId("mapping-error").classList.add("hidden");
  } catch (error) {
    showMappingError(error);
  } finally {
    state.mappingBusy = false;
    renderUserMappings();
  }
}

async function loadPermissionMigrationPlan() {
  const tenantId = byId("mapping-tenant").value;
  if (!tenantId) return;
  state.migrationPlanLoading = true;
  renderPermissionMigration();
  try {
    state.migrationPlan = await api(`/tenants/${encodeURIComponent(tenantId)}/permission-migration/plan`);
    state.migrationPlanDetail = state.migrationPlan.counts.unsupported ? "unsupported" : "coveredByWorkspaceRoles";
    byId("migration-confirm").checked = false;
    byId("migration-error").classList.add("hidden");
  } catch (error) {
    showMigrationError(error);
  } finally {
    state.migrationPlanLoading = false;
    renderPermissionMigration();
    if (state.migrationPlan) {
      byId("migration-plan").scrollIntoView({ behavior: "smooth", block: "nearest" });
      byId("migration-confirm").focus({ preventScroll: true });
    }
  }
}

function showMigrationError(error) {
  byId("migration-error").textContent = error.message;
  byId("migration-error").classList.remove("hidden");
}

function renderMigrationPlanDetails(plan) {
  const categories = {
    workspaceRoles: {
      title: "Workspace-roller",
      summary: "{count} workspace-roller anvendes",
      items: plan?.operations.filter((item) => item.kind === "workspaceRole") || []
    },
    datasetRights: {
      title: "Semantic model-rettigheder",
      summary: "{count} semantic model-rettigheder anvendes",
      items: plan?.operations.filter((item) => item.kind === "datasetRight") || []
    },
    coveredByWorkspaceRoles: {
      title: "Dækket af workspace-rolle",
      summary: "{count} rettigheder dækkes af workspace-roller",
      items: plan?.coveredByWorkspaceRole || []
    },
    unsupported: {
      title: "Ikke-understøttede rettigheder",
      summary: "{count} rettigheder kan ikke kopieres præcist",
      items: plan?.unsupported || []
    }
  };
  const selected = categories[state.migrationPlanDetail] || categories.unsupported;
  document.querySelectorAll("[data-migration-detail]").forEach((button) => {
    const active = button.dataset.migrationDetail === state.migrationPlanDetail;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active);
  });
  byId("migration-detail-list").classList.toggle("hidden", !plan);
  byId("migration-detail-title").textContent = t(selected.title);
  byId("migration-detail-summary").textContent = t(selected.summary, { count: selected.items.length.toLocaleString(localeName()) });
  byId("migration-detail-body").innerHTML = selected.items.map((item) => {
    const detail = item.reason
      ? t(item.reason)
      : item.workspaceRole
        ? t("Dækket af workspace-rollen {role}", { role: item.workspaceRole })
        : t("Anvendes præcist");
    return `<tr>
      <td>${escapeHtml(item.sourceUserName)}</td>
      <td>${escapeHtml(item.targetUserName)}</td>
      <td>${escapeHtml(item.workspaceName)}</td>
      <td>${escapeHtml(item.artifactName || "–")}</td>
      <td><span class="badge">${escapeHtml(item.artifactType || "Workspace")}</span></td>
      <td><span class="badge access-badge">${escapeHtml(item.right)}</span></td>
      <td class="migration-detail-description">${escapeHtml(detail)}</td>
    </tr>`;
  }).join("");
}

function renderPermissionMigration() {
  if (!byId("migration-stage")) return;
  const plan = state.migrationPlan;
  const job = state.migrationJob || { status: "idle", progress: 0, stage: "Klar til at anvende mappede rettigheder", logs: [], failures: [] };
  const active = ["queued", "running", "cancelling"].includes(job.status);
  const tenantSelected = Boolean(byId("mapping-tenant").value);
  const mappedCount = state.userMappings?.sourceUsers.filter((user) => user.targetUserId).length || 0;
  byId("migration-plan-load").disabled = active || state.migrationPlanLoading || !tenantSelected || mappedCount === 0;
  byId("migration-plan-load").textContent = t(state.migrationPlanLoading ? "Indlæser plan..." : "Gennemgå plan");
  byId("migration-plan").classList.toggle("hidden", !plan);
  byId("migration-workspace-count").textContent = (plan?.counts.workspaceRoles || 0).toLocaleString(localeName());
  byId("migration-dataset-count").textContent = (plan?.counts.datasetRights || 0).toLocaleString(localeName());
  byId("migration-covered-count").textContent = (plan?.counts.coveredByWorkspaceRoles || 0).toLocaleString(localeName());
  byId("migration-unsupported-count").textContent = (plan?.counts.unsupported || 0).toLocaleString(localeName());
  renderMigrationPlanDetails(plan);
  byId("migration-confirm").disabled = active;
  byId("migration-start").disabled = active || !plan?.counts.total || !byId("migration-confirm").checked;
  const migrationStageMatch = job.stage?.match(/^Anvender rettighed (\d+)\/(\d+): (.*)$/);
  byId("migration-stage").textContent = migrationStageMatch
    ? t("Anvender rettighed {current}/{total}: {workspace}", { current: Number(migrationStageMatch[1]), total: Number(migrationStageMatch[2]), workspace: migrationStageMatch[3] })
    : t(job.stage);
  byId("migration-percent").textContent = `${job.progress || 0}%`;
  byId("migration-progress-bar").style.width = `${job.progress || 0}%`;
  byId("migration-progress-bar").parentElement.setAttribute("aria-valuenow", job.progress || 0);
  byId("migration-current").textContent = job.total
    ? t("Rettighed {current}/{total}", { current: (job.current || 0).toLocaleString(localeName()), total: job.total.toLocaleString(localeName()) })
    : t("Ikke startet");
  byId("migration-cancel").classList.toggle("hidden", !active);
  byId("migration-wait").classList.toggle("hidden", !job.wait);
  if (job.wait) {
    byId("migration-wait-title").textContent = t("Venter {seconds} sek. før næste API-kald", { seconds: Math.ceil(job.wait.seconds).toLocaleString(localeName()) });
    byId("migration-wait-detail").textContent = `${t(job.wait.reason === "retry" ? "Midlertidig API-fejl" : "Throttle-beskyttelse")} · ${t("Forventet fortsættelse kl. {time}", { time: formatTime(job.wait.nextCallAtUtc) })}`;
  }
  byId("migration-result").classList.toggle("hidden", !job.result);
  byId("migration-result").innerHTML = job.result ? Object.entries(job.result).map(([key, value]) => `<div><strong>${value.toLocaleString(localeName())}</strong><span>${escapeHtml(t(key))}</span></div>`).join("") : "";
  byId("migration-failures").classList.toggle("hidden", !job.failures?.length);
  byId("migration-failures").innerHTML = job.failures?.length ? `<strong>${t("Fejl under migration")}</strong>${job.failures.slice(0, 20).map((failure) => `<span>${escapeHtml(failure.targetUserName)} · ${escapeHtml(failure.workspaceName)}${failure.artifactName ? ` · ${escapeHtml(failure.artifactName)}` : ""}: ${escapeHtml(failure.error)}</span>`).join("")}` : "";
  byId("migration-log").textContent = job.logs?.length ? job.logs.join("\n") : t("Ingen aktivitet endnu.");
}

async function pollPermissionMigration() {
  clearTimeout(state.migrationTimer);
  try {
    state.migrationJob = await api("/permission-migrations/current");
    renderPermissionMigration();
    if (["queued", "running", "cancelling"].includes(state.migrationJob.status)) state.migrationTimer = setTimeout(pollPermissionMigration, 1000);
  } catch (error) {
    showMigrationError(error);
  }
}

async function startPermissionMigration() {
  const tenantId = byId("mapping-tenant").value;
  try {
    state.migrationJob = await api(`/tenants/${encodeURIComponent(tenantId)}/permission-migration`, { method: "POST", body: { confirmed: true } });
    byId("migration-error").classList.add("hidden");
    renderPermissionMigration();
    state.migrationTimer = setTimeout(pollPermissionMigration, 300);
  } catch (error) {
    showMigrationError(error);
  }
}

async function cancelPermissionMigration() {
  try {
    state.migrationJob = await api("/permission-migrations/current", { method: "DELETE" });
    renderPermissionMigration();
  } catch (error) {
    showMigrationError(error);
  }
}

async function openWorkspace(workspaceId) {
  const detail = await api(`/workspaces/${encodeURIComponent(workspaceId)}`);
  byId("dialog-title").textContent = detail.workspace.name;
  byId("dialog-content").innerHTML = `
    <div class="dialog-stats"><div class="dialog-stat"><span>FABRIC-ITEMS</span><strong>${detail.counts.artifacts.toLocaleString(localeName())}</strong></div><div class="dialog-stat"><span>ITEM-PRINCIPALS</span><strong>${detail.counts.itemPrincipals.toLocaleString(localeName())}</strong></div><div class="dialog-stat"><span>WORKSPACE-${t("Roller").toUpperCase()}</span><strong>${detail.counts.roles.toLocaleString(localeName())}</strong></div></div>
    <section class="dialog-section"><h3>${t("Workspace-adgang")}</h3><div class="dialog-list">${detail.roles.map((role) => `<div class="dialog-row"><div><strong>${escapeHtml(role.displayName)}</strong><span>${escapeHtml(role.email || role.principalType)}</span></div><span class="badge access-badge">${escapeHtml(role.role)}</span></div>`).join("") || `<p class="empty-state">${t("Ingen direkte roller")}</p>`}</div></section>
    <section class="dialog-section"><h3>${t("Item-fordeling")}</h3><div class="dialog-list">${detail.artifactTypes.map((item) => `<div class="dialog-row"><div><strong>${escapeHtml(item.type)}</strong><span>${t("Artifact-kategori")}</span></div><span class="badge">${item.count.toLocaleString(localeName())}</span></div>`).join("") || `<p class="empty-state">${t("Ingen items i scanner-resultatet")}</p>`}</div></section>`;
  byId("workspace-dialog").showModal();
}

function renderCoverage() {
  byId("coverage-score").textContent = state.coverage.covered.length;
  byId("covered-list").innerHTML = state.coverage.covered.map((item) => `<li>${escapeHtml(t(item))}</li>`).join("");
  byId("not-covered-list").innerHTML = state.coverage.notCovered.map((item) => `<li>${escapeHtml(t(item))}</li>`).join("");
  byId("api-notes-list").innerHTML = state.coverage.apiNotes.map((item) => `<li>${escapeHtml(t(item))}</li>`).join("");
}

function renderScan() {
  const scan = state.scan || { status: "idle", progress: 0, stage: "Klar til scanning", logs: [] };
  const active = ["queued", "running", "importing"].includes(scan.status);
  const legacyWorkspaceMatch = scan.stage?.match(/^Workspace (\d+) af (\d+):/);
  const workspaceProgress = scan.workspaceProgress || (legacyWorkspaceMatch
    ? { current: Number(legacyWorkspaceMatch[1]), total: Number(legacyWorkspaceMatch[2]) }
    : null);
  const labels = { idle: "Klar", queued: "I kø", running: "Kører", importing: "Importerer", completed: "Fuldført", failed: "Fejlet" };
  byId("scan-availability").textContent = t(labels[scan.status] || scan.status);
  byId("scan-availability").dataset.status = scan.status;
  const accessStageMatch = scan.stage?.match(/^Læser adgang for (\d+) workspaces$/);
  byId("scan-stage").textContent = workspaceProgress
    ? t("Scanner workspace {current}/{total}", workspaceProgress)
    : accessStageMatch
      ? t("Læser adgang for {count} workspaces", { count: Number(accessStageMatch[1]) })
      : t(scan.stage);
  byId("scan-percent").textContent = `${scan.progress}%`;
  byId("scan-progress").style.width = `${scan.progress}%`;
  byId("scan-progress").parentElement.setAttribute("aria-valuenow", scan.progress);
  byId("scan-started").textContent = scan.startedAtUtc ? t("Startet {date}", { date: formatDate(scan.startedAtUtc, true) }) : t("Ikke startet");
  byId("scan-completed").textContent = scan.completedAtUtc ? t("Afsluttet {date}", { date: formatDate(scan.completedAtUtc, true) }) : "";
  const wait = active ? scan.wait : null;
  byId("scan-wait").classList.toggle("hidden", !wait);
  if (wait) {
    const remainingSeconds = Math.max(0, Math.ceil((Date.parse(wait.nextCallAtUtc) - Date.now()) / 1000));
    const apiName = t(wait.api === "WorkspaceAccess" ? "Fabric workspace access API" : "Power BI metadata API");
    const waitTitles = { rateLimit: "Throttle-beskyttelse", retry: "Midlertidig API-fejl", metadataProcessing: "Power BI behandler metadata" };
    const waitDetails = {
      rateLimit: t("Venter mellem kald til {api} for at holde sig under grænsen på {limit} kald i timen.", { api: apiName, limit: wait.hourlyLimit.toLocaleString(localeName()) }),
      retry: t("Kaldet forsøges automatisk igen. Microsofts Retry-After eller eksponentiel backoff respekteres."),
      metadataProcessing: t("Power BI forbereder batchresultatet. Status kontrolleres hvert 30. sekund.")
    };
    byId("scan-wait-title").textContent = t(remainingSeconds > 0 ? "Næste API-kald om {seconds} sek." : "Næste API-kald nu", { seconds: remainingSeconds.toLocaleString(localeName()) });
    byId("scan-wait-detail").textContent = `${t(waitTitles[wait.reason] || wait.reason)} · ${waitDetails[wait.reason] || apiName}`;
    byId("scan-wait-next").textContent = t("Forventet fortsættelse kl. {time}", { time: formatTime(wait.nextCallAtUtc) });
  }
  byId("scan-log").textContent = scan.logs?.length ? scan.logs.join("\n") : t("Ingen aktivitet endnu.");
  const authenticated = state.auth?.status === "authenticated";
  const tenantSelected = Boolean(byId("scan-tenant").value);
  const hasWorkspaceSelection = selectedWorkspaceIds().length > 0;
  byId("scan-start").disabled = active || !authenticated || !tenantSelected || !hasWorkspaceSelection;
  byId("scan-start").textContent = t(active ? "Scan kører..." : !authenticated ? "Log ind for at scanne" : !tenantSelected ? "Vælg en tenant" : hasWorkspaceSelection ? "Start scan" : "Vælg mindst ét workspace");
  byId("scan-result").classList.toggle("hidden", !scan.result);
  byId("scan-result").innerHTML = scan.result ? Object.entries(scan.result).map(([key, value]) => `<div><strong>${Number(value).toLocaleString(localeName())}</strong><span>${escapeHtml(t(key))}</span></div>`).join("") : "";
  byId("scan-log").scrollTop = byId("scan-log").scrollHeight;
  state.scanWasActive ||= active;
  renderScanEstimate();
}

function renderAuth() {
  const auth = state.auth || { status: "idle", stage: "Ikke logget ind" };
  const labels = { idle: "Ikke logget ind", waiting: "Afventer", authenticated: "Logget ind", failed: "Fejlet", unavailable: "Utilgængelig" };
  const waiting = auth.status === "waiting";
  const authenticated = auth.status === "authenticated";
  byId("auth-status").textContent = t(labels[auth.status] || auth.status);
  byId("auth-status").dataset.status = auth.status;
  byId("auth-stage").textContent = t(auth.stage);
  byId("auth-account").classList.toggle("hidden", !authenticated);
  const authType = auth.account?.authType === "servicePrincipal" ? t("Service principal") : t("Microsoft account");
  byId("auth-account").textContent = authenticated ? `${authType} · ${auth.account.user} · ${auth.account.name}` : "";
  byId("scan-auth-summary").textContent = authenticated ? `${authType} · ${auth.account.user}` : t("Ikke logget ind");
  const deviceLogin = waiting && Boolean(auth.userCode);
  byId("auth-device").classList.toggle("hidden", !deviceLogin);
  byId("auth-device").querySelector("span").textContent = t("Åbn Microsoft-login og indtast koden");
  byId("auth-device-code").textContent = auth.userCode || "";
  byId("auth-device-link").textContent = t("Åbn Microsoft-login");
  byId("auth-device-link").href = auth.loginUrl || "https://microsoft.com/devicelogin";
  const tenantSelect = byId("scan-tenant");
  const selectedTenant = tenantSelect.value;
  tenantSelect.innerHTML = authenticated && auth.tenants?.length
    ? `<option value="">${t("Vælg tenant")}</option>` + auth.tenants.map((tenant) => `<option value="${escapeHtml(tenant.id)}">${escapeHtml(tenant.name)}${tenant.domain ? ` · ${escapeHtml(tenant.domain)}` : ""}</option>`).join("")
    : `<option value="">${t(authenticated ? "Ingen tilgængelige tenants" : "Log ind for at hente tenants")}</option>`;
  tenantSelect.disabled = !authenticated || !auth.tenants?.length;
  if (auth.tenants?.some((tenant) => tenant.id === selectedTenant)) tenantSelect.value = selectedTenant;
  if (!tenantSelect.value && auth.tenants?.length === 1) tenantSelect.value = auth.tenants[0].id;
  const mappingTenant = byId("mapping-tenant");
  const selectedMappingTenant = mappingTenant.value;
  mappingTenant.innerHTML = tenantSelect.innerHTML;
  mappingTenant.disabled = tenantSelect.disabled;
  if (auth.tenants?.some((tenant) => tenant.id === selectedMappingTenant)) mappingTenant.value = selectedMappingTenant;
  if (!mappingTenant.value && auth.tenants?.length === 1) mappingTenant.value = auth.tenants[0].id;
  byId("auth-login").disabled = waiting || auth.status === "unavailable";
  byId("auth-login").textContent = t(waiting ? "Afventer Microsoft..." : auth.status === "unavailable" ? "Kræver container-rebuild" : authenticated ? "Skift konto" : "Log ind med Microsoft");
  byId("auth-logout").classList.toggle("hidden", !authenticated);
  byId("sp-login").disabled = waiting || auth.status === "unavailable";
  renderScan();
  renderUserMappings();
}

async function pollAuth() {
  clearTimeout(state.authTimer);
  try {
    state.auth = await api("/auth/current");
    renderAuth();
    if (state.auth.status === "waiting") state.authTimer = setTimeout(pollAuth, 1000);
    else if (state.auth.status === "authenticated" && byId("scan-tenant").value && state.scanInventoryTenant !== byId("scan-tenant").value) await loadScanInventory();
  } catch (authError) {
    byId("auth-error").textContent = authError.message;
    byId("auth-error").classList.remove("hidden");
  }
}

async function startLogin() {
  const error = byId("auth-error");
  error.classList.add("hidden");
  try {
    state.auth = await api("/auth/login", { method: "POST" });
    renderAuth();
    state.authTimer = setTimeout(pollAuth, 300);
  } catch (authError) {
    error.textContent = authError.message;
    error.classList.remove("hidden");
  }
}

async function loginServicePrincipal(event) {
  event.preventDefault();
  const error = byId("auth-error");
  const secretInput = byId("sp-client-secret");
  error.classList.add("hidden");
  byId("sp-login").disabled = true;
  try {
    state.auth = await api("/auth/service-principal", {
      method: "POST",
      body: {
        tenantId: byId("sp-tenant-id").value.trim(),
        clientId: byId("sp-client-id").value.trim(),
        clientSecret: secretInput.value
      }
    });
    renderAuth();
    if (byId("scan-tenant").value) await loadScanInventory();
  } catch (authError) {
    error.textContent = authError.message;
    error.classList.remove("hidden");
  } finally {
    secretInput.value = "";
    byId("sp-login").disabled = false;
  }
}

async function logout() {
  const error = byId("auth-error");
  error.classList.add("hidden");
  try {
    state.auth = await api("/auth/current", { method: "DELETE" });
    state.scanInventory = null;
    state.scanInventoryTenant = null;
    renderAuth();
    renderScanInventory();
  } catch (authError) {
    error.textContent = authError.message;
    error.classList.remove("hidden");
  }
}

async function pollScan() {
  clearTimeout(state.scanTimer);
  try {
    state.scan = await api("/scans/current");
    renderScan();
    if (["queued", "running", "importing"].includes(state.scan.status)) {
      state.scanTimer = setTimeout(pollScan, 1000);
    } else if (state.scanWasActive && state.scan.status === "completed") {
      state.scanWasActive = false;
      await refreshSnapshotData();
    }
  } catch (error) {
    byId("scan-form-error").textContent = error.message;
    byId("scan-form-error").classList.remove("hidden");
  }
}

async function startScan(event) {
  event.preventDefault();
  const error = byId("scan-form-error");
  error.classList.add("hidden");
  const workspaceIds = selectedWorkspaceIds();
  if (!workspaceIds.length) {
    error.textContent = t("Vælg mindst ét workspace");
    error.classList.remove("hidden");
    return;
  }
  try {
    state.scan = await api("/scans", {
      method: "POST",
      body: {
        tenantId: byId("scan-tenant").value.trim(),
        workspaceLimit: 0,
        workspaceIds,
        includePersonalWorkspaces: byId("scan-personal").checked,
        includePowerBIArtifactUsers: byId("scan-artifacts").checked
      }
    });
    state.scanWasActive = true;
    renderScan();
    state.scanTimer = setTimeout(pollScan, 300);
  } catch (scanError) {
    error.textContent = scanError.message;
    error.classList.remove("hidden");
  }
}

async function refreshSnapshotData() {
  [state.summary, state.facets, state.coverage] = await Promise.all([api("/summary"), api("/facets"), api("/coverage")]);
  byId("snapshot-date").textContent = formatDate(state.summary.generatedAtUtc, true);
  renderOverview(); renderFilters(); renderCoverage();
  await Promise.all([loadPermissions(true), loadWorkspaces(true)]);
}

function exportPage() {
  const columns = ["principalName", "principalEmail", "workspaceName", "artifactName", "artifactType", "access", "artifactState"];
  const csv = [columns.join(","), ...state.permissions.items.map((row) => columns.map((key) => `"${String(row[key] || "").replaceAll('"', '""')}"`).join(","))].join("\r\n");
  const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" })); link.download = `fabric-item-permissions-page-${state.permissions.page}.csv`; link.click(); URL.revokeObjectURL(link.href);
}

function switchView(view) {
  const titles = { overview: "Adgangsoverblik", permissions: "Rettigheder", workspaces: "Workspaces", mappings: "Brugermapping for migration", coverage: "API-dækning", auth: "Authentication", scan: "Start discovery-scan" };
  state.activeView = view;
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
  document.querySelectorAll(".view").forEach((item) => item.classList.toggle("active-view", item.id === `${view}-view`));
  byId("page-title").textContent = t(titles[view]);
  document.querySelector(".sidebar").classList.remove("open");
}

function debounce(callback, delay = 250) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => callback(...args), delay); };
}

function bindEvents() {
  byId("language-select").addEventListener("change", (event) => setLanguage(event.target.value));
  document.querySelectorAll(".nav-item").forEach((button) => button.addEventListener("click", () => switchView(button.dataset.view)));
  document.querySelectorAll("[data-go]").forEach((button) => button.addEventListener("click", () => switchView(button.dataset.go)));
  byId("permission-search").addEventListener("input", debounce(() => loadPermissions(true)));
  ["workspace-filter", "type-filter", "access-filter"].forEach((id) => byId(id).addEventListener("change", () => loadPermissions(true)));
  byId("workspace-search").addEventListener("input", debounce(() => loadWorkspaces(true)));
  byId("export-csv").addEventListener("click", exportPage);
  byId("dialog-close").addEventListener("click", () => byId("workspace-dialog").close());
  byId("menu-toggle").addEventListener("click", () => document.querySelector(".sidebar").classList.toggle("open"));
  byId("theme-toggle").addEventListener("click", () => document.documentElement.setAttribute("data-theme", document.documentElement.dataset.theme === "dark" ? "light" : "dark"));
  byId("auth-login").addEventListener("click", startLogin);
  byId("auth-logout").addEventListener("click", logout);
  byId("service-principal-form").addEventListener("submit", loginServicePrincipal);
  byId("api-token-save").addEventListener("click", saveApiToken);
  byId("api-token").addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    saveApiToken();
  });
  byId("scan-tenant").addEventListener("change", loadScanInventory);
  byId("scan-artifacts").addEventListener("change", renderScanEstimate);
  byId("scan-personal").addEventListener("change", loadScanInventory);
  byId("scan-workspace-tree").addEventListener("click", (event) => {
    if (event.target.matches("input[data-capacity-id]")) event.stopPropagation();
  });
  byId("scan-workspace-tree").addEventListener("change", (event) => {
    const input = event.target;
    if (input.matches("input[data-capacity-id]")) {
      document.querySelectorAll(`#scan-workspace-tree input[data-parent-capacity="${input.dataset.capacityId}"]`).forEach((child) => { child.checked = input.checked; });
    }
    if (input.matches("input[data-capacity-id], input[data-workspace-id]")) updateCapacityCheckboxes();
  });
  byId("scan-form").addEventListener("submit", startScan);
  byId("mapping-tenant").addEventListener("change", () => { invalidateMigrationPlan(); loadUserMappings(); });
  byId("mapping-sync").addEventListener("click", syncDirectoryUsers);
  byId("migration-plan-load").addEventListener("click", loadPermissionMigrationPlan);
  document.querySelectorAll("[data-migration-detail]").forEach((button) => button.addEventListener("click", () => {
    state.migrationPlanDetail = button.dataset.migrationDetail;
    renderPermissionMigration();
    byId("migration-detail-list").scrollIntoView({ behavior: "smooth", block: "nearest" });
  }));
  byId("migration-confirm").addEventListener("change", renderPermissionMigration);
  byId("migration-start").addEventListener("click", startPermissionMigration);
  byId("migration-cancel").addEventListener("click", cancelPermissionMigration);
  document.querySelectorAll("[data-layout]").forEach((button) => button.addEventListener("click", () => {
    document.querySelectorAll("[data-layout]").forEach((item) => item.classList.toggle("active", item === button));
    byId("workspace-grid").classList.toggle("list-layout", button.dataset.layout === "list");
  }));
}

async function init() {
  try {
    byId("language-select").value = state.locale;
    applyStaticTranslations();
    [state.summary, state.facets, state.coverage] = await Promise.all([api("/summary"), api("/facets"), api("/coverage")]);
    byId("snapshot-date").textContent = formatDate(state.summary.generatedAtUtc, true);
    renderOverview(); renderFilters(); renderCoverage(); bindEvents();
    await Promise.all([loadPermissions(), loadWorkspaces(), pollAuth(), pollScan(), pollPermissionMigration()]);
    byId("loading").classList.add("hidden"); byId("app-content").classList.remove("hidden");
  } catch (error) {
    byId("loading").classList.add("hidden"); byId("error-state").classList.remove("hidden"); byId("error-message").textContent = error.message;
  }
}

init();