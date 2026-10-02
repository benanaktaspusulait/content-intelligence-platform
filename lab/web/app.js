const state = { videos: [], selected: null, mode: "action", labSection: "performance", lab: null };
const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value ?? "").replace(/[&<>\"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;" })[char]);
const badge = (value) => String(value || "").replaceAll(/[^A-Z]/g, "");

async function init() {
  state.videos = await fetch("/api/videos").then((response) => response.json());
  const series = [...new Set(state.videos.map((video) => video.series))].sort();
  $("#series").innerHTML += series.map((name) => `<option>${esc(name)}</option>`).join("");
  for (const id of ["search", "classification", "series", "sort"]) $("#" + id).addEventListener("input", render);
  document.querySelectorAll("[data-mode]").forEach((button) => button.onclick = () => setMode(button.dataset.mode));
  document.querySelectorAll("[data-lab]").forEach((button) => button.onclick = () => setLabSection(button.dataset.lab));
  setMode("action"); summary();
}

function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll("[data-mode]").forEach((button) => button.classList.toggle("active", button.dataset.mode === mode));
  $(".toolbar").hidden = mode === "lab";
  $(".workspace").hidden = mode === "lab";
  $("#labWorkspace").hidden = mode !== "lab";
  if (mode === "lab") {
    $("#modeNote").textContent = "Prediction, evidence, and learning remain versioned and separate.";
    loadLab();
    return;
  }
  $("#modeNote").textContent = mode === "action" ? "Creative structure match, not a view prediction." : "Preserves each video's own creative engine; observed performance outranks assumptions.";
  $("#sort").options[0].textContent = mode === "action" ? "Action DNA" : "Rescue hook";
  $("#classification").innerHTML = mode === "action"
    ? '<option value="">All classifications</option><option>BAD</option><option>AVERAGE/FIXABLE</option><option>GOOD</option><option>WINNER CANDIDATE</option>'
    : '<option value="">All rescue classes</option><option value="A">A — Prime / as-is</option><option value="B">B — Small fix</option><option value="C">C — Rescueable</option><option value="D">D — Low-value test</option><option value="E">E — Hold</option>';
  $("#tableHead").innerHTML = mode === "action"
    ? "<th>Video</th><th>Class</th><th>DNA</th><th>Hook</th><th>Goal</th><th>Action</th><th>Esc.</th><th>Final</th><th>Observed</th>"
    : "<th>Video</th><th>Rescue</th><th>Creative engine</th><th>Hook</th><th>Ending</th><th>Publishing</th><th>Observed</th>";
  render();
}

async function loadLab() {
  state.lab = await fetch("/api/lab").then((response) => response.json());
  renderLab();
}

function setLabSection(section) {
  state.labSection = section;
  document.querySelectorAll("[data-lab]").forEach((button) => button.classList.toggle("active", button.dataset.lab === section));
  renderLab();
}

function table(headers, rows) {
  if (!rows.length) return '<p class="notice">No evidence recorded yet.</p>';
  return `<table><thead><tr>${headers.map((item) => `<th>${esc(item.label)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${headers.map((item) => `<td>${esc(item.value(row) ?? "—")}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}

function renderLab() {
  if (!state.lab) return;
  const counts = state.lab.counts;
  const metrics = `<div class="lab-metrics"><div><small>Imports</small><strong>${counts.imports}</strong></div><div><small>Observations</small><strong>${counts.normalised_observations}</strong></div><div><small>Unresolved</small><strong>${counts.unresolved}</strong></div><div><small>Conflicts</small><strong>${counts.conflicts}</strong></div><div><small>Locked forecasts</small><strong>${counts.locked_predictions}</strong></div><div><small>Experiments</small><strong>${counts.experiments}</strong></div></div>`;
  let content = "";
  if (state.labSection === "performance") content = `<div class="lab-card"><h3>Observed trajectories</h3>${table([
    { label: "Video", value: (r) => r.filename }, { label: "Platform", value: (r) => r.platform },
    { label: "Checkpoint", value: (r) => r.checkpoint_minutes + "m" }, { label: "Views", value: (r) => r.views },
    { label: "Peak velocity", value: (r) => r.peak_velocity == null ? null : Math.round(r.peak_velocity) + "/h" },
    { label: "Band", value: (r) => r.performance_band }, { label: "Trajectory", value: (r) => r.trajectory_label },
  ], state.lab.trajectories)}</div>`;
  if (state.labSection === "imports") content = `<div class="lab-card"><h3>Import performance evidence</h3><div class="import-form"><input id="importPath" placeholder="Absolute CSV, TSV, XLSX, or JSON path inside new14092026"><select id="importPlatform"><option value="">Auto-detect</option><option>instagram</option><option>facebook</option><option>tiktok</option><option>manual</option></select><button class="secondary" onclick="runImport(true)">Preview</button><button onclick="runImport(false)">Commit import</button></div><pre id="importResult" class="notice">Preview validates schema without writing.</pre>${table([
    { label: "Source", value: (r) => r.source_filename }, { label: "Platform", value: (r) => r.platform }, { label: "Rows", value: (r) => r.row_count },
    { label: "Imported", value: (r) => r.imported_at }, { label: "Quality", value: (r) => r.quality_report_json },
  ], state.lab.imports)}</div>`;
  if (state.labSection === "predictions") content = `<div class="lab-card"><h3>Immutable prediction ledger</h3>${table([
    { label: "Video", value: (r) => r.filename }, { label: "Platform", value: (r) => r.platform }, { label: "Mode", value: (r) => r.mode },
    { label: "Model", value: (r) => r.model_version }, { label: "n", value: (r) => r.comparable_sample_size },
    { label: "Confidence", value: (r) => r.confidence }, { label: "State", value: (r) => r.locked_at ? "LOCKED" : "DRAFT" },
  ], state.lab.predictions)}</div>`;
  if (state.labSection === "experiments") content = `<div class="lab-card"><h3>Experiment registry</h3>${table([
    { label: "Name", value: (r) => r.name }, { label: "Platform", value: (r) => r.platform }, { label: "Design", value: (r) => r.design },
    { label: "Hypothesis", value: (r) => r.hypothesis }, { label: "Metric", value: (r) => `${r.primary_metric} @ ${r.horizon_minutes}m` }, { label: "Status", value: (r) => r.status },
  ], state.lab.experiments)}</div>`;
  if (state.labSection === "learning") content = `<div class="lab-card"><h3>Champion / challenger registry</h3>${table([
    { label: "Version", value: (r) => r.version }, { label: "Platform", value: (r) => r.platform }, { label: "Status", value: (r) => r.status },
    { label: "Algorithm", value: (r) => r.algorithm }, { label: "Rows", value: (r) => r.row_count }, { label: "Data as of", value: (r) => r.as_of },
  ], state.lab.models)}<p class="notice">Imports never auto-promote or retrain a model. Challenger creation and promotion are explicit.</p></div>`;
  if (state.labSection === "characters") content = `<div class="lab-card"><h3>Character coverage</h3>${table([
    { label: "Character", value: (r) => r.name }, { label: "Status", value: (r) => r.status }, { label: "Videos", value: (r) => r.video_count },
    { label: "Platforms", value: (r) => r.platforms }, { label: "Last measured", value: (r) => r.last_measured },
  ], state.lab.characters)}<p class="notice">Coverage is not popularity. Untested characters are unknown opportunities and remain in the exploration budget.</p></div>`;
  $("#labContent").innerHTML = metrics + content;
}

async function runImport(preview) {
  const result = $("#importResult");
  result.textContent = "Inspecting source…";
  const response = await fetch("/api/import-performance", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path: $("#importPath").value, platform: $("#importPlatform").value || null, timezone: "Europe/London", preview }) });
  const payload = await response.json();
  result.textContent = JSON.stringify(payload, null, 2);
  if (!preview && response.ok) await loadLab();
}

function summary() {
  const scores = state.videos.map((video) => +video.action_dna).sort((a, b) => a - b);
  $("#total").textContent = state.videos.length;
  $("#reviewCount").textContent = state.videos.filter((video) => !video.confirmed_classification && !video.override_classification).length;
  $("#fixCount").textContent = state.videos.filter((video) => video.classification === "AVERAGE/FIXABLE" || ["B", "C"].includes(video.rescue_classification)).length;
  $("#median").textContent = scores.length ? scores[Math.floor(scores.length / 2)].toFixed(0) : 0;
}

function filtered() {
  const query = $("#search").value.toLowerCase(), classification = $("#classification").value;
  const series = $("#series").value, sort = $("#sort").value;
  let rows = state.videos.filter((video) => {
    const currentClass = state.mode === "action" ? video.classification : video.rescue_classification;
    return (!query || (video.filename + " " + video.series).toLowerCase().includes(query)) && (!classification || currentClass === classification) && (!series || video.series === series);
  });
  const rank = state.mode === "action" ? { "WINNER CANDIDATE": 5, GOOD: 4, "AVERAGE/FIXABLE": 3, BAD: 2 } : { A: 5, B: 4, C: 3, D: 2, E: 1 };
  rows.sort((a, b) => {
    const aClass = state.mode === "action" ? a.classification : a.rescue_classification;
    const bClass = state.mode === "action" ? b.classification : b.rescue_classification;
    if (sort === "filename") return a.filename.localeCompare(b.filename);
    if (sort === "classification") return (rank[bClass] || 0) - (rank[aClass] || 0);
    if (sort === "performance") return (b.actual_performance || 0) - (a.actual_performance || 0);
    if (sort === "review") return Number(!!a.confirmed_classification) - Number(!!b.confirmed_classification);
    return state.mode === "action" ? b.action_dna - a.action_dna : (b.rescue_hook || 0) - (a.rescue_hook || 0);
  });
  return rows;
}

function render() {
  const rows = filtered(); $("#empty").hidden = !!rows.length;
  $("#rows").innerHTML = rows.map((video) => state.mode === "action" ? actionRow(video) : rescueRow(video)).join("");
  document.querySelectorAll("tbody tr").forEach((row) => row.onclick = () => detail(row.dataset.id));
}

function nameCell(video) {
  return `<td class="video-name"><strong>${esc(video.filename)}</strong><span>${esc(video.series)} · ${video.duration.toFixed(1)}s · ${video.width}×${video.height}</span></td>`;
}

function actionRow(video) {
  const classification = video.override_classification || video.classification;
  return `<tr data-id="${video.id}" class="${state.selected === video.id ? "active" : ""}">${nameCell(video)}<td><span class="badge ${badge(classification)}">${esc(classification)}</span></td><td class="score">${(+video.action_dna).toFixed(0)}</td><td>${video.hook_score}</td><td>${video.goal_score}</td><td>${video.action_score}</td><td>${video.escalation_score}</td><td>${video.final_score}</td><td>${video.actual_performance ?? "—"}</td></tr>`;
}

function rescueRow(video) {
  const classification = video.rescue_override_classification || video.rescue_classification;
  let engine = "Not analysed";
  try { engine = JSON.parse(video.rescue_engine || "[]").join(", ") || engine; } catch (_) {}
  return `<tr data-id="${video.id}" class="${state.selected === video.id ? "active" : ""}">${nameCell(video)}<td><span class="badge ${badge(classification)}">${esc(classification || "—")}</span></td><td class="video-name"><strong>${esc(engine)}</strong></td><td>${video.rescue_hook ?? "—"}</td><td>${video.rescue_ending ?? "—"}</td><td>${esc(video.rescue_publishing_use || "—")}</td><td>${video.actual_performance ?? "—"}</td></tr>`;
}

async function detail(id) {
  state.selected = id; render();
  const data = await fetch("/api/video?id=" + encodeURIComponent(id)).then((response) => response.json());
  const analysis = data.analysis, duration = data.duration || 1, events = analysis.timeline || [];
  const performance = data.performance.length ? `<ul class="issues">${data.performance.map((item) => `<li><strong>${esc(item.platform)} · ${esc(item.published_at || "date unknown")}</strong>Views ${item.views ?? "—"} · Reach ${item.reach ?? "—"} · Follows ${item.follows ?? "—"}${item.is_approximate ? " · approximate" : ""}<span>${esc(item.source_note || "")}</span></li>`).join("")}</ul>` : "<p>No platform metrics imported. Creative scores remain separate.</p>";
  const rescue = data.rescue ? rescueDetail(data) : '<div class="detail-section rescue-band"><h3>Stock Creative Rescue</h3><p>Not analysed in Rescue mode yet.</p></div>';
  $("#detail").innerHTML = `<video controls playsinline src="/media?id=${id}"></video><div class="detail-head"><span class="badge ${badge(data.override_classification || data.classification)}">${esc(data.override_classification || data.classification)}</span><h2>${esc(data.filename)}</h2><p>${esc(data.series)} · Creative structure match ${data.action_dna}/100 · confidence ${Math.round(data.confidence * 100)}%</p></div>${rescue}<div class="detail-section"><h3>Action DNA diagnosis</h3><p>${esc(analysis.diagnosis)}</p></div><div class="detail-section"><h3>Scores</h3><div class="score-grid">${Object.entries(analysis.scores).map(([key, value]) => `<div><small>${esc(key.replaceAll("_", " "))}</small><strong>${value}</strong></div>`).join("")}</div></div><div class="detail-section"><h3>Evidence timeline</h3><div class="timeline">${events.map((event) => `<i class="event ${esc(event.kind)}" title="${esc(event.kind + ": " + event.detail)}" style="left:${100 * event.start / duration}%;width:${Math.max(.5, 100 * (event.end - event.start) / duration)}%"></i>`).join("")}</div><div class="legend"><span>Green action</span><span>Yellow dead time</span><span>Black frames</span><span>Blue cut</span></div></div><div class="detail-section"><h3>Storyboard</h3><img class="storyboard" src="/artifact?id=${id}&name=storyboard.jpg" alt="Timestamped storyboard"></div><div class="detail-section"><h3>Observed performance</h3>${performance}</div><div class="detail-section"><h3>Action DNA review</h3><textarea id="note" placeholder="Human evidence or correction">${esc(data.human_note || "")}</textarea><div class="review-row"><button class="primary" onclick="review('${id}','confirm')">Confirm</button><button onclick="review('${id}','GOOD')">Override: Good</button><button onclick="review('${id}','AVERAGE/FIXABLE')">Override: Fixable</button><button class="danger" onclick="review('${id}','wrong')">Mark wrong</button></div></div>`;
}

function rescueDetail(data) {
  const rescue = data.rescue, classification = data.rescue_override_classification || rescue.classification;
  const best = rescue.best_moments.map((item) => `<li><strong>${esc(item.kind)} · ${item.timestamp ?? "unverified"}s</strong>${esc(item.description)}</li>`).join("");
  const fixes = rescue.fix_first.length ? rescue.fix_first.map((item) => `<li><strong>${esc(item.variant)} · ${esc(item.operation)}</strong>${esc(item.reason)}${item.semantic_risk ? " <span>Human reveal check required.</span>" : ""}</li>`).join("") : "<li>Preserve the existing cut. No mandatory edit.</li>";
  return `<div class="detail-section rescue-band"><h3>Stock Creative Rescue</h3><span class="badge ${badge(classification)}">${esc(classification)} — ${esc(rescue.classification_label)}</span><p class="rescue-engine"><strong>${esc(rescue.creative_engine.join(", "))}</strong><br>${esc(rescue.core_viewer_question)}</p><div class="score-grid"><div><small>Current hook</small><strong>${rescue.hook_score}</strong></div><div><small>Ending</small><strong>${rescue.ending_score}</strong></div><div><small>Confidence</small><strong>${Math.round(rescue.confidence * 100)}%</strong></div></div><h3>Best available moments</h3><ul class="issues">${best}</ul><h3>Fix first</h3><ul class="issues">${fixes}</ul><p><strong>${esc(rescue.publishing_use)}</strong> · ${esc(rescue.classification_reason)}</p><div class="links"><a href="/rescue-artifact?id=${data.id}&name=rescue_report.md" target="_blank">Full Rescue report</a></div><textarea id="rescueNote" placeholder="Creative engine correction or Rescue note">${esc(data.rescue_human_note || "")}</textarea><div class="review-row"><button class="primary" onclick="rescueReview('${data.id}','confirm')">Confirm Rescue</button><button onclick="rescueReview('${data.id}','A')">Override: A</button><button onclick="rescueReview('${data.id}','B')">Override: B</button><button onclick="rescueReview('${data.id}','C')">Override: C</button><button class="danger" onclick="rescueReview('${data.id}','E')">Hold</button></div></div>`;
}

async function review(id, action) {
  const payload = { video_id: id, note: $("#note").value };
  if (action === "confirm") payload.confirmed_classification = state.videos.find((video) => video.id === id).classification;
  else if (action === "wrong") payload.analysis_wrong = true; else payload.override_classification = action;
  await fetch("/api/review", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  await refresh(id);
}

async function rescueReview(id, action) {
  const video = state.videos.find((item) => item.id === id);
  const payload = { video_id: id, note: $("#rescueNote").value };
  if (action === "confirm") payload.confirmed_classification = video.rescue_classification; else payload.override_classification = action;
  await fetch("/api/rescue-review", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  await refresh(id);
}

async function refresh(id) {
  state.videos = await fetch("/api/videos").then((response) => response.json()); summary(); render(); detail(id);
}

init();
