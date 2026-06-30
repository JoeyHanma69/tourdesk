"""
backend/utils/ai_reply.py
=========================
Optional AI-generated replies for the Automated tier.

This is a *drop-in enhancement*. If AI replies are disabled, the provider is
unavailable, or anything fails, the functions here return None and the caller
(chat.py) falls back to the existing canned reply. The app therefore still
runs with no AI at all — exactly as before — so nothing breaks in stub mode.

The rest of the app only ever calls generate_automated_reply(message); the
provider behind it is chosen by the AI_PROVIDER env var, so you can switch
between Claude (cloud) and Ollama (local, free) by editing .env — no code change.

Enable in your .env:
    USE_AI_REPLIES=true
    AI_PROVIDER=ollama          # "ollama" (local) or "anthropic" (Claude)

  For Ollama (local, no API key):
    OLLAMA_MODEL=llama3.2       # any model you've pulled with `ollama pull`
    OLLAMA_HOST=http://localhost:11434   # optional; this is the default

  For Anthropic (Claude):
    ANTHROPIC_API_KEY=sk-ant-...
    AI_MODEL=claude-opus-4-8
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── EDIT THESE FACTS to match Turtle Down Under ──────────────────────────────
# The model answers ONLY from what's written here. Anything not covered is
# handed back to a human, so it can never invent a tour time or policy.
# Replace the placeholders below with your real details.
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
    "\n"
    "RULES:\n"
    "- Answer using ONLY the facts below. Never invent times, prices, or policies.\n"
    "- If the answer is not in the facts, say briefly that you'll connect the guest "
    "with a team member — do not guess and do not apologise repeatedly.\n"
    "- Be warm and concise: 2-3 sentences, no preamble like 'Thanks for your "
    "message'. Answer the question directly, then invite any follow-up.\n"
    "- Plain, friendly English. No markdown, no bullet points, no emoji.\n"
    "\n"
    "EXAMPLE\n"
    "Guest: what time do tours leave?\n"
    "You: Our tours depart daily at 9:00 AM and 1:00 PM from the Main Street "
    "jetty — try to arrive about 15 minutes early. Anything else I can help with?\n"
    "\n"
    + TDU_FACTS
)

# Clients are built once and memoized. None means "unavailable — use fallback".
_clients = {}
_attempted = set()


def _truthy(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


def _enabled() -> bool:
    return _truthy(os.getenv("USE_AI_REPLIES", "false"))


def _provider() -> str:
    return os.getenv("AI_PROVIDER", "anthropic").strip().lower()


# ── Provider: Ollama (local, free, no API key) ───────────────────────────────
def _ollama_reply(message: str) -> Optional[str]:
    client = _get_ollama_client()
    if client is None:
        return None
    try:
        resp = client.chat(
            model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            # Quality + speed tuning. Lower temperature = factual, consistent
            # answers (less drift); num_predict caps length so replies stay short
            # and fast; num_ctx gives room for the facts + question.
            options={
                "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.3")),
                "top_p": 0.9,
                "num_predict": int(os.getenv("OLLAMA_MAX_TOKENS", "300")),
                "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "4096")),
            },
            # Keep the model loaded in RAM between messages so the next guest
            # doesn't wait for a cold reload. Set "0" to unload immediately.
            keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "10m"),
        )
        return (resp["message"]["content"] or "").strip() or None
    except Exception as e:
        logger.error("Ollama reply failed, falling back to canned reply: %s", e)
        return None


def _get_ollama_client():
    if "ollama" in _attempted:
        return _clients.get("ollama")
    _attempted.add("ollama")
    try:
        import ollama  # imported lazily so the package is optional
        client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
        _clients["ollama"] = client
        logger.info(
            "✅ AI replies enabled via Ollama (model=%s)",
            os.getenv("OLLAMA_MODEL", "llama3.2"),
        )
    except Exception as e:
        logger.error("Could not initialise Ollama client: %s", e)
        _clients["ollama"] = None
    return _clients.get("ollama")


# ── Provider: Anthropic (Claude, cloud) ──────────────────────────────────────
def _anthropic_reply(message: str) -> Optional[str]:
    client = _get_anthropic_client()
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
        logger.error("Claude reply failed, falling back to canned reply: %s", e)
        return None


def _get_anthropic_client():
    if "anthropic" in _attempted:
        return _clients.get("anthropic")
    _attempted.add("anthropic")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning(
            "AI_PROVIDER=anthropic but ANTHROPIC_API_KEY is unset — "
            "using canned replies."
        )
        _clients["anthropic"] = None
        return None
    try:
        import anthropic  # imported lazily so the package is optional
        _clients["anthropic"] = anthropic.Anthropic(api_key=api_key)
        logger.info(
            "✅ AI replies enabled via Claude (model=%s)",
            os.getenv("AI_MODEL", "claude-opus-4-8"),
        )
    except Exception as e:
        logger.error("Could not initialise Anthropic client: %s", e)
        _clients["anthropic"] = None
    return _clients.get("anthropic")


# ── Public entry point ───────────────────────────────────────────────────────
_PROVIDERS = {
    "ollama": _ollama_reply,
    "anthropic": _anthropic_reply,
}


def generate_automated_reply(message: str) -> Optional[str]:
    """Return an AI-generated answer, or None to fall back to the canned reply.

    The provider is selected by AI_PROVIDER. Any unknown provider, a disabled
    flag, or a failure returns None — so the caller always has a safe fallback.
    """
    if not _enabled():
        return None

    handler = _PROVIDERS.get(_provider())
    if handler is None:
        logger.warning(
            "Unknown AI_PROVIDER=%r — expected one of %s. Using canned replies.",
            _provider(),
            ", ".join(_PROVIDERS),
        )
        return None

    return handler(message)
