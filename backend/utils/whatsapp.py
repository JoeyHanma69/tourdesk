"""
backend/utils/whatsapp.py
==========================
Helpers for sending messages back via the WhatsApp Cloud API.
Docs: https://developers.facebook.com/docs/whatsapp/cloud-api/messages
"""

import logging
import requests
from flask import current_app

logger = logging.getLogger(__name__)

GRAPH_URL = "https://graph.facebook.com/v19.0"


def send_text(to: str, body: str) -> bool:
    """Send a plain-text WhatsApp message. Returns True on success."""
    phone_id    = current_app.config.get("WHATSAPP_PHONE_ID", "")
    access_token = current_app.config.get("WHATSAPP_ACCESS_TOKEN", "")

    if not phone_id or not access_token:
        logger.warning("WhatsApp credentials not set — skipping send.")
        return False

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    try:
        resp = requests.post(
            f"{GRAPH_URL}/{phone_id}/messages",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info(f"Sent WhatsApp message to {to}")
        return True
    except requests.RequestException as e:
        logger.error(f"WhatsApp send failed: {e}")
        return False


def build_automated_reply(original_message: str) -> str:
    """
    Placeholder automated reply. In production, replace this with
    your LLM call or FAQ lookup based on the message content.
    """
    return (
        "👋 Thanks for your message! We've received it and will get back to you shortly.\n\n"
        "For urgent matters, please call us directly."
    )


def build_escalation_alert(sender: str, message: str) -> str:
    """Staff alert message for escalated issues."""
    return (
        f"🚨 ESCALATION ALERT\n"
        f"From: {sender}\n"
        f"Message: {message}\n\n"
        f"This message has been flagged as urgent. Please respond immediately."
    )
