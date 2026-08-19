const API_ROOT = "/api";
const state = {
  summary: null,
  coverage: null,
  facets: null,
  permissions: { items: [], page: 1, pageSize: 50, total: 0, totalPages: 1 },
  workspaces: { items: [], page: 1, pageSize: 24, total: 0, totalPages: 1 },
  permissionRequest: null,
  workspaceRequest: null,
  scan: null,
  scanTimer: null,
  scanWasActive: false
};

const byId = (id) => document.getElementById(id);
const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
})[char]);

async function api(path, options = {}) {
  const response = await fetch(`${API_ROOT}${path}`, {
    method: options.method || "GET",
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
    body: options.body ? JSON.stringify(options.body) : undefined,
    signal: options.signal
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `${path}: HTTP ${response.status}`);
  }
  return response.json();
}

function formatDate(value, withTime = false) {
  if (!value) return "Ukendt";
  return new Intl.DateTimeFormat("da-DK", withTime ? { dateStyle: "medium", timeStyle: "short" } : { dateStyle: "medium" }).format(new Date(value));
}

function renderOverview() {
  const { counts, principalCounts, typeCounts, recentItems } = state.summary;
  byId("metric-workspaces").textContent = counts.workspaces.toLocaleString("da-DK");
  byId("metric-artifacts").textContent = counts.artifacts.toLocaleString("da-DK");
  byId("metric-principals").textContent = counts.principals.toLocaleString("da-DK");
  byId("metric-assignments").textContent = counts.assignments.toLocaleString("da-DK");
  byId("metric-types").textContent = `${counts.artifactTypes} item-typer`;

  const maxCount = principalCounts[0]?.count || 1;
  byId("principal-bars").innerHTML = principalCounts.map((principal) => `
    <div class="bar-row"><div class="bar-person"><strong>${escapeHtml(principal.principalName)}</strong><small>${escapeHtml(principal.principalEmail)}</small></div>
    <div class="bar-track"><div class="bar-fill" style="width:${(principal.count / maxCount) * 100}%"></div></div><div class="bar-count">${principal.count.toLocaleString("da-DK")}</div></div>
  `).join("") || '<div class="empty-state">Ingen item-rettigheder fundet.</div>';

  byId("type-list").innerHTML = typeCounts.map((item) => `
    <div class="type-row"><span class="type-glyph">${escapeHtml(item.type.slice(0, 2).toUpperCase())}</span><strong>${escapeHtml(item.type)}</strong><span>${item.count.toLocaleString("da-DK")}</span></div>
  `).join("");
  byId("recent-items").innerHTML = recentItems.map((item) => `
    <div class="recent-item"><strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(item.type)} · ${escapeHtml(item.workspaceName)}</span><span>${formatDate(item.modified, true)}</span></div>
  `).join("") || '<div class="empty-state">Ingen datooplysninger fundet.</div>';
}

function fillSelect(id, values, label, getValue = (value) => value, getLabel = (value) => value) {
  byId(id).innerHTML = `<option value="">${label}</option>` + values.map((value) => `<option value="${escapeHtml(getValue(value))}">${escapeHtml(getLabel(value))}</option>`).join("");
}

function renderFilters() {
  fillSelect("workspace-filter", state.facets.workspaces, "Alle workspaces", (item) => item.id, (item) => item.name);
  fillSelect("type-filter", state.facets.artifactTypes, "Alle item-typer");
  fillSelect("access-filter", state.facets.accessRights, "Alle adgangstyper");
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
  byId("permission-count").textContent = state.permissions.total.toLocaleString("da-DK");
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
  byId(id).innerHTML = `<button data-page="${result.page - 1}" ${result.page === 1 ? "disabled" : ""}>←</button><span>Side ${result.page.toLocaleString("da-DK")} af ${result.totalPages.toLocaleString("da-DK")}</span><button data-page="${result.page + 1}" ${result.page === result.totalPages ? "disabled" : ""}>→</button>`;
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
    <div class="workspace-card-stats"><div><span>Items</span><strong>${workspace.artifacts.toLocaleString("da-DK")}</strong></div><div><span>Principals</span><strong>${workspace.principals.toLocaleString("da-DK")}</strong></div><div><span>Roller</span><strong>${workspace.roles.toLocaleString("da-DK")}</strong></div></div></button>
  `).join("");
  document.querySelectorAll("[data-workspace-id]").forEach((button) => button.addEventListener("click", () => openWorkspace(button.dataset.workspaceId)));
  renderPagination("workspaces-pagination", state.workspaces, (page) => { state.workspaces.page = page; loadWorkspaces(); });
}

async function openWorkspace(workspaceId) {
  const detail = await api(`/workspaces/${encodeURIComponent(workspaceId)}`);
  byId("dialog-title").textContent = detail.workspace.name;
  byId("dialog-content").innerHTML = `
    <div class="dialog-stats"><div class="dialog-stat"><span>FABRIC-ITEMS</span><strong>${detail.counts.artifacts.toLocaleString("da-DK")}</strong></div><div class="dialog-stat"><span>ITEM-PRINCIPALS</span><strong>${detail.counts.itemPrincipals.toLocaleString("da-DK")}</strong></div><div class="dialog-stat"><span>WORKSPACE-ROLLER</span><strong>${detail.counts.roles.toLocaleString("da-DK")}</strong></div></div>
    <section class="dialog-section"><h3>Workspace-adgang</h3><div class="dialog-list">${detail.roles.map((role) => `<div class="dialog-row"><div><strong>${escapeHtml(role.displayName)}</strong><span>${escapeHtml(role.email || role.principalType)}</span></div><span class="badge access-badge">${escapeHtml(role.role)}</span></div>`).join("") || '<p class="empty-state">Ingen direkte roller</p>'}</div></section>
    <section class="dialog-section"><h3>Item-fordeling</h3><div class="dialog-list">${detail.artifactTypes.map((item) => `<div class="dialog-row"><div><strong>${escapeHtml(item.type)}</strong><span>Artifact-kategori</span></div><span class="badge">${item.count.toLocaleString("da-DK")}</span></div>`).join("") || '<p class="empty-state">Ingen items i scanner-resultatet</p>'}</div></section>`;
  byId("workspace-dialog").showModal();
}

function renderCoverage() {
  byId("coverage-score").textContent = state.coverage.covered.length;
  byId("covered-list").innerHTML = state.coverage.covered.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  byId("not-covered-list").innerHTML = state.coverage.notCovered.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  byId("api-notes-list").innerHTML = state.coverage.apiNotes.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderScan() {
  const scan = state.scan || { status: "idle", progress: 0, stage: "Klar til scanning", logs: [] };
  const active = ["queued", "running", "importing"].includes(scan.status);
  const labels = { idle: "Klar", queued: "I kø", running: "Kører", importing: "Importerer", completed: "Fuldført", failed: "Fejlet" };
  byId("scan-availability").textContent = labels[scan.status] || scan.status;
  byId("scan-availability").dataset.status = scan.status;
  byId("scan-stage").textContent = scan.stage;
  byId("scan-percent").textContent = `${scan.progress}%`;
  byId("scan-progress").style.width = `${scan.progress}%`;
  byId("scan-progress").parentElement.setAttribute("aria-valuenow", scan.progress);
  byId("scan-started").textContent = scan.startedAtUtc ? `Startet ${formatDate(scan.startedAtUtc, true)}` : "Ikke startet";
  byId("scan-completed").textContent = scan.completedAtUtc ? `Afsluttet ${formatDate(scan.completedAtUtc, true)}` : "";
  byId("scan-log").textContent = scan.logs?.length ? scan.logs.join("\n") : "Ingen aktivitet endnu.";
  byId("scan-start").disabled = active;
  byId("scan-start").textContent = active ? "Scan kører..." : "Start scan";
  byId("scan-result").classList.toggle("hidden", !scan.result);
  byId("scan-result").innerHTML = scan.result ? Object.entries(scan.result).map(([key, value]) => `<div><strong>${Number(value).toLocaleString("da-DK")}</strong><span>${escapeHtml(key)}</span></div>`).join("") : "";
  byId("scan-log").scrollTop = byId("scan-log").scrollHeight;
  state.scanWasActive ||= active;
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
  try {
    state.scan = await api("/scans", {
      method: "POST",
      body: {
        tenantId: byId("scan-tenant").value.trim(),
        workspaceLimit: Number(byId("scan-limit").value),
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
  const titles = { overview: "Adgangsoverblik", permissions: "Rettigheder", workspaces: "Workspaces", coverage: "API-dækning", scan: "Start discovery-scan" };
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
  document.querySelectorAll(".view").forEach((item) => item.classList.toggle("active-view", item.id === `${view}-view`));
  byId("page-title").textContent = titles[view];
  document.querySelector(".sidebar").classList.remove("open");
}

function debounce(callback, delay = 250) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => callback(...args), delay); };
}

function bindEvents() {
  document.querySelectorAll(".nav-item").forEach((button) => button.addEventListener("click", () => switchView(button.dataset.view)));
  document.querySelectorAll("[data-go]").forEach((button) => button.addEventListener("click", () => switchView(button.dataset.go)));
  byId("permission-search").addEventListener("input", debounce(() => loadPermissions(true)));
  ["workspace-filter", "type-filter", "access-filter"].forEach((id) => byId(id).addEventListener("change", () => loadPermissions(true)));
  byId("workspace-search").addEventListener("input", debounce(() => loadWorkspaces(true)));
  byId("export-csv").addEventListener("click", exportPage);
  byId("dialog-close").addEventListener("click", () => byId("workspace-dialog").close());
  byId("menu-toggle").addEventListener("click", () => document.querySelector(".sidebar").classList.toggle("open"));
  byId("theme-toggle").addEventListener("click", () => document.documentElement.setAttribute("data-theme", document.documentElement.dataset.theme === "dark" ? "light" : "dark"));
  byId("scan-form").addEventListener("submit", startScan);
  document.querySelectorAll("[data-layout]").forEach((button) => button.addEventListener("click", () => {
    document.querySelectorAll("[data-layout]").forEach((item) => item.classList.toggle("active", item === button));
    byId("workspace-grid").classList.toggle("list-layout", button.dataset.layout === "list");
  }));
}

async function init() {
  try {
    [state.summary, state.facets, state.coverage] = await Promise.all([api("/summary"), api("/facets"), api("/coverage")]);
    byId("snapshot-date").textContent = formatDate(state.summary.generatedAtUtc, true);
    renderOverview(); renderFilters(); renderCoverage(); bindEvents();
    await Promise.all([loadPermissions(), loadWorkspaces(), pollScan()]);
    byId("loading").classList.add("hidden"); byId("app-content").classList.remove("hidden");
  } catch (error) {
    byId("loading").classList.add("hidden"); byId("error-state").classList.remove("hidden"); byId("error-message").textContent = error.message;
  }
}

init();