"""
backend/routes/chat.py
======================
The TourDesk web chatbot.

GET  /chat            — Serves the guest-facing chat page (the chatbot widget).
POST /api/chat        — A guest message from the chatbot. We classify it, store
                        it, and return the assistant's reply in the same response.
GET  /api/chat/poll    — Polled by the chat widget to pick up staff replies sent
                        from the dashboard (those aren't returned synchronously).

Conversations start inside our own TDU web application — no external
messaging provider is involved.
"""

import logging
import uuid

from flask import Blueprint, request, jsonify, render_template, current_app

from backend.utils.message_store import add_message, get_staff_replies_since
from backend.utils.chat import (
    WELCOME_MESSAGE,
    build_booking_reply,
    build_automated_reply,
    build_assisted_reply,
    build_escalation_reply,
    build_uncertain_reply,
    build_staff_note,
)
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
    attachment = body.get("attachment")

    if not text and not attachment:
        return jsonify({"error": "text field is required"}), 400

    # ── Classify + decide ────────────────────────────────────────────────────
    # The whole handling decision lives in pipeline.decide(), so the web app and
    # the CLI test harness share identical logic. An attachment-only message
    # (e.g. a guest just sends a photo) still needs some text to classify.
    prediction = current_app.classifier.predict(text or "[attachment]")
    decision = decide(prediction, text)

    # Reflect the final tier in the stored record so the dashboard matches the
    # reply the guest actually received (e.g. an urgent override shows Escalate).
    prediction.label = decision.final_label
    prediction.uncertain = decision.uncertain
    add_message(sender, text, prediction, attachment=attachment)

    logger.info(
        f"[{decision.final_label}] {decision.confidence:.0%} | "
        f"From {sender}: {text[:60]}"
    )
    if decision.urgent_override:
        logger.warning(f"🚨 URGENT keyword match — forced Escalate. From {sender}: {text[:80]}")
    if decision.final_label == "Escalate":
        logger.warning(build_staff_note(sender, text))

    # Build the assistant reply based on the prediction and message
    reply = decision.reply

    return jsonify({
        "reply":      reply,
        "label":      prediction.label,
        "confidence": prediction.confidence,
        "uncertain":  prediction.uncertain,
    })


# ── GET /api/chat/poll — pick up staff replies ───────────────────────────────
@chat_bp.route("/api/chat/poll", methods=["GET"])
def poll():
    """
    Polled by the chat widget every few seconds to pick up replies staff sent
    from the dashboard — those are delivered asynchronously, not in the
    response to /api/chat.

    Query: ?session_id=...&since_id=0
    Returns: [ { id, text, attachment, timestamp, ... }, ... ]  (oldest first)
    """
    session_id = str(request.args.get("session_id", "")).strip()
    since_id = int(request.args.get("since_id", 0) or 0)

    if not session_id:
        return jsonify([])

    return jsonify(get_staff_replies_since(session_id, since_id))


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
