"""
backend/utils/chat.py
=====================
Reply helpers for the TourDesk web chatbot.

Replies are returned straight back to the browser chat widget — there is no
external messaging provider. Each helper builds the text the guest sees based
on the classifier's predicted tier.
"""

from typing import Optional

from backend.utils.ai_reply import generate_automated_reply
from backend.utils.booking_store import find_reference, lookup_booking


WELCOME_MESSAGE = (
    "👋 Hi, welcome to Turtle Down Under! I'm the TourDesk assistant. "
    "Ask me anything about your tour — times, locations, bookings, or anything else."
)

# ── Safety net ───────────────────────────────────────────────────────────────
# Deterministic override for urgent / safety-critical messages. The ML model
# misses some of these (its Escalate recall is ~0.69), and you should never rely
# on a model alone for safety — so any message containing one of these phrases is
# forced to the Escalate tier regardless of what the classifier predicted.
URGENT_KEYWORDS = (
    "injured", "injury", "hurt", "bleeding", "blood", "wound",
    "emergency", "accident", "ambulance", "paramedic", "hospital",
    "drowning", "drown", "can't breathe", "cant breathe", "choking",
    "unconscious", "collapsed", "heart attack", "stroke", "seizure",
    "allergic", "anaphylaxis", "overdose", "stung", "bitten", "snake",
    "stranded", "lost at sea", "sinking", "capsized", "overboard",
    "danger", "dangerous", "urgent", "help me", "rescue", "missing",
)


def is_urgent(message: str) -> bool:
    """True if the message contains a safety/emergency phrase."""
    text = (message or "").lower()
    return any(keyword in text for keyword in URGENT_KEYWORDS)


def get_command_reply(message: str) -> Optional[str]:
    """Handle simple slash commands before the normal classifier flow."""
    text = (message or "").strip()
    if not text.startswith("/"):
        return None

    command = text.lower()
    if command == "/waifu":
        return (
            "✨ Here’s a playful waifu-style reply: "
            "You bring warmth and charm to this chat, and I’m happy to keep you company."
        )
    return None


def build_automated_reply(original_message: str) -> str:
    """
    Reply for routine ('Automated') questions.

    Tries Claude first (when USE_AI_REPLIES is on) so the guest gets a real
    answer; if AI replies are disabled or the call fails, falls back to the
    canned message below — so this always returns something sensible.
    """
    ai = generate_automated_reply(original_message)
    if ai:
        return ai

    return (
        "👋 Thanks for your message! We've got the details you need on the way.\n\n"
        "If anything's still unclear, just let me know and I'll connect you with our team."
    )


def build_booking_reply(message: str) -> Optional[str]:
    """Handle booking-status questions with a verify-before-reveal gate.

    Returns None when the message has no booking reference, so the normal
    tier-based reply flow continues. When a reference IS present:
      - name verified  -> return the booking details
      - not verified    -> ask for the name (never reveal whether the
                           reference exists, to anyone who can't name it)
    """
    reference = find_reference(message)
    if not reference:
        return None  # not a booking enquiry

    booking = lookup_booking(reference, message)
    if booking:
        return (
            f"Thanks — I've verified booking {reference}. "
            f"Your {booking['tour']} is {booking['status'].lower()} for "
            f"{booking['guests']} guest(s) on {booking['date']} at {booking['time']}. "
            "Is there anything else I can help with? "
            "(To change or cancel it, I'll connect you with our team.)"
        )

    # Reference detected but identity not verified — ask for the name. We do not
    # say whether the reference exists; that's the security gate.
    return (
        f"I can help with booking {reference}. To protect your reservation, "
        "please reply with the full name on the booking so I can verify it's you."
    )


def build_assisted_reply(original_message: str) -> str:
    """Reply for requests that need staff personalisation ('Assisted')."""
    return (
        "Thanks! I've passed this to our team so they can sort out the details for you. "
        "Someone will follow up shortly right here in the chat."
    )


def build_escalation_reply(original_message: str) -> str:
    """Reply for urgent / safety-critical situations ('Escalate')."""
    return (
        "🚨 I've flagged this as urgent and alerted our team right away. "
        "If this is an emergency, please call us directly on the number in your booking confirmation."
    )


def build_uncertain_reply(original_message: str) -> str:
    """Reply when the classifier is not confident — always routed to a human."""
    return (
        "Thanks for reaching out! I want to make sure you get the right answer, "
        "so I'm connecting you with a member of our team now."
    )


def build_staff_note(sender: str, message: str) -> str:
    """Internal note logged when a message is escalated for staff attention."""
    return (
        f"🚨 ESCALATION\n"
        f"From: {sender}\n"
        f"Message: {message}\n\n"
        f"Flagged as urgent — please respond in the dashboard."
    )
