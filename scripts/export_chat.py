"""
export_chat.py — WhatsApp Chat Export Parser
============================================
Converts a raw WhatsApp .txt export into a clean CSV of inbound guest messages.

Usage:
    python scripts/export_chat.py --input chat.txt --output messages.csv

Output CSV columns:
    timestamp, sender, text
"""

import argparse
import csv
import re
import sys
from pathlib import Path

# WhatsApp export line format (supports both 12h and 24h, with or without seconds)
# Examples:
#   [12/01/2024, 9:45 AM] Joey: Hello there
#   12/01/2024, 09:45 - Joey: Hello there
PATTERN = re.compile(
    r"[\[]*(\d{1,2}/\d{1,2}/\d{2,4}),?\s+"   # date
    r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?)"  # time
    r"[\] -]+?"                                  # separator
    r"([^:]+):\s+"                               # sender
    r"(.+)"                                      # message text
)

SKIP_PATTERNS = [
    "omitted",           # "<Media omitted>"
    "end-to-end",        # encryption notice
    "security code",     # security notices
    "joined using",      # group join messages
    "left",              # group leave messages
    "added",             # group add messages
    "created group",
    "changed the group",
    "changed this group",
    "your security code",
    "messages and calls are end-to-end encrypted",
]


def should_skip(text: str) -> bool:
    text_lower = text.lower()
    return any(p in text_lower for p in SKIP_PATTERNS)


def parse_chat(filepath: str) -> list[dict]:
    messages = []
    current = None

    with open(filepath, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            match = PATTERN.match(line)
            if match:
                # Save previous message
                if current and not should_skip(current["text"]):
                    messages.append(current)

                date, time, sender, text = match.groups()
                current = {
                    "timestamp": f"{date} {time}",
                    "sender":    sender.strip(),
                    "text":      text.strip(),
                }
            elif current:
                # Continuation of previous message (multi-line)
                current["text"] += " " + line

    # Don't forget the last message
    if current and not should_skip(current["text"]):
        messages.append(current)

    return messages


def main():
    parser = argparse.ArgumentParser(description="Parse WhatsApp chat export to CSV")
    parser.add_argument("--input",  required=True, help="Path to WhatsApp .txt export file")
    parser.add_argument("--output", required=True, help="Output CSV file path")
    parser.add_argument(
        "--sender-filter",
        help="Only include messages from this sender (optional). "
             "Leave blank to include all senders."
    )
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"❌  Input file not found: {args.input}")
        sys.exit(1)

    print(f"Parsing: {args.input}")
    messages = parse_chat(args.input)
    print(f"Found {len(messages)} messages total")

    if args.sender_filter:
        messages = [m for m in messages if args.sender_filter.lower() in m["sender"].lower()]
        print(f"Filtered to {len(messages)} messages from '{args.sender_filter}'")

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "sender", "text"])
        writer.writeheader()
        writer.writerows(messages)

    print(f"✅  Saved to: {args.output}")


if __name__ == "__main__":
    main()
