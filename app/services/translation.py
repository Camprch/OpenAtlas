# app/services/translation.py
from typing import Dict, List, Optional, Tuple

from app.config import get_settings
from app.services.enrichment import normalize_text


def detect_language(text: str) -> str | None:
    """
    Lightweight language detection wrapper.
    Returns a language code or None if undetected.
    """
    try:
        from langdetect import detect
    except Exception:
        return None
    try:
        return detect(text)
    except Exception:
        return None


def _get_openai_client(api_key: Optional[str]):
    from openai import OpenAI
    return OpenAI(api_key=api_key)


def _lang_label(lang: Optional[str]) -> str:
    if not lang:
        return "unknown (auto-detect)"
    lang_lower = lang.lower()
    if lang_lower == "fr":
        return "français naturel"
    if lang_lower == "es":
        return "espagnol naturel"
    if lang_lower == "de":
        return "allemand naturel"
    if lang_lower == "en":
        return "english"
    if lang_lower == "ru":
        return "russian"
    return lang


def _translate_subbatch(
    texts: List[str],
    *,
    source_lang: Optional[str],
    target_lang: str,
    model_name: str,
    api_key: Optional[str],
    ai_client: Optional[object] = None,
) -> List[str]:
    """
    Translate a sub-batch of messages from source language to the target language.
    Input texts map to output translations in the same order.
    """
    if not texts:
        return []

    source_label = _lang_label(source_lang)
    target_label = _lang_label(target_lang)

    # Build a JSONL-only translation prompt
    header = (
        f"You are a professional translator.\n"
        f"I will give you a list of numbered messages in {source_label}.\n"
        f"For each message, reply STRICTLY in JSON Lines format:\n"
        f'{{"index": <int>, "translation": "<translated text>"}}\n'
        f"One JSON object per line, same order as the indexes.\n"
        f"No text outside JSON, no comments.\n"
        f"IMPORTANT: Translate each message from {source_label} to {target_label}.\n"
        f"If a message contains proper names, hashtags, specific expressions, or untranslatable elements, keep them as is and put them in quotes in the translation.\n"
        f"Messages:\n"
    )

    body_lines = []
    for i, txt in enumerate(texts):
        body_lines.append(f"[{i}] {txt}")
    prompt = header + "\n".join(body_lines)

    # Call the OpenAI Responses API for translation
    client = ai_client or _get_openai_client(api_key)
    resp = client.responses.create(
        model=model_name,
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


def translate_messages(
    messages: List[dict],
    *,
    target_language: Optional[str] = None,
    ai_client: Optional[object] = None,
) -> List[dict]:
    """
    Takes a list of dicts with at least 'text',
    adds 'translated_text' in successive batches.
    Mutates the list in place and returns it.
    """
    if not messages:
        return messages

    settings = get_settings()
    target_lang = (target_language or settings.target_language or "").lower()
    if not target_lang:
        target_lang = "fr"

    print(f"[pipeline] [TRAD] batch_size={settings.batch_size}")
    if ai_client is None and (not settings.openai_api_key or not settings.openai_model):
        for msg in messages:
            msg["translated_text"] = msg.get("text", "")
        return messages

    has_text = any((msg.get("text") or "").strip() for msg in messages)
    if not has_text:
        for msg in messages:
            msg["translated_text"] = msg.get("text", "")
        print("[pipeline] [TRAD] Translation skipped: no translatable fields required")
        return messages

    groups: Dict[str, List[Tuple[int, str, Optional[str]]]] = {}
    for idx, msg in enumerate(messages):
        text = msg.get("text", "") or ""
        source_lang = detect_language(text)
        if not source_lang:
            msg["translated_text"] = text
            print("[pipeline] [TRAD] Translation skipped: missing source_lang")
            continue
        source_lang_code = source_lang.lower()
        if source_lang_code == target_lang:
            msg["translated_text"] = text
            print("[pipeline] [TRAD] Translation skipped: source_lang == target_lang")
            continue
        groups.setdefault(source_lang_code, []).append((idx, text, source_lang))

    if not groups:
        print("[pipeline] [TRAD] Translation skipped: no translatable fields required")
        return messages

    batch_size = settings.batch_size
    total = len(messages)
    print(f"[pipeline] [TRAD] batch_size={batch_size} | total={total} | groups={len(groups)}")
    for source_lang_code, items in groups.items():
        for start in range(0, len(items), batch_size):
            batch = items[start:start + batch_size]
            indices = [i for i, _text, _lang in batch]
            texts = [text for _i, text, _lang in batch]
            source_lang = batch[0][2]

            print(
                f"[pipeline] [TRAD] batch {start + 1}-{min(start + batch_size, len(items))} / {total} "
                f"(size={len(batch)} | lang={source_lang or source_lang_code})"
            )
            translations = _translate_subbatch(
                texts,
                source_lang=source_lang or source_lang_code,
                target_lang=target_lang,
                model_name=settings.openai_model,
                api_key=settings.openai_api_key,
                ai_client=ai_client,
            )

            for idx, trans in zip(indices, translations):
                messages[idx]["translated_text"] = trans
            print(
                f"[pipeline] [TRAD] batch done {start + 1}-{min(start + batch_size, len(items))} / {total} "
                f"(size={len(batch)} | lang={source_lang or source_lang_code})"
            )

    return messages
