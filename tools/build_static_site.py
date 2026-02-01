# tools/build_static_site.py
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import shutil

from app.database import get_session, init_db
from app.models.message import Message
from sqlmodel import select


OUTPUT_DIR = Path("static_site")
STATIC_DIR = OUTPUT_DIR / "static"
DATA_DIR = STATIC_DIR / "data"
CSS_DIR = STATIC_DIR / "css"
JS_DIR = STATIC_DIR / "js"


def _date_key(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    try:
        return value.isoformat()
    except Exception:
        return None


def build_static_site() -> None:
    init_db()

    events = []
    sources = set()
    labels = set()
    event_types = set()
    dates = set()

    with get_session() as session:
        stmt = select(
            Message.country_norm,
            Message.event_timestamp,
            Message.source,
            Message.label,
            Message.event_type,
        )
        rows = session.exec(stmt).all()

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
        events.append(
            {
                "country": country_norm,
                "date": date_key,
                "source": source or None,
                "label": label or None,
                "event_type": event_type or None,
            }
        )

    # Augment filters with detail rows (to match API behavior when main rows are sparse)
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
            if row[1]
        ],
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "events.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Copy static assets for consistent UI
    CSS_DIR.mkdir(parents=True, exist_ok=True)
    JS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copytree(Path("static/css"), CSS_DIR, dirs_exist_ok=True)
    shutil.copytree(Path("static/js"), JS_DIR, dirs_exist_ok=True)

    countries_src = Path("static/data/countries.json")
    countries_dst = DATA_DIR / "countries.json"
    countries_dst.write_text(countries_src.read_text(encoding="utf-8"), encoding="utf-8")

    # Write static HTML/JS that mirrors the dashboard map + filters
    (OUTPUT_DIR / "index.html").write_text(
        """<!DOCTYPE html>
<html lang=\"fr\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>OpenAtlas Static</title>
  <link rel="stylesheet" href="static/css/dashboard.css" />
  <link rel="stylesheet" href="static/css/sidepanel.css" />
  <link rel="stylesheet" href="static/css/base.css" />
  <link rel="stylesheet" href="static/css/dashboard_ui.css" />
  <link rel="stylesheet" href="static/css/events.css" />
  <link rel="stylesheet" href="static/css/filters.css" />
  <link rel="stylesheet" href="static/css/map.css" />
  <link rel="stylesheet" href="static/css/overrides.css" />
  <link rel="stylesheet" href="static/css/responsive.css" />
  <link
    rel=\"stylesheet\"
    href=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.css\"
    integrity=\"sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=\"
    crossorigin=\"\"
  >
  <script
    src=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.js\"
    integrity=\"sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=\"
    crossorigin=\"\"
  ></script>
</head>
<body class="static-site">
  <div id=\"filter-menu\">
    <button id=\"filter-menu-close\">×</button>
    <div id=\"filter-menu-options\"></div>
  </div>

  <header class=\"dashboard-header\">
    <div class=\"dashboard-header-left\">
      <span class=\"logo-icon logo-badge\">🌍</span>
      <span class=\"dashboard-title\">MAP</span>
      <div id=\"filter-container-global\">
        <button id=\"filter-btn-global\" class=\"pill-btn\">Filters <span class=\"pill-btn-icon\">🔬</span></button>
      </div>
      <button id=\"static-search-btn\" class=\"pill-btn header-search-btn\">Search <span class=\"pill-btn-icon\">🔎</span></button>
    </div>
  </header>

  <div id=\"dashboard-alert\"></div>
  <div id=\"map\"></div>

  <div id=\"sidepanel\">
    <button id=\"close-panel\">✖</button>
    <div id=\"sidepanel-header-row\">
      <h2 id=\"panel-country-name\"><span id=\"panel-country-text\"></span></h2>
    </div>
    <div id=\"sidepanel-content\">
      <div id=\"sidepanel-search-row\">
        <input id=\"static-search-input-panel\" type=\"search\" placeholder=\"Rechercher...\" />
      </div>
      <div id=\"sidepanel-events-header\">
        <h3>Events 📰</h3>
        <div id=\"filter-container-panel\">
          <button id=\"filter-btn-panel\" class=\"pill-btn\">Filter <span class=\"pill-btn-icon\">🔎</span></button>
        </div>
      </div>
      <div id=\"events\"></div>
    </div>
  </div>
  <div id=\"sidepanel-backdrop\"></div>

  <script type="module" src="static/js/static_app.js"></script>
</body>
</html>
""",
        encoding="utf-8",
    )

if __name__ == "__main__":
    build_static_site()
