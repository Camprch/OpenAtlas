# tools/build_static_site.py
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
import sys

# Load .env values before importing settings/db
from dotenv import load_dotenv
load_dotenv()

# Root of the repo so local modules import correctly when running as a script.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import shutil

from app.database import get_session, init_db
from app.models.message import Message
from sqlmodel import select


# Build output locations.
OUTPUT_DIR = Path("static_site")
STATIC_DIR = OUTPUT_DIR / "static"
DATA_DIR = STATIC_DIR / "data"
CSS_DIR = STATIC_DIR / "css"
JS_DIR = STATIC_DIR / "js"


def _date_key(value) -> str | None:
    """Normalize timestamps to YYYY-MM-DD for filter keys."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    try:
        return value.isoformat()
    except Exception:
        return None


def build_static_site() -> None:
    """Export DB content + assets into a fully static, offline-friendly site."""
    init_db()

    # Top-level aggregates used for filters and marker counts.
    events = []
    sources = set()
    labels = set()
    event_types = set()
    dates = set()

    with get_session() as session:
        # Lightweight rows for counts + filters.
        stmt = select(
            Message.country_norm,
            Message.event_timestamp,
            Message.source,
            Message.label,
            Message.event_type,
        )
        rows = session.exec(stmt).all()

        # Rich rows for the sidepanel event list.
        detail_rows = session.exec(
            select(
                Message.id,
                Message.country_norm,
                Message.region,
                Message.location,
                Message.title,
                Message.translated_text,
                Message.raw_text,
                Message.event_timestamp,
                Message.source,
                Message.label,
                Message.event_type,
                Message.orientation,
                Message.created_at,
                Message.channel,
                Message.telegram_message_id,
            )
        ).all()

    # Build filter sets + event list for the map markers.
    for country_norm, event_timestamp, source, label, event_type in rows:
        if not country_norm:
            continue
        date_key = _date_key(event_timestamp)
        if date_key:
            dates.add(date_key)
        if source:
            sources.add(source)
        if label:
            labels.add(label)
        if event_type:
            event_types.add(event_type)
        # Store only what the static UI needs for the map.
        events.append(
            {
                "country": country_norm,
                "date": date_key,
                "source": source or None,
                "label": label or None,
                "event_type": event_type or None,
            }
        )

    # Augment filters with detail rows (mirrors API behavior when main rows are sparse).
    for row in detail_rows:
        source = row[8]
        label = row[9]
        event_type = row[10]
        created_at = row[12]
        if source:
            sources.add(source)
        if label:
            labels.add(label)
        if event_type:
            event_types.add(event_type)
        if not dates and created_at:
            date_key = _date_key(created_at)
            if date_key:
                dates.add(date_key)

    # Single JSON payload used by the static JS.
    payload = {
        "events": events,
        "filters": {
            "date": sorted(dates, reverse=True),
            "source": sorted(sources),
            "label": sorted(labels),
            "event_type": sorted(event_types),
        },
        "details": [
            {
                "id": row[0],
                "country": row[1],
                "region": row[2],
                "location": row[3],
                "title": row[4],
                "text": row[5] or row[6] or "",
                "timestamp": _date_key(row[7]),
                "source": row[8],
                "label": row[9],
                "event_type": row[10],
                "orientation": row[11],
                "created_at": _date_key(row[12]),
                "channel": row[13],
                "telegram_message_id": row[14],
            }
            for row in detail_rows
        ],
    }

    # Write the data payload.
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "events.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Copy static assets for a consistent UI with the live app.
    CSS_DIR.mkdir(parents=True, exist_ok=True)
    JS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copytree(Path("static/css"), CSS_DIR, dirs_exist_ok=True)
    shutil.copytree(Path("static/js"), JS_DIR, dirs_exist_ok=True)

    countries_src = Path("static/data/countries.json")
    countries_dst = DATA_DIR / "countries.json"
    # Include the country coordinates/aliases lookup.
    countries_dst.write_text(countries_src.read_text(encoding="utf-8"), encoding="utf-8")

    # Write static HTML from template file.
    template_path = Path("templates") / "static_index.html"
    (OUTPUT_DIR / "index.html").write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")

if __name__ == "__main__":
    build_static_site()
