"""
backend/routes/webhook.py
==========================
Handles the WhatsApp Cloud API webhook.

GET  /webhook  — Meta's verification handshake (required once during setup)
POST /webhook  — Incoming messages from guests
"""

import hashlib
import hmac
import logging
import os

from flask import Blueprint, request, jsonify, current_app

from backend.utils.message_store import add_message
from backend.utils.whatsapp import send_text, build_automated_reply, build_escalation_alert

logger = logging.getLogger(__name__)
webhook_bp = Blueprint("webhook", __name__)


# ── GET /webhook — Meta verification handshake ───────────────────────────────
@webhook_bp.route("/webhook", methods=["GET"])
def verify():
    """
    When you register a webhook URL in the Meta Developer Portal,
    Meta sends this GET request to confirm you control the endpoint.
    """
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    verify_token = current_app.config.get("WHATSAPP_VERIFY_TOKEN", "")

    if mode == "subscribe" and token == verify_token:
        logger.info("✅ Webhook verified by Meta")
        return challenge, 200

    logger.warning(f"❌ Webhook verification failed — token mismatch")
    return "Forbidden", 403


# ── POST /webhook — Incoming messages ────────────────────────────────────────
@webhook_bp.route("/webhook", methods=["POST"])
def receive():
    """
    Meta posts every incoming WhatsApp message here.
    We classify it, store it, and optionally reply.
    """
    # Optional: verify the X-Hub-Signature-256 header for security
    _verify_signature(request)

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "ignored", "reason": "no JSON body"}), 200

    try:
        _process_payload(data)
    except Exception as e:
        logger.error(f"Error processing webhook payload: {e}", exc_info=True)

    # Always return 200 to Meta — otherwise it retries endlessly
    return jsonify({"status": "ok"}), 200


def _process_payload(data: dict):
    """Extract messages from the Meta webhook payload and classify them."""
    entry = data.get("entry", [])
    for e in entry:
        for change in e.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])

            for msg in messages:
                if msg.get("type") != "text":
                    continue  # skip image/audio/etc for now

                sender = msg.get("from", "unknown")
                text   = msg.get("text", {}).get("body", "").strip()

                if not text:
                    continue

                # ── Classify ────────────────────────────────────────────────
                prediction = current_app.classifier.predict(text)
                record     = add_message(sender, text, prediction)

                logger.info(
                    f"[{prediction.label}] {prediction.confidence:.0%} | "
                    f"From {sender}: {text[:60]}"
                )

                # ── Route based on tier ─────────────────────────────────────
                _handle_tier(sender, text, prediction)


def _handle_tier(sender: str, text: str, prediction):
    """Take action based on the predicted tier."""

    if prediction.uncertain:
        # Low confidence — send to staff review queue, don't auto-reply
        logger.info(f"⚠️  Low confidence ({prediction.confidence:.0%}) — flagged for review")
        return

    if prediction.label == "Automated":
        # Send an automated reply
        reply = build_automated_reply(text)
        send_text(sender, reply)

    elif prediction.label == "Assisted":
        # Flag for staff — no auto-reply, just appears in dashboard
        logger.info(f"📋 Assisted: queued for staff review from {sender}")

    elif prediction.label == "Escalate":
        # Alert staff immediately
        staff_number = os.getenv("STAFF_ALERT_NUMBER", "")
        if staff_number:
            alert = build_escalation_alert(sender, text)
            send_text(staff_number, alert)
        logger.warning(f"🚨 ESCALATION from {sender}: {text[:80]}")


def _verify_signature(req):
    """Verify X-Hub-Signature-256 from Meta. Logs warning if invalid, doesn't block."""
    app_secret = os.getenv("WHATSAPP_APP_SECRET", "")
    sig_header = req.headers.get("X-Hub-Signature-256", "")

    if not app_secret or not sig_header:
        return  # Skip if not configured

    expected = "sha256=" + hmac.new(
        app_secret.encode(), req.data, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, sig_header):
        logger.warning("⚠️  Webhook signature mismatch — possible spoofed request")
