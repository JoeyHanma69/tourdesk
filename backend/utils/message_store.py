"""
backend/utils/message_store.py
================================
Simple in-memory store for messages received during the session.
Resets on server restart. Replace with a database (SQLite/PostgreSQL) for production.
"""

from datetime import datetime
from collections import deque
import threading

_lock = threading.Lock()

# Stores last 500 messages in memory
_messages = deque(maxlen=500)

# Monotonically increasing id, independent of the deque's length so ids stay
# unique even after old messages fall off the 500-message window (the poll
# endpoint relies on ids only ever increasing).
_next_id = 1


def _alloc_id() -> int:
    global _next_id
    id_ = _next_id
    _next_id += 1
    return id_


def add_message(sender: str, text: str, prediction, attachment=None) -> dict:
    """Save a classified guest message and return the stored record."""
    with _lock:
        record = {
            "id":         _alloc_id(),
            "timestamp":  datetime.now().isoformat(),
            "sender":     sender,
            "text":       text,
            "label":      prediction.label,
            "confidence": prediction.confidence,
            "uncertain":  prediction.uncertain,
            "all_scores": prediction.all_scores,
            "from_staff": False,
            "attachment": attachment,
        }
        _messages.appendleft(record)   # newest first
    return record


def add_staff_reply(session_id: str, text: str, attachment=None) -> dict:
    """Save a staff reply addressed to a specific guest session (sent from
    the dashboard). Picked up by the guest chat widget's poll loop."""
    with _lock:
        record = {
            "id":         _alloc_id(),
            "timestamp":  datetime.now().isoformat(),
            "sender":     session_id,
            "text":       text,
            "label":      None,
            "confidence": None,
            "uncertain":  False,
            "all_scores": None,
            "from_staff": True,
            "attachment": attachment,
        }
        _messages.appendleft(record)
    return record


def get_all() -> list:
    with _lock:
        return list(_messages)


def get_staff_replies_since(session_id: str, since_id: int) -> list:
    """New staff replies for a guest session, oldest first — used by the
    guest chat widget to pick up replies sent from the dashboard."""
    with _lock:
        msgs = list(_messages)
    replies = [
        m for m in msgs
        if m["sender"] == session_id and m["from_staff"] and m["id"] > since_id
    ]
    replies.sort(key=lambda m: m["id"])
    return replies


def get_stats() -> dict:
    with _lock:
        msgs = [m for m in _messages if not m["from_staff"]]

    total = len(msgs)
    if total == 0:
        return {"total": 0, "Automated": 0, "Assisted": 0, "Escalate": 0, "uncertain": 0}

    counts = {"Automated": 0, "Assisted": 0, "Escalate": 0}
    uncertain = 0
    for m in msgs:
        counts[m["label"]] = counts.get(m["label"], 0) + 1
        if m["uncertain"]:
            uncertain += 1

    return {
        "total":     total,
        "uncertain": uncertain,
        **counts,
    }
