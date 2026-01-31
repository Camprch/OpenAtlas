# app/services/translation.py
from typing import List
from openai import OpenAI

from app.config import get_settings


# Load settings for translation
settings = get_settings()
TARGET_LANGUAGE = settings.target_language
client = OpenAI(api_key=settings.openai_api_key)
MODEL_NAME = settings.openai_model
# Number of messages per OpenAI call
BATCH_SIZE = settings.batch_size


def _translate_subbatch(texts: List[str]) -> List[str]:
    """
    Translate a sub-batch of messages from English to the target language.
    Input texts map to output translations in the same order.
    """
    if not texts:
        return []

    # Pick a human-readable label for the target language
    lang = TARGET_LANGUAGE
    if lang.lower() == "fr":
        lang_label = "français naturel"
    elif lang.lower() == "es":
        lang_label = "espagnol naturel"
    elif lang.lower() == "de":
        lang_label = "allemand naturel"
    else:
        lang_label = f"{lang}"

    # Build a JSONL-only translation prompt
    header = (
        f"You are a professional translator.\n"
        f"I will give you a list of numbered messages in English.\n"
        f"For each message, reply STRICTLY in JSON Lines format:\n"
        f'{{"index": <int>, "translation": "<translated text>"}}\n'
        f"One JSON object per line, same order as the indexes.\n"
        f"No text outside JSON, no comments.\n"
        f"IMPORTANT: Translate each message into {lang_label}, even if the original text is already in that language or another.\n"
        f"If a message contains proper names, hashtags, specific expressions, or untranslatable elements, keep them as is and put them in quotes in the translation.\n"
        f"Messages:\n"
    )

    body_lines = []
    for i, txt in enumerate(texts):
        body_lines.append(f"[{i}] {txt}")
    prompt = header + "\n".join(body_lines)

    # Call the OpenAI Responses API for translation
    resp = client.responses.create(
        model=MODEL_NAME,
        input=prompt,
    )

    try:
        raw = resp.output_text
    except AttributeError:
        raw = str(resp)

    import json
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    translations = [""] * len(texts)

    # Parse JSONL lines and map translations back by index
    for line in lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        if "index" not in obj or "translation" not in obj:
            continue
        idx = obj["index"]
        if not isinstance(idx, int):
            continue
        if 0 <= idx < len(texts):
            translations[idx] = str(obj["translation"])

    # Fallback: keep original text when a translation is missing
    for i, t in enumerate(translations):
        if not t:
            translations[i] = texts[i]

    return translations


def translate_messages(messages: List[dict]) -> List[dict]:
    """
    Takes a list of dicts with at least 'text',
    adds 'translated_text' in successive batches.
    Mutates the list in place and returns it.
    """
    if not messages:
        return messages

    total = len(messages)
    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        sub = messages[start:end]
        texts = [m.get("text", "") for m in sub]

        # Log progress per batch to surface translation activity
        print(f"[pipeline] [TRAD] batch {start + 1}-{end} / {total}")
        # Translate each batch to reduce API calls
        translations = _translate_subbatch(texts)

        for msg, trans in zip(sub, translations):
            msg["translated_text"] = trans

    return messages
