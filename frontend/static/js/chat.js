/**
 * chat.js — TourDesk guest chatbot
 * ================================
 * Initialises a conversation with the app, then exchanges messages with the
 * /api/chat endpoint. Also polls /api/chat/poll so replies staff send from
 * the dashboard show up here without a page reload.
 */

const thread   = document.getElementById("chat-thread");
const form     = document.getElementById("chat-form");
const input    = document.getElementById("chat-input");
const sendBtn  = document.getElementById("chat-send");

let sessionId = null;

// ── Render helpers ────────────────────────────────────────────────────────────
function addBubble(text, who, attachment) {
  const el = document.createElement("div");
  el.className = `bubble bubble-${who}`;

  if (text) {
    const textEl = document.createElement("div");
    textEl.textContent = text;
    el.appendChild(textEl);
  }
  if (attachment) {
    el.appendChild(renderAttachment(attachment));
  }

  thread.appendChild(el);
  thread.scrollTop = thread.scrollHeight;
  return el;
}

function renderAttachment(attachment) {
  if (attachment.is_image) {
    const img = document.createElement("img");
    img.src = attachment.url;
    img.alt = attachment.filename || "attachment";
    img.className = "bubble-attachment-img";
    return img;
  }
  const link = document.createElement("a");
  link.href = attachment.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.className = "bubble-attachment-file";
  link.textContent = "📄 " + (attachment.filename || "attachment");
  return link;
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
  startPolling();
}

// ── Send a message ────────────────────────────────────────────────────────────
async function sendMessage(text) {
  const attachment = pendingAttachment;
  addBubble(text, "user", attachment);
  clearAttachment();
  const typing = showTyping();
  setBusy(true);

  try {
    const res  = await fetch("/api/chat", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ text, session_id: sessionId, attachment }),
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

// ── Attachments ────────────────────────────────────────────────────────────────
attachBtn.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", async () => {
  const file = fileInput.files[0];
  fileInput.value = "";
  if (!file) return;

  attachBtn.disabled = true;
  try {
    const formData = new FormData();
    formData.append("file", file);
    const res  = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) {
      alert(data.error || "Upload failed");
      return;
    }
    pendingAttachment = data;
    renderAttachPreview();
  } catch (e) {
    alert("Upload failed: " + e.message);
  } finally {
    attachBtn.disabled = false;
  }
});

function renderAttachPreview() {
  if (!pendingAttachment) {
    attachPreview.classList.add("hidden");
    attachPreview.innerHTML = "";
    return;
  }
  attachPreview.classList.remove("hidden");
  attachPreview.innerHTML = "";

  const label = document.createElement("span");
  label.textContent = "📎 " + pendingAttachment.filename;
  attachPreview.appendChild(label);

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "chat-attach-remove";
  remove.textContent = "✕";
  remove.addEventListener("click", clearAttachment);
  attachPreview.appendChild(remove);
}

function clearAttachment() {
  pendingAttachment = null;
  renderAttachPreview();
}

// ── Wire up the composer ──────────────────────────────────────────────────────
form.addEventListener("submit", e => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text && !pendingAttachment) return;
  input.value = "";
  sendMessage(text);
});

initConversation();
setInterval(pollForStaffReplies, POLL_MS);
