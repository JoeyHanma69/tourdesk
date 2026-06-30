#!/usr/bin/env python
"""
tools/chat_test.py — TourDesk AI internal test harness  (standalone, zero UI)
============================================================================
Type a guest message, see the AI's decision and the reply it would send.
No Flask, no browser, no server. Purely to validate the decision logic.

It runs the SAME logic as the live chatbot by importing
backend.utils.pipeline.decide(), so what you see here is exactly what a guest
would get — there is no second copy of the logic to drift out of sync.

This file is separate from the web app: nothing in the app imports it, and you
can move or delete it freely.

USAGE (run from the project root):
    python tools/chat_test.py                  # interactive REPL
    python tools/chat_test.py "your message"   # one-shot
    python tools/chat_test.py --samples        # run a built-in test set

It works WITHOUT the trained model (stub mode) — the model-based tier won't be
meaningful, but the safety net, booking gate, confidence and reply logic all
validate. Download the model for full classification.
"""

import os
import sys


def _find_project_root() -> str:
    """Locate the tourdesk project so this script can live ANYWHERE.

    Resolution order:
      1. TOURDESK_ROOT env var (set this if you keep the script outside the repo)
      2. walk up from this file looking for a backend/utils folder (inside repo)
      3. fall back to the parent directory
    """
    env = os.getenv("TOURDESK_ROOT")
    if env and os.path.isdir(os.path.join(env, "backend", "utils")):
        return env

    here = os.path.dirname(os.path.abspath(__file__))
    d = here
    for _ in range(8):
        if os.path.isdir(os.path.join(d, "backend", "utils")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.path.dirname(here)


# Make the project importable no matter where this script is placed.
_PROJECT_ROOT = _find_project_root()
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Load .env if python-dotenv is available (for MODEL_DIR, USE_AI_REPLIES, etc.)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))
except Exception:
    pass

from backend.utils.classifier import TourDeskClassifier
from backend.utils.pipeline import decide


SAMPLES = [
    "What time does the tour start tomorrow?",
    "Where do we meet for the day trip?",
    "Can we change our pickup location to the hotel?",
    "is my booking TDU1001 confirmed? this is Jordan Smith",
    "is TDU1001 confirmed?",
    "There's been an accident and someone is hurt!",
    "and also, i have been injured",
    "I lost my passport and I don't know what to do",
]


def load_classifier() -> TourDeskClassifier:
    model_dir = os.getenv("MODEL_DIR", "ml_classifier/model")
    threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.65"))
    return TourDeskClassifier(model_dir=model_dir, threshold=threshold)


def show(clf: TourDeskClassifier, text: str) -> None:
    prediction = clf.predict(text)
    d = decide(prediction, text)

    print("\n" + "=" * 66)
    print(f"  MESSAGE : {text}")
    print("-" * 66)
    print(f"  model tier   : {d.raw_label}   ({d.confidence:.0%} confidence)")
    if d.all_scores:
        scores = "   ".join(f"{k} {v * 100:.0f}%" for k, v in d.all_scores.items())
        print(f"  all scores   : {scores}")

    flags = []
    if d.urgent_override:
        flags.append("URGENT keyword -> forced Escalate")
    if d.uncertain:
        flags.append("low confidence -> human review")
    if d.booking_matched:
        flags.append("booking lookup matched")
    print(f"  flags        : {', '.join(flags) if flags else 'none'}")
    print(f"  FINAL tier   : {d.final_label}")
    print("-" * 66)
    print("  REPLY TO GUEST:")
    for line in d.reply.splitlines() or [""]:
        print(f"    {line}")
    print("=" * 66)


def main() -> None:
    args = sys.argv[1:]
    print("Loading classifier (first load can take a moment)...")
    clf = load_classifier()
    mode = "MODEL loaded" if clf.is_ready else "STUB MODE (no model — tier is placeholder)"
    print(f"Ready — {mode}\n")

    if args and args[0] == "--samples":
        for m in SAMPLES:
            show(clf, m)
        return
    if args:
        show(clf, " ".join(args))
        return

    print("Type a guest message and press Enter.  ('quit' or Ctrl-C to exit)")
    try:
        while True:
            text = input("\nguest> ").strip()
            if text.lower() in ("quit", "exit", "q"):
                break
            if text:
                show(clf, text)
    except (KeyboardInterrupt, EOFError):
        print("\nbye")


if __name__ == "__main__":
    main()