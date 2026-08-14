(function () {
  "use strict";

  function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatDate(value) {
    if (!value) return "";
    return value.replace("T", " ").replace("Z", "");
  }

  async function api(method, url, body) {
    const response = await fetch(url, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });

    let payload = null;
    const text = await response.text();
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch (err) {
        payload = null;
      }
    }

    return { ok: response.ok, status: response.status, data: payload };
  }

  function showError(el, message) {
    if (!el) return;
    el.textContent = message;
    el.hidden = !message;
  }

  // ---------- Result / diff rendering (shared) ----------

  function diffTable(diffs) {
    if (!diffs || diffs.length === 0) {
      return "<p class=\"muted\">No diffs.</p>";
    }

    const rows = diffs
      .map(
        (diff) => `
        <tr>
          <td>${escapeHtml(diff.kind)}</td>
          <td><span class="badge ${diff.severity === "notice" ? "notice" : "drift"}">${escapeHtml(diff.severity || "drift")}</span></td>
          <td>${escapeHtml(diff.field)}</td>
          <td>${escapeHtml(diff.expected)}</td>
          <td>${escapeHtml(diff.actual)}</td>
          <td>${escapeHtml(diff.message)}</td>
        </tr>`
      )
      .join("");

    return `
      <table>
        <thead>
          <tr><th>Kind</th><th>Severity</th><th>Field</th><th>Expected</th><th>Actual</th><th>Message</th></tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  // A passing run can still carry notice-level diffs (lenient contracts
  // record extra fields as notices). Show those runs as "notice" so they
  // stand apart from a clean pass, without treating them as failures.
  function displayState(run) {
    if (run.result !== "pass") return run.result;
    const noticeCount =
      run.notice_count !== undefined
        ? run.notice_count
        : (run.diffs || []).filter((diff) => diff.severity === "notice").length;
    return noticeCount > 0 ? "notice" : "pass";
  }

  function resultTitle(state) {
    if (state === "pass") return "PASS";
    if (state === "notice") return "PASS (WITH NOTICES)";
    if (state === "drift") return "DRIFT DETECTED";
    return "ERROR";
  }

  function renderRunPanel(run) {
    const state = displayState(run);
    const container = document.createElement("div");
    container.className = `result-panel ${state}`;

    let body = `<div class="result-title">${resultTitle(state)}</div>`;
    body += `<p class="muted">Run #${run.id} · ${formatDate(run.created_at)} · status ${run.status_code ?? "—"} · ${run.duration_ms ?? "—"} ms</p>`;

    if (run.result === "error") {
      body += `<p>${escapeHtml(run.error_message)}</p>`;
    } else {
      body += diffTable(run.diffs);
    }

    if (!run.acknowledged) {
      body += `<button type="button" class="btn btn-secondary acknowledge-btn" data-run-id="${run.id}">Acknowledge</button>`;
    } else {
      body += `<span class="badge acknowledged">Acknowledged</span>`;
    }

    container.innerHTML = body;

    const ackBtn = container.querySelector(".acknowledge-btn");
    if (ackBtn) {
      ackBtn.addEventListener("click", async () => {
        ackBtn.disabled = true;
        const { ok, data } = await api("POST", `/api/runs/${run.id}/acknowledge`);
        if (ok) {
          renderInto(container.parentElement, data.run);
        } else {
          ackBtn.disabled = false;
        }
      });
    }

    return container;
  }

  function renderInto(mountEl, run) {
    mountEl.innerHTML = "";
    mountEl.appendChild(renderRunPanel(run));
  }

  // ---------- Dashboard ----------

  function initDashboard() {
    const list = document.getElementById("projects-list");
    const form = document.getElementById("create-project-form");
    const errorEl = document.getElementById("create-project-error");

    async function loadProjects() {
      const { ok, data } = await api("GET", "/api/projects");
      if (!ok) {
        list.innerHTML = '<p class="form-error">Could not load projects.</p>';
        return;
      }

      if (data.projects.length === 0) {
        list.innerHTML = '<p class="muted">No projects yet. Create one above.</p>';
        return;
      }

      list.innerHTML = data.projects
        .map(
          (project) => `
          <div class="list-item">
            <div>
              <a href="/projects/${project.id}">${escapeHtml(project.name)}</a>
              <div class="muted">${escapeHtml(project.base_url)}</div>
            </div>
          </div>`
        )
        .join("");
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      showError(errorEl, "");

      const formData = new FormData(form);
      const payload = {
        name: formData.get("name"),
        base_url: formData.get("base_url"),
        description: formData.get("description"),
      };

      const { ok, data } = await api("POST", "/api/projects", payload);
      if (!ok) {
        showError(errorEl, (data && data.error) || "Could not create project.");
        return;
      }

      form.reset();
      loadProjects();
    });

    loadProjects();
  }

  // ---------- Project detail ----------

  function initProjectPage() {
    const root = document.getElementById("project-page");
    const projectId = root.dataset.projectId;
    const list = document.getElementById("endpoints-list");
    const form = document.getElementById("create-endpoint-form");
    const errorEl = document.getElementById("create-endpoint-error");

    async function loadEndpoints() {
      const { ok, data } = await api("GET", `/api/projects/${projectId}/endpoints`);
      if (!ok) {
        list.innerHTML = '<p class="form-error">Could not load endpoints.</p>';
        return;
      }

      if (data.endpoints.length === 0) {
        list.innerHTML = '<p class="muted">No endpoints yet. Add one above.</p>';
        return;
      }

      list.innerHTML = data.endpoints
        .map(
          (endpoint) => `
          <div class="list-item">
            <div>
              <a href="/endpoints/${endpoint.id}">
                <span class="method-badge">${escapeHtml(endpoint.method)}</span>${escapeHtml(endpoint.path)}
              </a>
              ${endpoint.description ? `<div class="muted">${escapeHtml(endpoint.description)}</div>` : ""}
            </div>
          </div>`
        )
        .join("");
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      showError(errorEl, "");

      const formData = new FormData(form);
      const payload = {
        method: formData.get("method"),
        path: formData.get("path"),
        description: formData.get("description"),
      };

      const { ok, data } = await api("POST", `/api/projects/${projectId}/endpoints`, payload);
      if (!ok) {
        showError(errorEl, (data && data.error) || "Could not create endpoint.");
        return;
      }

      form.reset();
      loadEndpoints();
    });

    loadEndpoints();
  }

  // ---------- Endpoint detail: contract builder + run ----------

  const FIELD_TYPES = ["string", "integer", "number", "boolean", "array", "object"];

  function typeOptions(selected) {
    return FIELD_TYPES.map(
      (type) => `<option value="${type}" ${type === selected ? "selected" : ""}>${type}</option>`
    ).join("");
  }

  function createFieldRow() {
    const row = document.createElement("div");
    row.className = "field-row-item";
    row.innerHTML = `
      <input type="text" class="field-name" placeholder="field name" required>
      <select class="field-type">${typeOptions("string")}</select>
      <select class="item-type" hidden>${typeOptions("string")}</select>
      <label><input type="checkbox" class="field-required" checked> required</label>
      <button type="button" class="btn btn-secondary add-nested-btn" hidden>+ nested field</button>
      <button type="button" class="btn btn-danger remove-field-btn">Remove</button>
      <div class="field-rows-nested" hidden></div>
    `;

    const typeSelect = row.querySelector(".field-type");
    const itemTypeSelect = row.querySelector(".item-type");
    const nestedContainer = row.querySelector(".field-rows-nested");
    const addNestedBtn = row.querySelector(".add-nested-btn");
    const removeBtn = row.querySelector(".remove-field-btn");

    function syncVisibility() {
      const type = typeSelect.value;
      itemTypeSelect.hidden = type !== "array";

      const showsNested =
        type === "object" || (type === "array" && itemTypeSelect.value === "object");
      nestedContainer.hidden = !showsNested;
      addNestedBtn.hidden = !showsNested;
    }

    typeSelect.addEventListener("change", syncVisibility);
    itemTypeSelect.addEventListener("change", syncVisibility);
    removeBtn.addEventListener("click", () => row.remove());
    addNestedBtn.addEventListener("click", () => {
      nestedContainer.appendChild(createFieldRow());
    });

    syncVisibility();
    return row;
  }

  function serializeFields(container) {
    const fields = {};
    container.querySelectorAll(":scope > .field-row-item").forEach((row) => {
      const name = row.querySelector(".field-name").value.trim();
      if (!name) return;

      const type = row.querySelector(".field-type").value;
      const required = row.querySelector(".field-required").checked;
      const def = { type, required };

      if (type === "object") {
        def.fields = serializeFields(row.querySelector(".field-rows-nested"));
      }

      if (type === "array") {
        const itemType = row.querySelector(".item-type").value;
        def.items = { type: itemType };
        if (itemType === "object") {
          def.items.fields = serializeFields(row.querySelector(".field-rows-nested"));
        }
      }

      fields[name] = def;
    });

    return fields;
  }

  function initEndpointPage() {
    const root = document.getElementById("endpoint-page");
    const endpointId = root.dataset.endpointId;

    const fieldsRoot = document.getElementById("schema-fields-root");
    const addFieldBtn = document.getElementById("add-field-btn");
    const preview = document.getElementById("schema-preview");
    const expectedStatusInput = document.getElementById("expected-status");
    const strictnessSelect = document.getElementById("contract-strictness");
    const saveBtn = document.getElementById("save-contract-btn");
    const saveError = document.getElementById("save-contract-error");
    const contractsList = document.getElementById("contracts-list");
    const runBtn = document.getElementById("run-btn");
    const runStatus = document.getElementById("run-status");
    const runResult = document.getElementById("run-result");
    const recentRunsList = document.getElementById("recent-runs-list");

    let activeContractId = null;

    function updatePreview() {
      const schema = { fields: serializeFields(fieldsRoot) };
      preview.textContent = JSON.stringify(schema, null, 2);
      return schema;
    }

    fieldsRoot.addEventListener("input", updatePreview);
    fieldsRoot.addEventListener("change", updatePreview);
    addFieldBtn.addEventListener("click", () => {
      fieldsRoot.appendChild(createFieldRow());
      updatePreview();
    });

    saveBtn.addEventListener("click", async () => {
      showError(saveError, "");
      const schema = updatePreview();

      if (Object.keys(schema.fields).length === 0) {
        showError(saveError, "Add at least one field before saving.");
        return;
      }

      const payload = {
        schema_json: schema,
        expected_status: parseInt(expectedStatusInput.value, 10) || 200,
        strictness: strictnessSelect.value,
      };

      const { ok, data } = await api("POST", `/api/endpoints/${endpointId}/contracts`, payload);
      if (!ok) {
        showError(saveError, (data && data.error) || "Could not save contract.");
        return;
      }

      loadContracts();
    });

    async function loadContracts() {
      const { ok, data } = await api("GET", `/api/endpoints/${endpointId}/contracts`);
      if (!ok) {
        contractsList.innerHTML = '<p class="form-error">Could not load contracts.</p>';
        return;
      }

      if (data.contracts.length === 0) {
        contractsList.innerHTML = '<p class="muted">No contracts yet. Build one above.</p>';
        runBtn.disabled = true;
        activeContractId = null;
        return;
      }

      contractsList.innerHTML = data.contracts
        .map(
          (contract) => `
          <div class="list-item">
            <div>
              <strong>v${contract.version}</strong>
              ${contract.is_active ? '<span class="badge pass">active</span>' : ""}
              <div class="muted">expected status ${contract.expected_status} · ${escapeHtml(contract.strictness)} · ${formatDate(contract.created_at)}</div>
            </div>
          </div>`
        )
        .join("");

      const active = data.contracts.find((c) => c.is_active);
      activeContractId = active ? active.id : null;
      runBtn.disabled = !activeContractId;

      if (activeContractId) {
        loadRecentRuns(activeContractId);
      }
    }

    async function loadRecentRuns(contractId) {
      const { ok, data } = await api("GET", `/api/contracts/${contractId}/runs?per_page=5`);
      if (!ok) return;

      if (data.runs.length === 0) {
        recentRunsList.innerHTML = '<p class="muted">No runs yet.</p>';
        return;
      }

      recentRunsList.innerHTML = data.runs
        .map(
          (run) => `
          <div class="list-item">
            <a href="/runs/${run.id}">Run #${run.id} · ${formatDate(run.created_at)}</a>
            <span class="badge ${displayState(run)}">${displayState(run)}</span>
          </div>`
        )
        .join("");
    }

    runBtn.addEventListener("click", async () => {
      if (!activeContractId) return;
      runBtn.disabled = true;
      runStatus.textContent = "Running…";
      runResult.innerHTML = "";

      const { ok, data, status } = await api("POST", `/api/contracts/${activeContractId}/run`);
      runBtn.disabled = false;
      runStatus.textContent = "";

      if (!ok || status === 404) {
        runResult.innerHTML = `<p class="form-error">${escapeHtml((data && data.error) || "Run failed.")}</p>`;
        return;
      }

      renderInto(runResult, data.run);
      loadRecentRuns(activeContractId);
    });

    updatePreview();
    loadContracts();
  }

  // ---------- History ----------

  function initHistoryPage() {
    const list = document.getElementById("history-list");
    const filterSelect = document.getElementById("history-filter");
    const prevBtn = document.getElementById("history-prev");
    const nextBtn = document.getElementById("history-next");
    const pageLabel = document.getElementById("history-page-label");

    let page = 1;
    const perPage = 20;

    async function load() {
      const params = new URLSearchParams({ page, per_page: perPage });
      if (filterSelect.value) params.set("result", filterSelect.value);

      const { ok, data } = await api("GET", `/api/runs?${params.toString()}`);
      if (!ok) {
        list.innerHTML = '<p class="form-error">Could not load history.</p>';
        return;
      }

      if (data.runs.length === 0) {
        list.innerHTML = '<p class="muted">No runs found.</p>';
      } else {
        list.innerHTML = `
          <table>
            <thead>
              <tr><th>Project</th><th>Endpoint</th><th>Result</th><th>When</th><th></th></tr>
            </thead>
            <tbody>
              ${data.runs
                .map(
                  (run) => `
                <tr>
                  <td>${escapeHtml(run.project_name)}</td>
                  <td><span class="method-badge">${escapeHtml(run.endpoint_method)}</span>${escapeHtml(run.endpoint_path)}</td>
                  <td><span class="badge ${displayState(run)}">${displayState(run)}</span> ${run.acknowledged ? '<span class="badge acknowledged">ack</span>' : ""}</td>
                  <td>${formatDate(run.created_at)}</td>
                  <td><a href="/runs/${run.id}">View</a></td>
                </tr>`
                )
                .join("")}
            </tbody>
          </table>`;
      }

      const totalPages = Math.max(1, Math.ceil(data.total / perPage));
      pageLabel.textContent = `Page ${page} of ${totalPages}`;
      prevBtn.disabled = page <= 1;
      nextBtn.disabled = page >= totalPages;
    }

    filterSelect.addEventListener("change", () => {
      page = 1;
      load();
    });
    prevBtn.addEventListener("click", () => {
      if (page > 1) {
        page -= 1;
        load();
      }
    });
    nextBtn.addEventListener("click", () => {
      page += 1;
      load();
    });

    load();
  }

  // ---------- Run detail ----------

  function initRunDetailPage() {
    const root = document.getElementById("run-detail-page");
    const runId = root.dataset.runId;
    const content = document.getElementById("run-detail-content");

    async function load() {
      const { ok, data } = await api("GET", `/api/runs/${runId}`);
      if (!ok) {
        content.innerHTML = '<p class="form-error">Run not found.</p>';
        return;
      }

      content.innerHTML = "";
      content.appendChild(renderRunPanel(data.run));

      if (data.run.response_body !== null && data.run.response_body !== undefined) {
        const pre = document.createElement("pre");
        pre.className = "json-preview";
        pre.textContent =
          typeof data.run.response_body === "string"
            ? data.run.response_body
            : JSON.stringify(data.run.response_body, null, 2);
        const heading = document.createElement("h3");
        heading.textContent = "Response body";
        content.appendChild(heading);
        content.appendChild(pre);
      }
    }

    load();
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("dashboard-page")) initDashboard();
    if (document.getElementById("project-page")) initProjectPage();
    if (document.getElementById("endpoint-page")) initEndpointPage();
    if (document.getElementById("history-page")) initHistoryPage();
    if (document.getElementById("run-detail-page")) initRunDetailPage();
  });
})();
