// Claumeet Control Center frontend. Vanilla JS. All untrusted text is rendered with textContent.
"use strict";
(() => {
  let CSRF = null;
  let lastStatus = null;
  const $ = (s) => document.querySelector(s);
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };
  const fmtTime = (ts) => new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

  async function api(path, opts = {}) {
    const o = { credentials: "same-origin", headers: {}, ...opts };
    if (o.body && !(o.body instanceof FormData)) { o.headers["Content-Type"] = "application/json"; o.body = JSON.stringify(o.body); }
    if (o.method && o.method !== "GET") o.headers["X-CSRF-Token"] = CSRF || "";
    const r = await fetch(path, o);
    if (r.status === 401) { showLogin(); throw new Error("auth"); }
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.detail || j.error || r.statusText);
    return j;
  }
  const post = (p, body) => api(p, { method: "POST", body: body || {} });
  function toast(msg, bad) { const h = $("#hint"); h.textContent = msg; h.classList.remove("hidden"); h.style.borderColor = bad ? "var(--danger)" : ""; }

  function showLogin() { $("#login").classList.remove("hidden"); $("#app").classList.add("hidden"); }
  function showApp() { $("#login").classList.add("hidden"); $("#app").classList.remove("hidden"); }

  async function boot() {
    const s = await fetch("/api/session", { credentials: "same-origin" }).then((r) => r.json());
    if (!s.authenticated) return showLogin();
    CSRF = s.csrf; showApp(); bindUI(); bindWizard(); connectWS(); refreshAll(); loadWizard();
    setInterval(refreshLive, 3000);
  }

  $("#login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try { await fetch("/api/login", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passphrase: $("#pass").value }) }).then((r) => { if (!r.ok) throw new Error("Sign-in failed"); });
      location.reload();
    } catch (err) { $("#login-err").textContent = err.message; }
  });

  // ---------- tabs ----------
  function bindUI() {
    document.querySelectorAll(".sidebar button").forEach((b) => b.addEventListener("click", () => {
      document.querySelectorAll(".sidebar button").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      document.querySelectorAll(".tab").forEach((t) => t.classList.add("hidden"));
      $("#tab-" + b.dataset.tab).classList.remove("hidden");
      const loaders = { memory: loadMemory, schedule: loadSchedules, provider: loadRegistry, security: loadSecurity, persona: loadPersona };
      if (loaders[b.dataset.tab]) loaders[b.dataset.tab]();
    }));
    document.querySelectorAll("[data-cmd]").forEach((b) => b.addEventListener("click", () => cmd(b.dataset.cmd)));
    $("#estop").addEventListener("click", estop);
    document.addEventListener("keydown", (e) => { if (e.ctrlKey && e.shiftKey && (e.key === "X" || e.key === "x")) { e.preventDefault(); estop(); } });
    $("#join-form").addEventListener("submit", async (e) => { e.preventDefault();
      try { const r = await post("/api/join", { url: $("#join-url").value }); toast(r.ok ? "Opening Claumeet's browser… click 'Ask to join' there." : "Not joined: " + (r.reason || ""), !r.ok); } catch (err) { toast(err.message, true); } });
    $("#consent-btn").addEventListener("click", async () => { const r = await post("/api/consent/grant"); toast(r.ok ? "Disclosure posted. Claumeet is listening." : "Not started: " + r.reason, !r.ok); });
    $("#ask-form").addEventListener("submit", async (e) => { e.preventDefault(); const t = $("#ask-text").value.trim(); if (!t) return;
      addOwnerReply("You", t); $("#ask-text").value = "";
      try { const r = await post("/api/owner/ask", { text: t }); addOwnerReply("Claumeet (private)", r.ok ? r.text : "Unavailable: " + r.reason); } catch (err) { addOwnerReply("Error", err.message); } });
    $("#say-form").addEventListener("submit", async (e) => { e.preventDefault(); const r = await cmd("speak", { text: $("#say-text").value }); if (r && r.ok) $("#say-text").value = ""; });
    $("#chat-form").addEventListener("submit", async (e) => { e.preventDefault(); const r = await cmd("chat_send", { text: $("#chat-text").value }); if (r && r.ok) $("#chat-text").value = ""; });
    $("#aud-form").addEventListener("submit", audition);
    $("#pron-form").addEventListener("submit", async (e) => { e.preventDefault(); await post("/api/pronunciations", { term: $("#pron-term").value, spoken: $("#pron-spoken").value }); loadPersona(); });
    $("#persona-reset").addEventListener("click", async () => { await post("/api/settings/conversation/reset"); loadPersona(); });
    $("#mem-search").addEventListener("click", loadMemory);
    $("#mem-domain").addEventListener("change", loadMemory);
    $("#mem-form").addEventListener("submit", async (e) => { e.preventDefault(); const d = $("#mem-new-domain").value;
      await post("/api/memory", { domain: d, title: $("#mem-title").value, body: $("#mem-body").value, shareable: d === "public" }); $("#mem-body").value = ""; loadMemory(); });
    $("#doc-form").addEventListener("submit", async (e) => { e.preventDefault(); const f = $("#doc-file").files[0]; if (!f) return;
      const fd = new FormData(); fd.append("file", f); fd.append("domain", $("#doc-share").checked ? "public" : "owner_private"); fd.append("shareable", $("#doc-share").checked);
      const r = await api("/api/documents", { method: "POST", body: fd }); toast(r.ok ? `Ingested ${r.filename}: ${r.chunks} chunks` : "Rejected: " + r.reason, !r.ok); loadMemory(); });
    $("#sched-form").addEventListener("submit", async (e) => { e.preventDefault();
      const start = $("#sched-start").value + ":00+06:00";
      const r = await post("/api/schedules", { title: $("#sched-title").value, url: $("#sched-url").value, start_iso: start, recurrence: $("#sched-rec").value });
      toast(r.ok ? "Meeting approved." : "Not saved: " + r.reason, !r.ok); loadSchedules(); });
    $("#key-form").addEventListener("submit", async (e) => { e.preventDefault(); $("#key-msg").textContent = "Validating…";
      const r = await post("/api/secrets/gemini", { key: $("#key").value }); $("#key").value = "";
      $("#key-msg").textContent = r.ok ? "Key validated and saved to Windows Credential Manager." : r.reason; });
    $("#key-del").addEventListener("click", async () => { await api("/api/secrets/gemini", { method: "DELETE" }); $("#key-msg").textContent = "Key deleted."; });
    $("#probe-btn").addEventListener("click", async () => { $("#key-msg").textContent = "Probing (uses a few free requests)…";
      const r = await post("/api/probe"); $("#key-msg").textContent = r.results.map((x) => `${x.model}: ${x.result}`).join(" | ") || "No key configured."; renderRegistry(r.registry); });
    $("#pass-form").addEventListener("submit", async (e) => { e.preventDefault(); try { await post("/api/passphrase", { passphrase: $("#newpass").value }); $("#newpass").value = ""; toast("Passphrase set."); loadSecurity(); } catch (err) { toast(err.message, true); } });
    $("#revoke").addEventListener("click", async () => { await post("/api/sessions/revoke"); location.reload(); });
  }

  async function cmd(kind, payload) {
    try { const r = await post("/api/command", { kind, payload: payload || {} });
      if (r.needs_confirmation) toast("Needs your confirmation in Approvals.");
      else if (!r.ok) toast(`${kind}: ${r.reason || "failed"}`, true);
      else if (r.text) addOwnerReply("Claumeet (private)", r.text);
      return r; } catch (err) { toast(err.message, true); }
  }
  async function estop() { const r = await cmd("emergency_stop"); if (r && r.ok) toast(`Emergency stop: audio flushed in ${r.flush_ms} ms. Claumeet is muted and paused.`); }

  // ---------- live updates ----------
  function connectWS() {
    const ws = new WebSocket((location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws");
    ws.onmessage = (m) => { const ev = JSON.parse(m.data); onEvent(ev); };
    ws.onclose = () => setTimeout(connectWS, 3000);
  }
  function onEvent(ev) {
    if (ev.kind === "status") return renderStatus(ev.data);
    if (ev.kind === "owner_hint") toast(ev.data.text);
    if (ev.kind === "owner_reply" || ev.kind === "vision") addOwnerReply("Claumeet (private)", ev.data.text);
    if (ev.kind === "transcript") addLine("#transcript", ev.data.speaker, ev.data.text, ev.ts);
    if (ev.kind === "chat") addLine("#chat", ev.data.sender, ev.data.text, ev.ts);
    if (ev.kind === "decision") addDecision(ev.data);
    if (ev.kind === "error") toast("Error: " + (ev.data.error || ""), true);
    if (ev.kind === "ended") toast("Meeting ended: " + ev.data.reason);
  }
  function addLine(sel, who, text, ts) {
    const box = $(sel); const d = el("div");
    d.append(el("span", "muted small", fmtTime(ts) + " "), el("span", who === "Claumeet" ? "claude" : "who", who + ": "), el("span", "", text));
    box.append(d); while (box.children.length > 300) box.firstChild.remove(); box.scrollTop = box.scrollHeight;
  }
  function addDecision(d) {
    const box = $("#decisions"); box.append(el("div", "", `${fmtTime(d.ts)}  ${d.what} → ${d.verdict} (${d.reason})`));
    while (box.children.length > 300) box.firstChild.remove(); box.scrollTop = box.scrollHeight;
  }
  function addOwnerReply(who, text) { const box = $("#owner-replies"); const d = el("div"); d.append(el("span", "who", who + ": "), el("span", "", text)); box.append(d); box.scrollTop = box.scrollHeight; }

  function kv(target, obj) {
    const dl = $(target); dl.replaceChildren();
    for (const [k, v] of Object.entries(obj)) { dl.append(el("dt", "", k), el("dd", "", v === null || v === undefined ? "—" : String(v))); }
  }
  function renderStatus(s) {
    lastStatus = s;
    $("#state-pill").textContent = s.state + (s.controls.output_muted ? " · muted" : "") + (s.controls.processing_paused ? " · paused" : "");
    const dot = $("#state-dot"); dot.className = "dot " + (["listening", "speaking", "thinking"].includes(s.state) ? "live" : ["failed"].includes(s.state) ? "bad" : s.state === "idle" ? "" : "warn");
    $("#consent-btn").disabled = !["consent_pending", "paused"].includes(s.state);
    const inMeeting = !["idle", "ended", "failed"].includes(s.state);
    document.querySelectorAll("#tab-overview [data-cmd], #tab-owner [data-cmd], #say-form button, #chat-form button").forEach((b) => {
      b.disabled = !inMeeting; b.title = inMeeting ? "" : "Available while Claumeet is in a meeting"; });
    const r = s.resources || {};
    kv("#ov-kv", { Meeting: s.meeting || "none", "In meeting for": s.meeting_uptime ? Math.round(s.meeting_uptime / 60) + " min" : "—",
      Provider: s.provider.status, "Live model": s.provider.live_model, Voice: s.provider.voice, "API key": s.provider.key_configured ? "configured" : "not set",
      "Free-only": s.provider.free_only ? "on" : "OFF", "Resource tier": s.governor.tier + (s.governor.reasons.length ? " (" + s.governor.reasons.join(", ") + ")" : ""),
      "App RAM": r.rss_mb ? r.rss_mb + " MB (" + r.processes + " processes)" : "—", "System free RAM": r.system_available_mb ? r.system_available_mb + " MB" : "—",
      Uptime: Math.round(s.uptime / 60) + " min" });
    const env = $("#envelope"); env.replaceChildren(); (s.envelope || []).forEach((v) => { const b = el("span"); b.style.height = Math.max(2, Math.min(32, v * 64)) + "px"; env.append(b); });
    const c = s.consent; const cb = $("#consent-box"); cb.replaceChildren();
    cb.append(el("div", "", "Disclosure given: " + (c.disclosure_given ? "yes" : "no")));
    cb.append(el("div", "", "Allowed now: " + (Object.entries(c.modalities).filter(([, v]) => v).map(([k]) => k).join(", ") || "nothing yet")));
    c.participants.forEach((p) => cb.append(el("div", "muted", `${p.name}: audio ${p.status.audio}, chat ${p.status.chat}`)));
    const roster = $("#roster"); roster.replaceChildren(); if (!s.participants.length) roster.append(el("p", "muted", "No participants visible."));
    s.participants.forEach((p) => roster.append(el("div", "", p.name)));
    const ap = $("#approvals"); ap.replaceChildren(); if (!s.approvals.length) ap.append(el("p", "muted", "Nothing to approve."));
    s.approvals.forEach((a) => { const d = el("div"); d.append(el("div", "", `${a.kind} — ${a.reason} (expires in ${a.expires_in}s)`), el("div", "muted small", JSON.stringify(a.payload)));
      const yes = el("button", "btn primary", "Approve"), no = el("button", "btn", "Deny");
      yes.onclick = () => post("/api/approvals/" + a.id, { approve: true }).then((r) => toast(r.ok ? "Approved." : r.reason, !r.ok));
      no.onclick = () => post("/api/approvals/" + a.id, { approve: false }); const row = el("div", "row"); row.append(yes, no); d.append(row); ap.append(d); });
    const lat = s.latency || {}; const perf = {};
    for (const [k, v] of Object.entries(lat)) perf[k] = `p50 ${v.p50} ms · p95 ${v.p95} ms (n=${v.n})`;
    for (const [k, v] of Object.entries(s.counters || {})) perf[k] = v;
    perf["CPU (app)"] = r.cpu_percent !== undefined ? r.cpu_percent + "%" : "—"; perf["CPU (system)"] = r.system_cpu_percent !== undefined ? r.system_cpu_percent + "%" : "—";
    perf["Last error"] = s.provider.last_error || "none";
    (s.provider.health || []).forEach((h) => { perf["health:" + h.name] = `${h.available ? "available" : "suspended " + h.suspended_seconds + "s"} · req ${h.requests} · 429s ${h.quota_hits}`; });
    perf["Browser capabilities"] = JSON.stringify(s.browser_capabilities);
    kv("#perf", perf);
  }
  async function refreshAll() { try { renderStatus(await api("/api/status")); refreshLive(); } catch (e) { /* auth handled */ } }
  async function refreshLive() {
    if ($("#tab-live").classList.contains("hidden")) return;
    const l = await api("/api/live"); const q = $("#questions"); q.replaceChildren();
    l.questions.forEach((x) => q.append(el("div", x.answered ? "muted" : "", (x.answered ? "✓ " : "• ") + x.text)));
  }

  // ---------- first-run wizard ----------
  async function loadWizard() {
    const w = await api("/api/setup");
    const box = $("#wizard");
    if (w.complete || w.dismissed) { box.classList.add("hidden"); return; }
    box.classList.remove("hidden");
    w.steps.forEach((st) => $("#step-" + st.id).classList.toggle("done", st.done));
  }
  function bindWizard() {
    $("#wz-signin").addEventListener("click", async () => { const r = await post("/api/setup/signin"); toast(r.ok ? "Chrome opened. Sign in Claumeet's account there, then click \"I've signed in\"." : r.reason, !r.ok); });
    $("#wz-signed").addEventListener("click", async () => { await post("/api/setup/mark", { google_signed_in: true }); loadWizard(); });
    $("#wz-key-form").addEventListener("submit", async (e) => { e.preventDefault(); $("#wz-key-msg").textContent = "Checking the key with Google…";
      const r = await post("/api/secrets/gemini", { key: $("#wz-key").value.trim() }); $("#wz-key").value = "";
      $("#wz-key-msg").textContent = r.ok ? "✓ Key works and is saved." : "✗ " + r.reason + ". Copy the key again from AI Studio and paste it."; loadWizard(); });
    $("#wz-probe").addEventListener("click", async () => { $("#wz-probe-msg").textContent = "Testing… (up to a minute)";
      const r = await post("/api/probe"); const ok = r.results.filter((x) => x.result === "ok");
      $("#wz-probe-msg").textContent = r.results.length ? (ok.length ? `✓ Working: ${ok.map((x) => x.model).join(", ")}` : "✗ No free model answered. Check the key, or try again in a few minutes.") : "Save your key first.";
      loadWizard(); });
    $("#wz-hide").addEventListener("click", async () => { await post("/api/setup/mark", { dismissed: true }); loadWizard(); });
  }

  // ---------- persona ----------
  const SLIDERS = [["humor", "Humor"], ["initiative", "Initiative"], ["energy", "Energy"]];
  async function loadPersona() {
    const s = lastStatus || (await api("/api/status")); const c = s.conversation;
    const modes = $("#modes"); modes.replaceChildren();
    ["automatic", "casual", "professional", "educational", "serious", "quiet"].forEach((m) => {
      const b = el("button", "btn" + (c.mode === m ? " active" : ""), m); b.onclick = async () => { await post("/api/settings/conversation", { mode: m }); lastStatus = await api("/api/status"); loadPersona(); }; modes.append(b); });
    const f = $("#persona-form"); f.replaceChildren();
    SLIDERS.forEach(([k, label]) => { const l = el("label", "", `${label}: ${c[k]}`); const i = el("input"); i.type = "range"; i.min = 0; i.max = 1; i.step = 0.05; i.value = c[k];
      i.onchange = async () => { await post("/api/settings/conversation", { [k]: Number(i.value) }); l.firstChild.textContent = `${label}: ${i.value}`; }; l.append(i); f.append(l); });
    [["response_sentences", "Response length (sentences)", 1, 8], ["min_unsolicited_gap_seconds", "Min gap between unprompted turns (s)", 5, 180], ["max_consecutive_turns", "Max consecutive turns", 1, 8], ["chat_per_minute", "Chat messages per minute", 0, 10]].forEach(([k, label, mn, mx]) => {
      const l = el("label", "", `${label}: ${c[k]}`); const i = el("input"); i.type = "range"; i.min = mn; i.max = mx; i.step = 1; i.value = c[k];
      i.onchange = async () => { await post("/api/settings/conversation", { [k]: Number(i.value) }); l.firstChild.textContent = `${label}: ${i.value}`; }; l.append(i); f.append(l); });
    const p = await api("/api/pronunciations"); const box = $("#prons"); box.replaceChildren();
    p.forEach((x) => { const d = el("div", "", `${x.term} → ${x.spoken} `); const del = el("button", "btn", "Delete"); del.onclick = async () => { await api("/api/pronunciations/" + encodeURIComponent(x.term), { method: "DELETE" }); loadPersona(); }; d.append(del); box.append(d); });
  }
  async function audition(e) {
    e.preventDefault(); $("#aud-info").textContent = "Generating…";
    const r = await post("/api/audition", { text: $("#aud-text").value });
    if (!r.ok) { $("#aud-info").textContent = "Unavailable: " + r.reason; return; }
    const pl = $("#aud-player"); pl.src = "data:audio/wav;base64," + r.wav_b64; pl.classList.remove("hidden"); pl.play();
    $("#aud-info").textContent = `${r.provider} · generated in ${r.ms} ms`;
  }

  // ---------- memory ----------
  async function loadMemory() {
    const d = $("#mem-domain").value, q = $("#mem-q").value.trim();
    const rows = await api("/api/memory?" + new URLSearchParams(q ? { q } : d ? { domain: d } : {}));
    const box = $("#mem-list"); box.replaceChildren(); if (!rows.length) box.append(el("p", "muted", "No memories."));
    rows.forEach((m) => { const div = el("div"); div.append(el("span", "badge", m.domain), el("b", "", " " + (m.title || "(untitled)")), el("div", "small", m.body),
      el("div", "muted small", `source: ${m.source || "—"} · ${new Date(m.created * 1000).toLocaleDateString()}${m.expires ? " · expires " + new Date(m.expires * 1000).toLocaleDateString() : ""}`));
      const del = el("button", "btn", "Delete"); del.onclick = async () => { await api("/api/memory/" + m.id, { method: "DELETE" }); loadMemory(); }; div.append(del); box.append(div); });
    const docs = await api("/api/documents"); const db = $("#docs"); db.replaceChildren();
    docs.forEach((x) => db.append(el("div", "", `${x.filename} · ${x.chunks} chunks · ${x.domain}${x.shareable ? " · shareable" : ""}`)));
  }
  // ---------- schedules ----------
  async function loadSchedules() {
    const r = await api("/api/schedules"); const box = $("#sched-list"); box.replaceChildren();
    if (!r.schedules.length) box.append(el("p", "muted", "No approved meetings."));
    r.schedules.forEach((s) => { const d = el("div"); d.append(el("b", "", s.title), el("div", "muted small", `${s.recurrence} · starts ${s.start_iso} · next ${s.next || "—"} · ${s.enabled ? "enabled" : "disabled"}`));
      const t = el("button", "btn", s.enabled ? "Disable" : "Enable"); t.onclick = async () => { await post(`/api/schedules/${s.id}/enabled`, { approve: !s.enabled }); loadSchedules(); };
      const del = el("button", "btn warn", "Delete"); del.onclick = async () => { await api("/api/schedules/" + s.id, { method: "DELETE" }); loadSchedules(); };
      const row = el("div", "row"); row.append(t, del); d.append(row); box.append(d); });
    const m = $("#missed"); m.replaceChildren(); r.missed.forEach((x) => m.append(el("div", "", `${x.title} ${x.occurrence}: ${x.reason}`)));
  }
  // ---------- provider ----------
  async function loadRegistry() { renderRegistry(await api("/api/registry")); }
  function renderRegistry(rows) { const box = $("#registry"); box.replaceChildren();
    rows.forEach((m) => box.append(el("div", "", `${m.kind.padEnd(5)} ${m.id}  · free tier: ${m.free_tier} · ${m.status} · probe: ${m.probe}`))); }
  // ---------- security ----------
  async function loadSecurity() {
    const s = await api("/api/security");
    kv("#sec-kv", { "Bound to": s.bind_host, "Active sessions": s.sessions.length, "Passphrase": s.passphrase_set ? "set" : "not set (pairing link only)",
      "Secret store": s.secret_backend, "Gemini key": s.key_configured ? "stored" : "not stored", "Raw audio retention": s.retention.retain_raw_audio ? "ON" : "off",
      "Vision": s.vision_enabled ? "enabled" : "disabled" });
    const a = await api("/api/audit"); const box = $("#audit"); box.replaceChildren();
    a.forEach((x) => box.append(el("div", "", `${new Date(x.ts * 1000).toLocaleString()}  ${x.actor}  ${x.action}  ${x.decision}  ${x.reason}`)));
  }

  boot();
})();
