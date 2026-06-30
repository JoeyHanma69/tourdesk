"""
backend/utils/booking_store.py
==============================
Sample booking data + a *verified* lookup.

Inspired by how trading apps (e.g. Kraken) gate account actions: the bot never
reveals booking details until the guest proves who they are. Here the identity
check is lightweight — the full name on the booking must appear in the guest's
message — but the principle is the real lesson: verify before you reveal, and
never confirm whether a reference exists to someone who can't name the booking.

This is an in-memory stand-in. In production, replace BOOKINGS / _get() with a
query against your real booking database.
"""

import re
from typing import Optional

# ── Sample bookings (replace with your real data source) ─────────────────────
BOOKINGS = {
    "TDU1001": {
        "name": "Jordan Smith", "tour": "Turtle Snorkel Tour",
        "date": "2026-07-04", "time": "9:00 AM", "guests": 2, "status": "Confirmed",
    },
    "TDU1002": {
        "name": "Priya Patel", "tour": "Sunset Reef Cruise",
        "date": "2026-07-05", "time": "1:00 PM", "guests": 4, "status": "Confirmed",
    },
    "TDU1003": {
        "name": "Liam O'Brien", "tour": "Turtle Snorkel Tour",
        "date": "2026-07-06", "time": "9:00 AM", "guests": 1, "status": "Pending payment",
    },
}

# Matches references like "TDU1001", "tdu 1001", "TDU-1001".
_REFERENCE_RE = re.compile(r"\bTDU[\s-]?(\d{3,5})\b", re.IGNORECASE)


def find_reference(text: str) -> Optional[str]:
    """Return a normalised booking reference found in the text, or None."""
    match = _REFERENCE_RE.search(text or "")
    return f"TDU{match.group(1)}" if match else None


def _get(reference: str) -> Optional[dict]:
    return BOOKINGS.get((reference or "").upper())


def reference_exists(reference: str) -> bool:
    return _get(reference) is not None


def lookup_booking(reference: str, message: str) -> Optional[dict]:
    """Return the booking ONLY if the guest's message also contains the full
    name on it (the identity check). Returns None if the booking doesn't exist
    OR the name wasn't provided — the caller must not distinguish the two, so we
    don't leak whether a reference is real to someone who can't verify it.
    """
    booking = _get(reference)
    if not booking:
        return None

    text = (message or "").lower()
    name_tokens = booking["name"].lower().split()
    # Every part of the name must appear in the message.
    if all(token in text for token in name_tokens):
        return booking
    return None
