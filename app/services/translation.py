# app/services/translation.py
from typing import List
from openai import OpenAI

from app.config import get_settings


settings = get_settings()
TARGET_LANGUAGE = settings.target_language
client = OpenAI(api_key=settings.openai_api_key)
MODEL_NAME = settings.openai_model
# Nombre de messages par appel OpenAI
BATCH_SIZE = settings.batch_size


def _translate_subbatch(texts: List[str]) -> List[str]:
    """
    Traduit un sous-batch de messages depuis l’anglais vers la langue cible (settings.target_language).
    Texte => texte, même ordre.
    """
    if not texts:
        return []

    # Prompt dynamique selon la langue cible
    lang = TARGET_LANGUAGE
    if lang.lower() == "fr":
        lang_label = "français naturel"
    elif lang.lower() == "es":
        lang_label = "espagnol naturel"
    elif lang.lower() == "de":
        lang_label = "allemand naturel"
    else:
        lang_label = f"{lang}"

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

    # fallback si certains indices sont vides => on remet le texte d’origine
    for i, t in enumerate(translations):
        if not t:
            translations[i] = texts[i]

    return translations


def translate_messages(messages: List[dict]) -> List[dict]:
    """
    Prend une liste de dicts avec au moins 'text',
    ajoute 'translated_text' en batchs successifs.
    Modifie la liste en place et la renvoie.
    """
    if not messages:
        return messages

    total = len(messages)
    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        sub = messages[start:end]
        texts = [m.get("text", "") for m in sub]

        translations = _translate_subbatch(texts)

        for msg, trans in zip(sub, translations):
            msg["translated_text"] = trans

    return messages
