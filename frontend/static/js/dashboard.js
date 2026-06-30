/**
 * dashboard.js — TourDesk AI Frontend Logic
 * ==========================================
 * - Polls /api/stats and /api/messages every 5 seconds
 * - Renders messages in the feed with tier badges
 * - Handles the test classifier panel
 */

const POLL_INTERVAL = 5000; // ms
let   currentFilter = "all";
let   lastMessageId = 0;

// Estimated staff handling time saved per auto-resolved message (minutes).
// Used only for the "Staff time saved (est.)" impact metric.
const MINUTES_SAVED_PER_AUTOMATED = 3;

// ── Clock ────────────────────────────────────────────────────────────────────
function updateClock() {
  const el = document.getElementById("live-clock");
  if (el) el.textContent = new Date().toLocaleTimeString("en-AU", { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

// ── Health check ─────────────────────────────────────────────────────────────
async function checkHealth() {
  try {
    const res  = await fetch("/api/health");
    const data = await res.json();
    const badge = document.getElementById("model-badge");
    if (!badge) return;
    if (data.model_ready) {
      badge.textContent = "Model Ready ✓";
      badge.className   = "badge badge-ready";
    } else {
      badge.textContent = "Stub Mode — model not loaded";
      badge.className   = "badge badge-stub";
    }
  } catch (_) {}
}
checkHealth();

// ── Stats ─────────────────────────────────────────────────────────────────────
async function refreshStats() {
  try {
    const res  = await fetch("/api/stats");
    const data = await res.json();
    setText("stat-total",     data.total     ?? 0);
    setText("stat-automated", data.Automated ?? 0);
    setText("stat-assisted",  data.Assisted  ?? 0);
    setText("stat-escalate",  data.Escalate  ?? 0);
    setText("stat-uncertain", data.uncertain ?? 0);
    renderImpact(data);
  } catch (_) {}
}

// ── Business impact metrics (derived from stats) ───────────────────────────────
function renderImpact(data) {
  const total     = data.total     ?? 0;
  const automated = data.Automated ?? 0;
  const escalate  = data.Escalate  ?? 0;

  // Auto-resolution rate
  const rate = total > 0 ? Math.round((automated / total) * 100) : 0;
  setText("impact-rate", total > 0 ? rate + "%" : "—");

  // Estimated staff time saved
  setText("impact-time", formatMinutesSaved(automated * MINUTES_SAVED_PER_AUTOMATED));

  // Escalations caught + total handled
  setText("impact-escalations", escalate);
  setText("impact-handled", total);
}

function formatMinutesSaved(mins) {
  if (mins <= 0) return "—";
  if (mins < 60) return mins + " min";
  const hrs = mins / 60;
  return (hrs < 10 ? hrs.toFixed(1) : Math.round(hrs)) + " hrs";
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

// ── Message feed ──────────────────────────────────────────────────────────────
async function refreshMessages() {
  try {
    const url  = currentFilter === "all"
      ? "/api/messages?limit=100"
      : currentFilter === "uncertain"
        ? "/api/messages?limit=100"
        : `/api/messages?label=${currentFilter}&limit=100`;

    const res  = await fetch(url);
    const msgs = await res.json();

    const filtered = currentFilter === "uncertain"
      ? msgs.filter(m => m.uncertain)
      : msgs;

    renderFeed(filtered);
  } catch (_) {}
}

function renderFeed(messages) {
  const feed = document.getElementById("message-feed");
  if (!feed) return;

  if (!messages.length) {
    feed.innerHTML = '<div class="empty-state">No messages yet. Waiting for chatbot messages…</div>';
    return;
  }

  feed.innerHTML = messages.map(m => {
    const time     = new Date(m.timestamp).toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit" });
    const confPct  = (m.confidence * 100).toFixed(0) + "%";
    const uncertain = m.uncertain
      ? '<span class="uncertain-tag">⚠ uncertain</span>'
      : "";

    return `
      <div class="msg-item tier-${m.label}">
        <div class="msg-tier">
          <span class="tier-badge badge-${m.uncertain ? "uncertain" : m.label}">
            ${m.uncertain ? "?" : m.label}
          </span>
        </div>
        <div class="msg-body">
          <div class="msg-text">${escapeHtml(m.text)}</div>
          <div class="msg-meta">
            <span class="msg-sender">📱 ${escapeHtml(m.sender)}</span>
            <span class="msg-time">${time}</span>
            <span class="msg-conf">${confPct}</span>
            ${uncertain}
          </div>
        </div>
      </div>`;
  }).join("");
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Filter tabs ───────────────────────────────────────────────────────────────
document.querySelectorAll(".filter-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentFilter = btn.dataset.label;
    refreshMessages();
  });
});

// ── Test panel ────────────────────────────────────────────────────────────────
const testBtn    = document.getElementById("test-btn");
const testInput  = document.getElementById("test-input");
const testResult = document.getElementById("test-result");

testBtn.addEventListener("click", runTest);
testInput.addEventListener("keydown", e => {
  if (e.key === "Enter" && e.ctrlKey) runTest();
});

async function runTest() {
  const text = testInput.value.trim();
  if (!text) return;

  testBtn.disabled    = true;
  testBtn.textContent = "Classifying…";
  testResult.classList.add("hidden");

  try {
    const res  = await fetch("/api/classify", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ text }),
    });
    const data = await res.json();
    renderTestResult(data);
  } catch (e) {
    alert("Error connecting to server: " + e.message);
  } finally {
    testBtn.disabled    = false;
    testBtn.textContent = "Classify";
  }
}

function renderTestResult(data) {
  const badgeEl     = document.getElementById("result-badge");
  const confEl      = document.getElementById("result-conf");
  const scoresEl    = document.getElementById("result-scores");
  const uncertainEl = document.getElementById("result-uncertain");

  const label  = data.uncertain ? "uncertain" : data.label;
  const confPct = (data.confidence * 100).toFixed(1) + "%";

  badgeEl.textContent = data.label;
  badgeEl.className   = `tier-badge badge-${label}`;
  confEl.textContent  = confPct + " confidence";

  // Score bars
  const order  = ["Automated", "Assisted", "Escalate"];
  scoresEl.innerHTML = order.map(cls => {
    const score = ((data.all_scores[cls] ?? 0) * 100).toFixed(1);
    return `
      <div class="score-row">
        <span class="score-name">${cls}</span>
        <div class="score-bar-wrap">
          <div class="score-bar-fill fill-${cls}" style="width:${score}%"></div>
        </div>
        <span class="score-pct">${score}%</span>
      </div>`;
  }).join("");

  if (data.uncertain) {
    uncertainEl.classList.remove("hidden");
  } else {
    uncertainEl.classList.add("hidden");
  }

  testResult.classList.remove("hidden");
}

// ── Polling loop ──────────────────────────────────────────────────────────────
async function poll() {
  await Promise.all([refreshStats(), refreshMessages()]);
}

poll();
setInterval(poll, POLL_INTERVAL);
