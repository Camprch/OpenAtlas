# app/services/enrichment.py
from typing import List, Dict, Any, Optional
import json

from openai import OpenAI
from app.config import get_settings


settings = get_settings()
TARGET_LANGUAGE = settings.target_language
client = OpenAI(api_key=settings.openai_api_key)
MODEL_NAME = settings.openai_model
BATCH_SIZE = settings.batch_size

EXPECTED_FIELDS = ["country", "region", "location", "title", "event_type", "source", "timestamp"]


def _empty_enrichment() -> Dict[str, Optional[str]]:
    return {
        "country": None,
        "region": None,
        "location": None,
        "title": None,
        "source": None,
        "timestamp": None,
    }


def _enrich_subbatch(items: List[Dict[str, Any]]) -> List[Dict[str, Optional[str]]]:
    """
    items: [{ "id": int, "text": str }]
    Retourne, dans le même ordre, une liste de dicts avec les champs EXPECTED_FIELDS.
    L’enrichissement est toujours fait en anglais (prompt et extraction).
    Ajoute event_type avec une liste fermée de 10 types d’événements.
    """
    if not items:
        return []

    event_types = [
        "Protest", "Conflict", "Political", "Natural disaster", "Crime",
        "Cyber Attack", "Public health", "Economic", "Security Alert", "Other"
    ]

    header = (
        "You are an OSINT information extraction system.\n"
        "For each message below, produce ONE JSON LINE (JSONL format):\n"
        '{"id": <int>, "country": "...", "region": "...", "location": "...", '
        '"title": "...", "event_type": "...", "source": "...", "timestamp": "..."}\n\n'
        "Rules:\n"
        "- 'id' = identifier provided in input.\n"
        "- 'country' = main impacted country in English (\"Country1\", \"Country2\", ...), or \"\" if uncertain.\n"
        "- 'region' = large area (province, region, etc.) or \"\".\n"
        "- 'location' = city / specific place or \"\".\n"
        f"- 'title' = short sentence (8-18 words) summarizing the event, in {TARGET_LANGUAGE}.\n"
        f"- 'event_type' = one of: {', '.join(event_types)}. Choose the most relevant type for the event.\n"
        "- 'source' = explicit source in the text, else \"\".\n"
        "- 'timestamp' = explicit timestamp in ISO 8601, else \"\".\n"
        "No text outside JSON, no comments.\n\n"
        "Messages:\n"
    )

    body = "\n".join(f"[{it['id']}] {it.get('text','')}" for it in items)
    prompt = header + body

    resp = client.responses.create(
        model=MODEL_NAME,
        input=prompt,
    )

    try:
        raw = resp.output_text
    except AttributeError:
        raw = str(resp)

    lines = [l.strip() for l in raw.splitlines() if l.strip()]

    id_to_index = {int(it["id"]): idx for idx, it in enumerate(items)}
    results: List[Dict[str, Optional[str]]] = [_empty_enrichment() for _ in items]
    seen_ids = set()

    for line in lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict) or "id" not in obj:
            continue
        try:
            obj_id = int(obj["id"])
        except Exception:
            continue
        if obj_id not in id_to_index or obj_id in seen_ids:
            continue

        filtered: Dict[str, Optional[str]] = {}
        for k in EXPECTED_FIELDS:
            v = obj.get(k, "")
            if v is None:
                v = ""
            elif not isinstance(v, str):
                v = str(v)
            filtered[k] = v

        results[id_to_index[obj_id]] = filtered
        seen_ids.add(obj_id)

    return results


def enrich_messages(messages: List[dict]) -> List[dict]:
    """
    Prend une liste de dicts avec 'text' (toujours en anglais !),
    enrichit par batchs successifs. L’enrichissement est toujours fait en anglais.
    """
    if not messages:
        return messages

    total = len(messages)
    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        sub = messages[start:end]

        items = [
            {"id": i, "text": (m.get("text") or "")}
            for i, m in enumerate(sub)
        ]

        enrichments = _enrich_subbatch(items)


        for msg, enr in zip(sub, enrichments):
            if enr:
                msg["country"] = enr.get("country") or None
                msg["region"] = enr.get("region") or None
                msg["location"] = enr.get("location") or None
                msg["title"] = enr.get("title") or None
                msg["event_type"] = enr.get("event_type") or None

    return messages
