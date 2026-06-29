"""
backend/utils/chat.py
=====================
Reply helpers for the TourDesk web chatbot.

Replies are returned straight back to the browser chat widget — there is no
external messaging provider. Each helper builds the text the guest sees based
on the classifier's predicted tier.
"""


WELCOME_MESSAGE = (
    "👋 Hi, welcome to Turtle Down Under! I'm the TourDesk assistant. "
    "Ask me anything about your tour — times, locations, bookings, or anything else."
)


def build_automated_reply(original_message: str) -> str:
    """
    Reply for routine ('Automated') questions. In production, replace this with
    your LLM call or FAQ lookup based on the message content.
    """
    return (
        "👋 Thanks for your message! We've got the details you need on the way.\n\n"
        "If anything's still unclear, just let me know and I'll connect you with our team."
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
