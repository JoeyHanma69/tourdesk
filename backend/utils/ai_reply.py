"""
backend/utils/ai_reply.py
=========================
Optional AI-generated replies for the Automated tier, powered by Claude.

This is a *drop-in enhancement*. If AI replies are disabled, no API key is
present, or anything fails, the functions here return None and the caller
(chat.py) falls back to the existing canned reply. The app therefore still
runs with no API key — exactly as before — so nothing breaks in stub mode.

Enable by setting in your .env:
    USE_AI_REPLIES=true
    ANTHROPIC_API_KEY=sk-ant-...
    AI_MODEL=claude-opus-4-8     # optional; this is the default
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── EDIT THESE FACTS to match Turtle Down Under ──────────────────────────────
# Claude answers ONLY from what's written here. Anything not covered is handed
# back to a human, so it can never invent a tour time or policy. Replace the
# placeholders below with your real details.
TDU_FACTS = """\
TOUR FACTS (placeholder — replace with the real Turtle Down Under details):
- Daily tours depart 9:00 AM and 1:00 PM from the Main Street jetty.
- Guests should arrive 15 minutes before departure.
- What to bring: sunscreen, hat, water, towel, and a light jacket.
- Free cancellation up to 24 hours before departure.
- Tours run rain or shine; only cancelled for unsafe sea conditions (full refund).
- Children under 5 travel free; under-16s must be accompanied by an adult.
"""

SYSTEM_PROMPT = (
    "You are the Turtle Down Under guest assistant in a live web chat.\n"
    "Answer using ONLY the facts below. If the answer is not covered, do NOT "
    "guess — say you'll connect the guest with a team member who can help.\n"
    "Keep replies warm and concise (2-3 sentences) and end by inviting any "
    "follow-up questions.\n\n"
    + TDU_FACTS
)

# Module-level client, built once. _init_attempted guards against retrying a
# failed/disabled init on every message.
_client = None
_init_attempted = False


def _truthy(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


def _get_client():
    """Lazily build the Anthropic client.

    Returns None when AI replies are disabled or unavailable — that None is the
    signal for the caller to use the canned reply instead.
    """
    global _client, _init_attempted
    if _init_attempted:
        return _client
    _init_attempted = True

    if not _truthy(os.getenv("USE_AI_REPLIES", "false")):
        return None  # feature flag off — silent, this is the default

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning(
            "USE_AI_REPLIES is on but ANTHROPIC_API_KEY is unset — "
            "using canned replies."
        )
        return None

    try:
        import anthropic  # imported lazily so the package is optional
        _client = anthropic.Anthropic(api_key=api_key)
        logger.info(
            "✅ AI replies enabled (model=%s)",
            os.getenv("AI_MODEL", "claude-opus-4-8"),
        )
    except Exception as e:
        logger.error("Could not initialise Anthropic client: %s", e)
        _client = None
    return _client


def generate_automated_reply(message: str) -> Optional[str]:
    """Return a Claude-generated answer, or None to fall back to the canned reply."""
    client = _get_client()
    if client is None:
        return None

    try:
        resp = client.messages.create(
            model=os.getenv("AI_MODEL", "claude-opus-4-8"),
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": message}],
        )
        text = next((b.text for b in resp.content if b.type == "text"), "").strip()
        return text or None
    except Exception as e:
        # Never show the guest a stack trace — log it and fall back.
        logger.error("AI reply failed, falling back to canned reply: %s", e)
        return None
