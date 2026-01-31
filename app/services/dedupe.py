# app/services/dedupe.py
from typing import List, Dict


def dedupe_messages(messages: List[Dict]) -> List[Dict]:
    """
    Simple dedupe logic:
    - if title exists: key = (source, channel, country, title)
    - otherwise: key = (source, channel, country, translated_text/raw_text)
    Keeps the first occurrence and drops the rest.
    """
    seen = set()
    result: List[Dict] = []

    for msg in messages:
        # Build a stable key using common identity fields
        source = msg.get("source")
        channel = msg.get("channel")
        country = msg.get("country") or ""

        title = (msg.get("title") or "").strip()
        text = (msg.get("translated_text") or msg.get("raw_text") or msg.get("text") or "").strip()

        # Prefer title-based keys when available
        if title:
            key = ("title", source, channel, country, title)
        else:
            key = ("text", source, channel, country, text)

        # Keep the first seen message for each key
        if key in seen:
            continue
        seen.add(key)
        result.append(msg)

    return result
