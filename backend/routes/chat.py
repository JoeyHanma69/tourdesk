"""
backend/routes/chat.py
======================
The TourDesk web chatbot.

GET  /chat       — Serves the guest-facing chat page (the chatbot widget).
POST /api/chat   — A guest message from the chatbot. We classify it, store it,
                   and return the assistant's reply in the same response.

Conversations start inside our own TDU web application — no external
messaging provider is involved.
"""

import logging
import uuid

from flask import Blueprint, request, jsonify, render_template, current_app

from backend.utils.message_store import add_message
from backend.utils.chat import WELCOME_MESSAGE, build_staff_note
from backend.utils.pipeline import decide

logger = logging.getLogger(__name__)
chat_bp = Blueprint("chat", __name__)


# ── GET /chat — guest chatbot page ───────────────────────────────────────────
@chat_bp.route("/chat", methods=["GET"])
def chat_page():
    """Serve the chatbot widget that initialises a conversation with the app."""
    return render_template("chat.html", welcome=WELCOME_MESSAGE)


# ── GET /api/chat/welcome — opening message ──────────────────────────────────
@chat_bp.route("/api/chat/welcome", methods=["GET"])
def welcome():
    """
    Called when the chatbot first opens to start the conversation.
    Returns a fresh session id and the assistant's greeting.
    """
    return jsonify({
        "session_id": uuid.uuid4().hex,
        "reply": WELCOME_MESSAGE,
    })


# ── POST /api/chat — incoming guest message ──────────────────────────────────
@chat_bp.route("/api/chat", methods=["POST"])
def receive():
    """
    Handle one message from the chatbot.

    Body: { "text": "...", "session_id": "..." (optional) }
    Returns: { "reply": "...", "label": "...", "confidence": .., "uncertain": .. }
    """
    body = request.get_json(silent=True) or {}
    text = str(body.get("text", "")).strip()
    sender = str(body.get("session_id", "")).strip() or "guest"

    if not text:
        return jsonify({"error": "text field is required"}), 400

    # ── Classify + decide ────────────────────────────────────────────────────
    # The whole handling decision lives in pipeline.decide(), so the web app and
    # the CLI test harness share identical logic.
    prediction = current_app.classifier.predict(text)
    decision = decide(prediction, text)

    # Reflect the final tier in the stored record so the dashboard matches the
    # reply the guest actually received (e.g. an urgent override shows Escalate).
    prediction.label = decision.final_label
    prediction.uncertain = decision.uncertain
    add_message(sender, text, prediction)

    logger.info(
        f"[{decision.final_label}] {decision.confidence:.0%} | "
        f"From {sender}: {text[:60]}"
    )
    if decision.urgent_override:
        logger.warning(f"🚨 URGENT keyword match — forced Escalate. From {sender}: {text[:80]}")
    if decision.final_label == "Escalate":
        logger.warning(build_staff_note(sender, text))

    return jsonify({
        "reply":      decision.reply,
        "label":      decision.final_label,
        "confidence": decision.confidence,
        "uncertain":  decision.uncertain,
    })
