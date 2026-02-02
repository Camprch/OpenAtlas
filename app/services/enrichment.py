# app/services/enrichment.py
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import re
import unicodedata

from app.config import get_settings
try:
    import pycountry
except Exception:  # pragma: no cover - optional dependency at runtime
    pycountry = None


AI_FIELDS: List[str] = ["country", "region", "location", "title"]


def normalize_text(text: str) -> str:
    """
    Normalize text deterministically for parsing and caching.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text))
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text



@lru_cache(maxsize=1)
def _load_country_data() -> tuple[Dict[str, str], Dict[str, List[float]]]:
    base_dir = Path(__file__).resolve().parents[2]
    countries_path = base_dir / "static" / "data" / "countries.json"
    data = json.loads(countries_path.read_text(encoding="utf-8"))
    aliases = data.get("aliases", {})
    coords = data.get("coordinates", {})
    return aliases, coords


def _strip_emoji_prefix(value: str) -> str:
    value = re.sub(r"^[^A-Za-z0-9]+\s*", "", value)
    return value.strip()


def _alias_matches(text_lower: str, alias: str) -> Optional[int]:
    pattern = r"(?<!\w)" + re.escape(alias) + r"(?!\w)"
    match = re.search(pattern, text_lower)
    if not match:
        return None
    return match.start()


@lru_cache(maxsize=1)
def _pycountry_names() -> List[str]:
    if pycountry is None:
        return []
    names: List[str] = []
    for c in pycountry.countries:
        if hasattr(c, "name") and c.name:
            names.append(c.name)
        if hasattr(c, "official_name") and c.official_name:
            names.append(c.official_name)
        if hasattr(c, "common_name") and c.common_name:
            names.append(c.common_name)
    unique = {n.strip() for n in names if n and n.strip()}
    return sorted(unique, key=lambda s: (-len(s), s))


def infer_country(text: str) -> tuple[Optional[str], float]:
    """
    Try to infer a country name from text using aliases + pycountry.
    Returns (country_name, confidence).
    """
    if not text:
        return None, 0.0
    aliases, _coords = _load_country_data()
    text_lower = text.lower()

    matches: List[tuple[int, str]] = []
    for alias, canonical in aliases.items():
        pos = _alias_matches(text_lower, alias)
        if pos is None:
            continue
        matches.append((pos, canonical))

    if matches:
        matches.sort(key=lambda x: x[0])
        canonical = matches[0][1]
        if len(matches) == 1:
            return _strip_emoji_prefix(canonical), 0.95
        # Multiple matches: pick the first mention deterministically
        return _strip_emoji_prefix(canonical), 0.95

    # Fallback to pycountry names
    for name in _pycountry_names():
        alias = name.lower()
        if _alias_matches(text_lower, alias) is not None:
            return name, 0.7

    return None, 0.0


_COORD_REGEX = re.compile(
    r"(?P<lat>-?\d{1,2}\.\d+)\s*[,/ ]\s*(?P<lon>-?\d{1,3}\.\d+)",
    re.IGNORECASE,
)

_COORD_HEMI_REGEX = re.compile(
    r"(?P<lat>\d{1,2}\.\d+)\s*[°]?\s*(?P<ns>[NS])\s*[,/ ]\s*"
    r"(?P<lon>\d{1,3}\.\d+)\s*[°]?\s*(?P<ew>[EW])",
    re.IGNORECASE,
)


def infer_location(text: str) -> tuple[Optional[str], float]:
    """
    Infer a location by extracting explicit coordinates from text.
    Returns (location, confidence).
    """
    if not text:
        return None, 0.0

    match = _COORD_HEMI_REGEX.search(text)
    if match:
        lat = match.group("lat")
        lon = match.group("lon")
        ns = match.group("ns").upper()
        ew = match.group("ew").upper()
        lat = f"{lat}{ns}"
        lon = f"{lon}{ew}"
        return f"{lat}, {lon}", 0.95

    match = _COORD_REGEX.search(text)
    if match:
        lat = match.group("lat")
        lon = match.group("lon")
        return f"{lat}, {lon}", 0.95

    return None, 0.0


def enrich_record(record: Dict[str, str]) -> tuple[Dict[str, Optional[str]], Dict[str, float], str]:
    """
    Deterministic enrichment pass.
    Returns (fields, confidences, normalized_text).
    """
    original_text = record.get("text") or ""
    text_norm = normalize_text(original_text)

    country, country_conf = infer_country(text_norm)
    location, location_conf = infer_location(text_norm)

    fields: Dict[str, Optional[str]] = {
        "country": country,
        "region": None,
        "location": location,
        "title": None,
    }
    confidences: Dict[str, float] = {
        "country": country_conf,
        "region": 0.0,
        "location": location_conf,
        "title": 0.0,
    }
    return fields, confidences, text_norm

@dataclass
class EnrichmentConfig:
    min_confidence: Dict[str, float] = field(
        default_factory=lambda: {
            "country": 0.9,
            "location": 0.9,
        }
    )
    pipeline_version: str = "1"
    ai_timeout: int = 30
    debug: bool = True
    ai_client: Optional[Any] = None
    model_name: Optional[str] = None
    target_language: str = "fr"
    batch_size: int = 20


def _get_openai_client(api_key: Optional[str]):
    from openai import OpenAI
    return OpenAI(api_key=api_key)


def _enrich_subbatch(
    items: List[Dict[str, Any]],
    config: EnrichmentConfig,
    api_key: Optional[str],
) -> List[Dict[str, Optional[str]]]:
    """
    items: [{"id": int, "text": str, "lang": str, "known_fields": {}, "missing_fields": []}]
    Returns list of dicts with missing fields only (same order as items).
    """
    if not items:
        return []

    header = (
        "You are an OSINT information extraction system.\n"
        "You will receive one JSON object per line. Each object contains:\n"
        "- id: integer\n"
        "- text: normalized message text\n"
        "- known_fields: fields already extracted\n"
        "- missing_fields: list of fields that are still unknown\n\n"
        "For EACH input line, output ONE JSON object on a single line (JSONL).\n"
        "Rules:\n"
        "- Output must be strict JSON, no comments or extra text.\n"
        "- Each output object MUST include the id and ONLY the fields listed in missing_fields.\n"
        "- If a field is unknown, set it to an empty string.\n"
        f"- title MUST be a short sentence (8-18 words) in {config.target_language}.\n"
        "- country must be the main impacted country in English, or empty string if uncertain.\n"
        "- region is a large area (province/region), or empty string.\n"
        "- location is a city or specific place, or empty string.\n"
        "Do NOT repeat known_fields. Do NOT infer fields not requested.\n"
        "\n"
        "Inputs:\n"
    )

    body_lines = [json.dumps(item, ensure_ascii=False) for item in items]
    prompt = header + "\n".join(body_lines)

    client = config.ai_client or _get_openai_client(api_key)
    resp = client.responses.create(
        model=config.model_name,
        input=prompt,
        timeout=config.ai_timeout,
    )

    try:
        raw = resp.output_text
    except AttributeError:
        raw = str(resp)

    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    id_to_index = {int(it["id"]): idx for idx, it in enumerate(items)}
    results: List[Dict[str, Optional[str]]] = [dict() for _ in items]

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
        if obj_id not in id_to_index:
            continue
        idx = id_to_index[obj_id]
        missing = set(items[idx].get("missing_fields", []))
        filtered: Dict[str, Optional[str]] = {}
        for field in missing:
            value = obj.get(field, "")
            if value is None:
                value = ""
            elif not isinstance(value, str):
                value = str(value)
            filtered[field] = value
        results[idx] = filtered

    return results


def _resolve_config(config: Optional[EnrichmentConfig]) -> EnrichmentConfig:
    settings = get_settings()
    if config is None:
        return EnrichmentConfig(
            pipeline_version=settings.enrichment_version,
            model_name=settings.openai_model,
            target_language=settings.target_language,
            batch_size=settings.batch_size,
        )

    if not config.pipeline_version:
        config.pipeline_version = settings.enrichment_version
    if not config.model_name:
        config.model_name = settings.openai_model
    if not config.target_language:
        config.target_language = settings.target_language
    if not config.batch_size:
        config.batch_size = settings.batch_size
    return config


def enrich_messages(messages: List[dict], *, config: Optional[EnrichmentConfig] = None) -> List[dict]:
    """
    Takes a list of dicts with 'text', enriches them in batches.
    Deterministic enrichment runs first; AI is a fallback for missing fields.
    """
    if not messages:
        return messages

    config = _resolve_config(config)
    settings = get_settings()
    print(f"[pipeline] [ENRICH] batch_size={config.batch_size}")
    total = len(messages)
    for start in range(0, total, config.batch_size):
        end = min(start + config.batch_size, total)
        sub = messages[start:end]

        print(f"[pipeline] [ENRICH] batch {start + 1}-{end} / {total} (size={len(sub)})")

        ai_items: List[Dict[str, Any]] = []
        ai_payloads: List[Dict[str, Any]] = []
        deterministic_resolved = 0

        for idx, msg in enumerate(sub):
            fields, confidences, text_norm = enrich_record(msg)

            # Apply deterministic values only if confidence is high enough
            for field, value in fields.items():
                if msg.get(field):
                    continue
                if value is None:
                    continue
                threshold = config.min_confidence.get(field, 1.0)
                if confidences.get(field, 0.0) >= threshold:
                    msg[field] = value

            missing_fields = [
                field for field in AI_FIELDS
                if not (msg.get(field) or "").strip()
            ]

            if not missing_fields:
                deterministic_resolved += 1
                if config.debug:
                    print("[pipeline] [ENRICH][AI] AI enrichment skipped: all fields resolved deterministically")
                continue

            payload = {
                "id": idx,
                "text": text_norm,
                "known_fields": {k: msg.get(k) for k in AI_FIELDS if msg.get(k)},
                "missing_fields": missing_fields,
            }
            ai_payloads.append(payload)
            ai_items.append(payload)

        if ai_items and config.ai_client is None and (not settings.openai_api_key or not config.model_name):
            if config.debug:
                print("[pipeline] [ENRICH][AI] disabled (missing OpenAI settings).")
            continue

        if config.debug:
            print(
                f"[pipeline] [ENRICH][AI] to_call={len(ai_items)}"
            )

        if not ai_items:
            continue

        # Call AI for the remaining items
        results = _enrich_subbatch(ai_payloads, config, settings.openai_api_key)

        for item, result in zip(ai_items, results):
            if not isinstance(result, dict) or not result:
                continue
            missing_fields = item.get("missing_fields", [])
            msg = sub[item["id"]]
            for field in missing_fields:
                value = result.get(field, "")
                if value:
                    msg[field] = value

        for msg in sub:
            for field in AI_FIELDS:
                if not (msg.get(field) or "").strip():
                    msg[field] = None

    return messages
