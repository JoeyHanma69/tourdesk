"""
backend/utils/pipeline.py
=========================
The message-handling decision as ONE pure function, so the logic can be
validated without Flask, a browser, or a network call.

Both the live web route (routes/chat.py) and the CLI test harness
(scripts/chat_test.py) call decide() — so whatever you validate in the harness
is exactly what runs in production. No drift.

decide() takes a classifier Prediction + the message text and returns a
Decision describing every step: what the model said, whether the safety net or
confidence threshold changed the outcome, whether a booking matched, the final
tier, and the reply the guest would receive.
"""

from dataclasses import dataclass
from typing import Optional

from backend.utils.chat import (
    is_urgent,
    build_booking_reply,
    build_automated_reply,
    build_assisted_reply,
    build_escalation_reply,
    build_uncertain_reply,
)


@dataclass
class Decision:
    text: str
    raw_label: str          # what the model predicted
    final_label: str        # tier after the safety-net override
    confidence: float
    uncertain: bool         # below confidence threshold -> human review
    urgent_override: bool   # safety net forced Escalate
    booking_matched: bool   # a verified booking reply was produced
    all_scores: dict
    reply: str              # the text the guest would receive


def decide(prediction, text: str) -> Decision:
    """Run the full handling decision for one message. Pure: no I/O, no logging."""
    raw_label = prediction.label
    final_label = prediction.label
    uncertain = prediction.uncertain

    # 1. Safety net — urgent keywords force Escalate regardless of the model.
    urgent_override = is_urgent(text)
    if urgent_override:
        final_label = "Escalate"
        uncertain = False

    # 2. Booking enquiries are answered first (with the verify-before-reveal
    #    gate). NOTE: this currently takes precedence even over an escalation.
    booking_reply = build_booking_reply(text)
    booking_matched = booking_reply is not None

    # 3. Build the reply for the resolved state.
    if booking_reply is not None:
        reply = booking_reply
    elif uncertain:
        reply = build_uncertain_reply(text)
    elif final_label == "Automated":
        reply = build_automated_reply(text)
    elif final_label == "Assisted":
        reply = build_assisted_reply(text)
    elif final_label == "Escalate":
        reply = build_escalation_reply(text)
    else:  # unexpected label — safe default
        reply = build_automated_reply(text)

    return Decision(
        text=text,
        raw_label=raw_label,
        final_label=final_label,
        confidence=prediction.confidence,
        uncertain=uncertain,
        urgent_override=urgent_override,
        booking_matched=booking_matched,
        all_scores=getattr(prediction, "all_scores", {}) or {},
        reply=reply,
    )
