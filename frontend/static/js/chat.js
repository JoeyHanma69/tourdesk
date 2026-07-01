/**
 * chat.js — TourDesk guest chatbot
 * ================================
 * Initialises a conversation with the app, then exchanges messages with the
 * /api/chat endpoint.
 */

const thread   = document.getElementById("chat-thread");
const form     = document.getElementById("chat-form");
const input    = document.getElementById("chat-input");
const sendBtn  = document.getElementById("chat-send");

let sessionId = null;
let lastAgentId = 0;          // highest staff-reply id we've shown
const POLL_MS = 3000;         // how often we check for staff replies

// ── Render helpers ────────────────────────────────────────────────────────────
function addBubble(text, who) {
  const el = document.createElement("div");
  el.className = `bubble bubble-${who}`;
  el.textContent = text;
  thread.appendChild(el);
  thread.scrollTop = thread.scrollHeight;
  return el;
}

function showTyping() {
  const el = document.createElement("div");
  el.className = "bubble bubble-bot bubble-typing";
  el.innerHTML = "<span></span><span></span><span></span>";
  thread.appendChild(el);
  thread.scrollTop = thread.scrollHeight;
  return el;
}

// ── Start the conversation ────────────────────────────────────────────────────
async function initConversation() {
  try {
    const res  = await fetch("/api/chat/welcome");
    const data = await res.json();
    sessionId = data.session_id;
    addBubble(data.reply, "bot");
  } catch (_) {
    addBubble("👋 Welcome to Turtle Down Under! How can we help?", "bot");
  }
}

// ── Send a message ────────────────────────────────────────────────────────────
async function sendMessage(text) {
  addBubble(text, "user");
  const typing = showTyping();
  setBusy(true);

  try {
    const res  = await fetch("/api/chat", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ text, session_id: sessionId }),
    });
    const data = await res.json();
    typing.remove();
    // When a human has taken over, the bot stays silent — their reply arrives
    // via polling instead. Otherwise show the bot's reply.
    if (!data.handled) {
      addBubble(data.reply || "Sorry, something went wrong. Please try again.", "bot");
    }
  } catch (_) {
    typing.remove();
    addBubble("⚠️ Couldn't reach our team right now. Please try again shortly.", "bot");
  } finally {
    setBusy(false);
  }
}

function setBusy(busy) {
  input.disabled   = busy;
  sendBtn.disabled = busy;
  if (!busy) input.focus();
}

// ── Wire up the composer ──────────────────────────────────────────────────────
form.addEventListener("submit", e => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  sendMessage(text);
});

// ── Poll for staff replies ────────────────────────────────────────────────────
async function pollForStaffReplies() {
  if (!sessionId) return;
  try {
    const res  = await fetch(`/api/chat/poll?session_id=${sessionId}&after=${lastAgentId}`);
    const data = await res.json();
    (data.messages || []).forEach(m => {
      addBubble(m.text, "agent");
      if (m.id > lastAgentId) lastAgentId = m.id;
    });
  } catch (_) {}
}

initConversation();
setInterval(pollForStaffReplies, POLL_MS);
