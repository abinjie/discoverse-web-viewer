const state = {
  catalog: null,
  robot: "airbot_play",
  compat: null,
};

const els = {
  robotGroup: document.getElementById("robot_group"),
  taskSelect: document.getElementById("task_select"),
  taskRuntime: document.getElementById("task_runtime"),
  gsFieldset: document.getElementById("gs_fieldset"),
  gsSceneGroup: document.getElementById("gs_scene_group"),
  gsAssetsGroup: document.getElementById("gs_assets_group"),
  gsZ: document.getElementById("gs_z"),
  btnStart: document.getElementById("btn_start"),
  btnStopAll: document.getElementById("btn_stop_all"),
  formMessage: document.getElementById("form_message"),
  sessionsList: document.getElementById("sessions_list"),
  optRandomize: document.getElementById("opt_randomize"),
  optSync: document.getElementById("opt_sync"),
};

function renderMode() {
  const checked = document.querySelector('input[name="render_mode"]:checked');
  return checked ? checked.value : "mesh";
}

function setMessage(text, kind = "") {
  els.formMessage.textContent = text || "";
  els.formMessage.className = `message ${kind}`.trim();
}

async function fetchJson(url, options) {
  const resp = await fetch(url, options);
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(data.detail || data.error || resp.statusText);
  }
  return data;
}

function renderRobots(robots) {
  els.robotGroup.innerHTML = "";
  for (const robot of robots) {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "radio";
    input.name = "robot";
    input.value = robot.id;
    input.checked = robot.id === state.robot;
    input.addEventListener("change", () => {
      if (input.checked) {
        state.robot = robot.id;
        refreshCompatibility();
      }
    });
    label.append(input, document.createTextNode(` ${robot.label}`));
    els.robotGroup.append(label);
  }
}

function renderTasks(tasks) {
  els.taskSelect.innerHTML = "";
  for (const task of tasks) {
    const opt = document.createElement("option");
    opt.value = task.id;
    opt.textContent = `${task.label} (${task.id})`;
    els.taskSelect.append(opt);
  }
  els.taskSelect.addEventListener("change", refreshCompatibility);
}

function renderGsAssets(gsAssets) {
  const scenes = gsAssets.filter((a) => a.group === "scene" && a.available);
  els.gsSceneGroup.innerHTML = "";
  if (scenes.length) {
    const label = document.createElement("label");
    label.textContent = "背景场景";
    const select = document.createElement("select");
    select.id = "gs_scene_select";
    for (const scene of scenes) {
      const opt = document.createElement("option");
      opt.value = scene.id;
      opt.textContent = scene.label;
      select.append(opt);
    }
    els.gsSceneGroup.append(label, select);
  }

  els.gsAssetsGroup.innerHTML = "";
  for (const asset of gsAssets) {
    if (asset.group === "scene" || !asset.available) continue;
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = asset.id;
    input.dataset.gsAsset = "1";
    label.append(input, document.createTextNode(` ${asset.label}`));
    els.gsAssetsGroup.append(label);
  }
}

function applyGsHints(hints) {
  for (const input of els.gsAssetsGroup.querySelectorAll('input[data-gs-asset="1"]')) {
    input.checked = hints.includes(input.value);
  }
}

function updateRuntimeHint() {
  const task = state.catalog.tasks.find((t) => t.id === els.taskSelect.value);
  if (!task) {
    els.taskRuntime.textContent = "";
    return;
  }
  const cls = task.runtime === "static_preview" ? "warn" : "ok";
  els.taskRuntime.textContent = task.runtime_label;
  els.taskRuntime.className = `hint ${cls}`;
}

async function refreshCompatibility() {
  updateRuntimeHint();
  const task = els.taskSelect.value;
  try {
    state.compat = await fetchJson(
      `/api/catalog/compatibility?robot=${encodeURIComponent(state.robot)}&task=${encodeURIComponent(task)}`
    );
    if (state.compat.gs_hints?.length) {
      applyGsHints(state.compat.gs_hints);
    }
    els.btnStart.disabled = !state.compat.ok;
    if (!state.compat.ok) {
      setMessage(state.compat.error || "组合不可用", "error");
    } else {
      setMessage("");
    }
  } catch (err) {
    setMessage(err.message, "error");
    els.btnStart.disabled = true;
  }
}

function updateGsFieldset() {
  const gs = renderMode() === "gs";
  els.gsFieldset.disabled = !gs;
}

async function loadCatalog() {
  state.catalog = await fetchJson("/api/catalog");
  state.robot = state.catalog.defaults?.robot || "airbot_play";
  renderRobots(state.catalog.robots);
  renderTasks(state.catalog.tasks);
  renderGsAssets(state.catalog.gs_assets);
  els.taskSelect.value = state.catalog.defaults?.task || "stack_block";
  await refreshCompatibility();
}

async function startSession() {
  setMessage("正在启动 Viewer …");
  els.btnStart.disabled = true;
  const gsSceneSelect = document.getElementById("gs_scene_select");
  const gsAssets = [...els.gsAssetsGroup.querySelectorAll('input[data-gs-asset="1"]:checked')].map(
    (el) => el.value
  );
  const body = {
    robot: state.robot,
    task: els.taskSelect.value,
    enable_gs: renderMode() === "gs",
    gs_scene: gsSceneSelect ? gsSceneSelect.value : "lab3",
    gs_assets: gsAssets,
    gs_offset: [0, 0, Number(els.gsZ.value) || 0],
    randomize: els.optRandomize.checked,
    sync: els.optSync.checked,
  };
  try {
    const record = await fetchJson("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setMessage(`会话 ${record.session_id} 已启动`, "ok");
    window.open(record.viewer_url, "_blank", "noopener,noreferrer");
    await refreshSessions();
  } catch (err) {
    setMessage(err.message, "error");
  } finally {
    els.btnStart.disabled = !(state.compat && state.compat.ok);
  }
}

async function refreshSessions() {
  const data = await fetchJson("/api/sessions");
  const sessions = data.sessions || [];
  if (!sessions.length) {
    els.sessionsList.innerHTML = '<p class="empty">暂无活跃会话</p>';
    return;
  }
  els.sessionsList.innerHTML = "";
  for (const s of sessions) {
    const card = document.createElement("div");
    card.className = "session-card";
    card.innerHTML = `
      <div class="title">${s.config.robot} / ${s.config.task}</div>
      <div class="meta">${s.session_id} · :${s.port} · ${s.status} · ${s.config.enable_gs ? "GS" : "Mesh"}</div>
      <div class="card-actions">
        <a href="${s.viewer_url}" target="_blank" rel="noopener noreferrer">打开 Viewer</a>
        <button type="button" data-stop="${s.session_id}">停止</button>
      </div>`;
    els.sessionsList.append(card);
  }
  els.sessionsList.querySelectorAll("button[data-stop]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await fetchJson(`/api/sessions/${btn.dataset.stop}`, { method: "DELETE" });
      await refreshSessions();
    });
  });
}

document.querySelectorAll('input[name="render_mode"]').forEach((el) => {
  el.addEventListener("change", updateGsFieldset);
});

els.btnStart.addEventListener("click", startSession);
els.btnStopAll.addEventListener("click", async () => {
  await fetchJson("/api/sessions", { method: "DELETE" });
  await refreshSessions();
  setMessage("已停止全部会话", "ok");
});

updateGsFieldset();
loadCatalog().then(refreshSessions).catch((err) => setMessage(err.message, "error"));
setInterval(refreshSessions, 5000);
