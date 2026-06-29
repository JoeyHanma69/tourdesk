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


def add_message(sender: str, text: str, prediction) -> dict:
    """Save a classified message and return the stored record."""
    record = {
        "id":         len(_messages) + 1,
        "timestamp":  datetime.now().isoformat(),
        "sender":     sender,
        "text":       text,
        "label":      prediction.label,
        "confidence": prediction.confidence,
        "uncertain":  prediction.uncertain,
        "all_scores": prediction.all_scores,
    }
    with _lock:
        _messages.appendleft(record)   # newest first
    return record


def get_all() -> list:
    with _lock:
        return list(_messages)


def get_stats() -> dict:
    with _lock:
        msgs = list(_messages)

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
