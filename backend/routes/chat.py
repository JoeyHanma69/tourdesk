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
from backend.utils.chat import (
    WELCOME_MESSAGE,
    is_urgent,
    build_booking_reply,
    build_automated_reply,
    build_assisted_reply,
    build_escalation_reply,
    build_uncertain_reply,
    build_staff_note,
)

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

    # ── Classify ─────────────────────────────────────────────────────────────
    prediction = current_app.classifier.predict(text) 
    # Safety net: a deterministic keyword check forces urgent/safety messages to
    # Escalate, even when the ML model misses them. Applied before storing so the
    # dashboard also shows it flagged as an escalation.
    if is_urgent(text):
        logger.warning(f"🚨 URGENT keyword match — forcing Escalate. From {sender}: {text[:80]}")
        prediction.label = "Escalate"
        prediction.uncertain = False 


    add_message(sender, text, prediction)

    logger.info(
        f"[{prediction.label}] {prediction.confidence:.0%} | "
        f"From {sender}: {text[:60]}"
    )

    # ── Build the reply based on tier ────────────────────────────────────────
    reply = _build_reply(sender, text, prediction)

    return jsonify({
        "reply":      reply,
        "label":      prediction.label,
        "confidence": prediction.confidence,
        "uncertain":  prediction.uncertain,
    })


def _build_reply(sender: str, text: str, prediction) -> str:
    """Pick the right reply for the predicted tier."""
    # Booking enquiries are handled first, with a verify-before-reveal gate,
    # regardless of the classified tier. Returns None if there's no reference.
    booking_reply = build_booking_reply(text)
    if booking_reply:
        return booking_reply

    if prediction.uncertain:
        logger.info(f"⚠️  Low confidence ({prediction.confidence:.0%}) — routed to human review")
        return build_uncertain_reply(text)

    if prediction.label == "Automated":
        return build_automated_reply(text)

    if prediction.label == "Assisted":
        logger.info(f"📋 Assisted: queued for staff review from {sender}")
        return build_assisted_reply(text)

    if prediction.label == "Escalate":
        logger.warning(f"🚨 ESCALATION from {sender}: {text[:80]}")
        logger.warning(build_staff_note(sender, text))
        return build_escalation_reply(text)

    # Fallback for any unexpected label
    return build_automated_reply(text)
