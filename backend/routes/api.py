"""
backend/routes/api.py
======================
JSON API consumed by the frontend dashboard via fetch().

GET  /api/messages        — All stored messages (newest first)
GET  /api/stats           — Counts per tier + uncertainty
POST /api/classify        — Manually test a message
GET  /api/health          — Model status check
"""

from flask import Blueprint, jsonify, request, current_app
from backend.utils.message_store import get_all, get_stats, add_message, add_agent_message

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/staff/reply", methods=["POST"])
def staff_reply():
    """A TDU staff member replies into a guest's chat.

    Body: { "session_id": "...", "text": "..." }
    Stores the reply and marks the session as human-handled (the bot goes quiet).
    The guest's chat picks it up via GET /api/chat/poll.
    """
    body = request.get_json(silent=True) or {}
    session_id = str(body.get("session_id", "")).strip()
    text = str(body.get("text", "")).strip()
    if not session_id or not text:
        return jsonify({"error": "session_id and text are required"}), 400

    record = add_agent_message(session_id, text)
    return jsonify(record)


@api_bp.route("/messages", methods=["GET"])
def messages():
    """Return all messages stored in memory, newest first."""
    label  = request.args.get("label")   # optional filter e.g. ?label=Escalate
    limit  = int(request.args.get("limit", 100))

    msgs = get_all()
    if label:
        msgs = [m for m in msgs if m["label"] == label]
    return jsonify(msgs[:limit])


@api_bp.route("/stats", methods=["GET"])
def stats():
    """Return per-tier message counts."""
    return jsonify(get_stats())


@api_bp.route("/classify", methods=["POST"])
def classify():
    """
    Manually classify a message — used by the dashboard test panel.

    Body: { "text": "your message here" }
    """
    body = request.get_json(silent=True) or {}
    text = str(body.get("text", "")).strip()

    if not text:
        return jsonify({"error": "text field is required"}), 400

    prediction = current_app.classifier.predict(text)

    # Optionally store test messages with a "test" sender tag
    if body.get("save", False):
        add_message("__test__", text, prediction)

    return jsonify({
        "text":       prediction.text,
        "label":      prediction.label,
        "confidence": prediction.confidence,
        "uncertain":  prediction.uncertain,
        "all_scores": prediction.all_scores,
    })


@api_bp.route("/health", methods=["GET"])
def health():
    """Quick status check — useful for monitoring and debugging."""
    return jsonify({
        "status":       "ok",
        "model_ready":  current_app.classifier.is_ready,
        "model_dir":    current_app.config.get("MODEL_DIR"),
        "threshold":    current_app.config.get("CONFIDENCE_THRESHOLD"),
    })
