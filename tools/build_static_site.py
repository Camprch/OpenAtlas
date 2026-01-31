# tools/build_static_site.py
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlmodel import select
import shutil

from app.database import get_session, init_db
from app.models.message import Message


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
  <link rel=\"stylesheet\" href=\"./static/css/dashboard.css\" />
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
  <style>
    .header-search-btn { display: inline-flex; }
  </style>
</head>
<body>
  <div id=\"filter-menu\" style=\"display:none; position:fixed; top:60px; left:80px; transform:none; background:#23272e; color:#eee; border:1px solid #444; border-radius:12px; box-shadow:0 4px 24px #0008; z-index:9999; min-width:260px; padding:18px 20px;\">
    <button id=\"filter-menu-close\" style=\"background:#444; color:#eee; border:none; border-radius:6px; padding:6px 16px; cursor:pointer; position:absolute; top:8px; right:12px;\">×</button>
    <div id=\"filter-menu-options\" style=\"margin-top:18px;\"></div>
  </div>

  <header style=\"display:flex; align-items:center; gap:8px; justify-content:space-between;\">
    <div style=\"display:flex; align-items:center; gap:16px;\">
      <span class=\"logo-icon\" style=\"display:flex; align-items:center; justify-content:center; width:36px; height:36px; background:linear-gradient(135deg, #22c55e 60%, #2563eb 100%); border-radius:50%; box-shadow:0 2px 8px #0005; font-size:1.5rem; margin-right:5px; border:2px solid #23272e;\">🌍</span>
      <span style=\"font-size:1.35rem; font-weight:700; letter-spacing:1.2px; color:#eee; font-family:'Segoe UI', Arial, sans-serif; text-shadow:0 2px 6px #0003;\">MAP</span>
      <div id=\"filter-container-global\" style=\"display:flex; align-items:center; gap:4px;\">
        <button id=\"filter-btn-global\" style=\"padding:6px 14px; background:#1a1f24; border:1px solid #444; color:#eee; border-radius:999px; font-size:13px; cursor:pointer; font-family:Arial, sans-serif;\">Filters <span style='font-size:1.2em;'>🔬</span></button>
      </div>
      <button id=\"static-search-btn\" class=\"header-search-btn\" style=\"padding:6px 14px; background:#1a1f24; border:1px solid #444; color:#eee; border-radius:999px; font-size:13px; cursor:pointer; font-family:Arial, sans-serif;\">Search <span style='font-size:1.1em;'>🔎</span></button>
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
      <div id=\"sidepanel-search-row\" style=\"margin:6px 0 10px 0;\">
        <input id=\"static-search-input-panel\" type=\"search\" placeholder=\"Rechercher...\" style=\"width:100%; padding:6px 12px; background:#1a1f24; border:1px solid #444; color:#eee; border-radius:999px; font-size:13px; font-family:Arial, sans-serif; outline:none;\" />
      </div>
      <div id=\"sidepanel-events-header\" style=\"display:flex; align-items:center; gap:10px; margin-bottom:8px;\">
        <h3 style=\"margin:0;\">Events 📰</h3>
        <div id=\"filter-container-panel\">
          <button id=\"filter-btn-panel\" style=\"padding:6px 14px; background:#1a1f24; border:1px solid #444; color:#eee; border-radius:999px; font-size:13px; cursor:pointer; font-family:Arial, sans-serif;\">Filter <span style='font-size:1.2em;'>🔎</span></button>
        </div>
      </div>
      <div id=\"events\"></div>
    </div>
  </div>
  <div id=\"sidepanel-backdrop\"></div>

  <script type=\"module\" src=\"./static/js/static_app.js\"></script>
</body>
</html>
""",
        encoding="utf-8",
    )

    (JS_DIR / "static_app.js").write_text(
        """import { initMap, markerStyle, clearMarkers, map, markersByCountry } from './static_map.js';\n\nconst filterMenu = document.getElementById('filter-menu');\nconst filterClose = document.getElementById('filter-menu-close');\nconst filterBtn = document.getElementById('filter-btn-global');\nconst filterBtnPanel = document.getElementById('filter-btn-panel');\nconst sidepanel = document.getElementById('sidepanel');\nconst sidepanelBackdrop = document.getElementById('sidepanel-backdrop');\nconst sidepanelClose = document.getElementById('close-panel');\nconst panelCountryText = document.getElementById('panel-country-text');\nconst eventsContainer = document.getElementById('events');\nconst staticSearchInputPanel = document.getElementById('static-search-input-panel');\nconst staticSearchBtn = document.getElementById('static-search-btn');\n\nconst selected = { date: new Set(), source: new Set(), label: new Set(), event_type: new Set() };\nlet currentCountryKey = null;\nlet searchQuery = '';\nlet allDetails = [];\nconst isMobile = window.matchMedia('(max-width: 768px)').matches;\n\nfunction normalize(str) {\n  return (str || '').normalize('NFD').replace(/\\p{Diacritic}/gu, '').toLowerCase();\n}\n\nfunction containsQuery(text, query) {\n  if (!query) return false;\n  return normalize(text).includes(normalize(query));\n}\n\nfunction highlightQuery(text, query) {\n  if (!query) return text || '';\n  const raw = text || '';\n  const normText = normalize(raw);\n  const normQuery = normalize(query);\n  if (!normQuery) return raw;\n  let result = '';\n  let i = 0;\n  while (i < raw.length) {\n    let found = -1;\n    for (let j = i; j <= raw.length - normQuery.length; j++) {\n      if (normText.substr(j, normQuery.length) === normQuery) {\n        found = j;\n        break;\n      }\n    }\n    if (found === -1) {\n      result += raw.slice(i);\n      break;\n    }\n    result += raw.slice(i, found) + `<span class="search-hl" style="background:#ffe066;color:#222;border-radius:3px;padding:0 2px;">` + raw.slice(found, found + normQuery.length) + '</span>';\n    i = found + normQuery.length;\n  }\n  return result;\n}\n\nfunction applyFilters(events) {\n  return events.filter(e => {\n    if (selected.date.size && (!e.date || !selected.date.has(e.date))) return false;\n    if (selected.source.size && (!e.source || !selected.source.has(e.source))) return false;\n    if (selected.label.size && (!e.label || !selected.label.has(e.label))) return false;\n    if (selected.event_type.size && (!e.event_type || !selected.event_type.has(e.event_type))) return false;\n    return true;\n  });\n}\n\nfunction applyFiltersToDetails(details) {\n  return details.filter(item => {\n    if (selected.date.size && (!item.timestamp || !selected.date.has(item.timestamp))) return false;\n    if (selected.source.size && (!item.source || !selected.source.has(item.source))) return false;\n    if (selected.label.size && (!item.label || !selected.label.has(item.label))) return false;\n    if (selected.event_type.size && (!item.event_type || !selected.event_type.has(item.event_type))) return false;\n    return true;\n  });\n}\n\nfunction buildCountryEvents(countryKey, details) {\n  const filtered = applyFiltersToDetails(details);\n  const buckets = new Map();\n  filtered.forEach(item => {\n    const key = `${item.region || ''}||${item.location || ''}`;\n    if (!buckets.has(key)) buckets.set(key, []);\n    buckets.get(key).push(item);\n  });\n\n  const zones = [];\n  buckets.forEach((items, key) => {\n    const [region, location] = key.split('||');\n    items.sort((a, b) => (b.timestamp || '').localeCompare(a.timestamp || ''));\n    const messages = items.map(m => {\n      const text = m.text || '';\n      const preview = text.length > 280 ? text.slice(0, 277) + '...' : text;\n      const url = (m.channel && m.telegram_message_id) ? `https://t.me/${m.channel}/${m.telegram_message_id}` : null;\n      return {\n        id: m.id,\n        telegram_message_id: m.telegram_message_id,\n        channel: m.channel,\n        title: m.title,\n        source: m.source,\n        orientation: m.orientation,\n        event_timestamp: m.timestamp,\n        created_at: m.created_at,\n        url,\n        translated_text: text,\n        preview,\n      };\n    });\n    zones.push({\n      region: region || null,\n      location: location || null,\n      messages_count: messages.length,\n      messages,\n    });\n  });\n\n  zones.sort((a, b) => b.messages_count - a.messages_count);\n  return {\n    date: selected.date.size ? Array.from(selected.date)[0] : new Date().toISOString().slice(0, 10),\n    country: countryKey,\n    zones,\n  };\n}\n\nfunction setSearchValue(value) {\n  if (staticSearchInputPanel) staticSearchInputPanel.value = value;\n}\n\nfunction openSearchPanel() {\n  closeFilterMenu();\n  panelCountryText.textContent = 'Recherche';\n  currentCountryKey = null;\n  sidepanel.classList.add('visible');\n  sidepanelBackdrop.classList.add('visible');\n}\n\nfunction renderSearchResults(query, details) {\n  const q = (query || '').trim();\n  if (!q) {\n    eventsContainer.textContent = 'Saisissez une recherche.';\n    return;\n  }\n  const filtered = applyFiltersToDetails(details).filter(item => {\n    const haystack = [\n      item.title,\n      item.text,\n      item.country,\n      item.region,\n      item.location,\n      item.source,\n      item.label,\n      item.event_type,\n    ].filter(Boolean).join(' ');\n    return containsQuery(haystack, q);\n  });\n  if (!filtered.length) {\n    eventsContainer.textContent = 'Aucun résultat.';\n    return;\n  }\n  const itemsHtml = filtered.map(item => {\n    const title = highlightQuery(item.title || '(Sans titre)', q);\n    const fullText = highlightQuery(item.text || '', q);\n    const where = [item.country, item.region, item.location].filter(Boolean).join(' – ');\n    const orientation = item.orientation ? ` • ${item.orientation}` : '';\n    const rawTime = item.timestamp || item.created_at;\n    const timeStr = rawTime ? new Date(rawTime).toLocaleString() : '';\n    const source = item.source || '';\n    const metaParts = [];\n    if (source) metaParts.push(`<span class="evt-source">${source}${orientation}</span>`);\n    if (timeStr) metaParts.push(`<span class="evt-time">${timeStr}</span>`);\n    if (where) metaParts.push(`<span class="evt-location" style="color:#aaa;">${highlightQuery(where, q)}</span>`);\n    const meta = metaParts.length ? `<div class="evt-meta">${metaParts.join('')}</div>` : '';\n    return `\n            <li class="event" data-msg-id="${item.id}">\n                <div class="evt-title" style="cursor:pointer;">${title}</div>\n                <div class="evt-text" style="display:block;">\n                    ${fullText}\n                    ${meta}\n                </div>\n            </li>\n        `;\n  }).join('');\n  eventsContainer.innerHTML = `<div style="margin-bottom:8px;color:#bbb;">${filtered.length} résultat(s)</div><ul class="event-list" style="display:block;">${itemsHtml}</ul>`;\n  eventsContainer.querySelectorAll('.evt-title').forEach(titleEl => {\n    if (!titleEl.dataset.listener) {\n      titleEl.addEventListener('click', function(e) {\n        e.stopPropagation();\n        const text = this.nextElementSibling;\n        if (text.style.display === 'none' || !text.style.display) {\n          text.style.display = 'block';\n        } else {\n          text.style.display = 'none';\n        }\n      });\n      titleEl.dataset.listener = '1';\n    }\n  });\n}\n\nfunction renderEvents(data) {\n  const eventsContainer = document.getElementById('events');\n  if (!data || !data.zones || data.zones.length === 0) {\n    eventsContainer.textContent = 'Aucun événement.';\n    return;\n  }\n  const html = data.zones.map((zone, idx) => {\n    const header = [zone.region, zone.location].filter(Boolean).join(' – ') || 'Zone inconnue';\n    const msgs = zone.messages.map((m, mIdx) => {\n      const title = m.title || '(Sans titre)';\n      const fullText = m.translated_text || '';\n      const orientation = m.orientation ? ` • ${m.orientation}` : '';\n      const postLink = m.url ? `<a href=\"${m.url}\" target=\"_blank\">post n° ${m.telegram_message_id}</a>` : '';\n      const timeStr = new Date(m.event_timestamp || m.created_at).toLocaleString();\n      return `\\n            <li class=\"event\" data-msg-id=\"${m.id}\">\\n                <div class=\"evt-title\" data-zone=\"${idx}\" data-msg=\"${mIdx}\" style=\"cursor:pointer;\">${title}</div>\\n                <div class=\"evt-text\" style=\"display:none;\">\\n                    ${fullText}\\n                    <div class=\"evt-meta\">\\n                        <span class=\"evt-source\">${m.source}${orientation}</span>\\n                        <span class=\"evt-time\">${timeStr}</span>\\n                        <span class=\"evt-link\">${postLink}</span>\\n                    </div>\\n                </div>\\n            </li>\\n        `;\n    }).join('');\n    return `\\n            <section class=\"zone-block\">\\n                <h4 class=\"zone-header\" data-idx=\"${idx}\">\\n                    <span class=\"toggle-btn\">▶</span> ${header}\\n                    <span class=\"evt-count\">(${zone.messages_count})</span>\\n                </h4>\\n                <ul class=\"event-list\" id=\"zone-list-${idx}\" style=\"display:none;\">\\n                    ${msgs}\\n                </ul>\\n            </section>\\n        `;\n  }).join('');\n  eventsContainer.innerHTML = html;\n  data.zones.forEach((zone, idx) => {\n    const headerEl = document.querySelector(`.zone-header[data-idx='${idx}']`);\n    const listEl = document.getElementById(`zone-list-${idx}`);\n    const btn = headerEl.querySelector('.toggle-btn');\n    headerEl.addEventListener('click', () => {\n      if (listEl.style.display === 'none') {\n        listEl.style.display = '';\n        btn.textContent = '▼';\n        listEl.querySelectorAll('.evt-title').forEach(titleEl => {\n          if (!titleEl.dataset.listener) {\n            titleEl.addEventListener('click', function(e) {\n              e.stopPropagation();\n              const text = this.nextElementSibling;\n              if (text.style.display === 'none' || !text.style.display) {\n                text.style.display = 'block';\n              } else {\n                text.style.display = 'none';\n              }\n            });\n            titleEl.dataset.listener = '1';\n          }\n        });\n      } else {\n        listEl.style.display = 'none';\n        btn.textContent = '▶';\n      }\n    });\n  });\n}\n\nfunction openSidePanel(countryKey, details) {\n  panelCountryText.textContent = countryKey.replace(/^[^\\p{L}\\p{N}]+/u, '').trim();\n  currentCountryKey = countryKey;\n  setSearchValue('');\n  searchQuery = '';\n  renderEvents(buildCountryEvents(countryKey, details));\n  sidepanel.classList.add('visible');\n  sidepanelBackdrop.classList.add('visible');\n}\n\nfunction closeSidePanel() {\n  sidepanel.classList.remove('visible');\n  sidepanelBackdrop.classList.remove('visible');\n}\n\nsidepanelClose.addEventListener('click', closeSidePanel);\nsidepanelBackdrop.addEventListener('click', closeSidePanel);\n\nfunction renderMarkers(events, coords, aliases, detailsByCountry) {\n  clearMarkers();\n  const counts = new Map();\n  events.forEach(e => {\n    if (!e.country) return;\n    const key = e.country;\n    counts.set(key, (counts.get(key) || 0) + 1);\n  });\n\n  counts.forEach((count, key) => {\n    let coordKey = key;\n    if (!coords[coordKey] && aliases[key] && coords[aliases[key]]) {\n      coordKey = aliases[key];\n    }\n    if (!coords[coordKey]) return;\n    const [lat, lon] = coords[coordKey];\n    const style = markerStyle(count);\n    const marker = L.circleMarker([lat, lon], style);\n    // Popup with flag + country name (desktop only)\n    if (!isMobile) {\n      let flag = '';\n      if (/^\\p{Emoji}/u.test(coordKey)) {\n        flag = coordKey.split(' ')[0];\n      } else {\n        for (const alias in aliases) {\n          if (aliases[alias] === coordKey && /^\\p{Emoji}/u.test(alias)) {\n            flag = alias.split(' ')[0];\n            break;\n          }\n        }\n      }\n      const countryName = coordKey.replace(/^[^\\p{L}\\p{N}]+/u, '').trim();\n      marker.bindPopup(`<div style='text-align:center;min-width:70px;'><span style='font-size:2.2em;line-height:1;'>${flag}</span><br><b>${countryName}</b></div>`);\n      marker.on('mouseover', () => marker.openPopup && marker.openPopup());\n      marker.on('mouseout', () => marker.closePopup && marker.closePopup());\n    }\n    marker.on('mouseover', () => marker.setStyle({ radius: style.radius * 1.15 }));\n    marker.on('mouseout', () => marker.setStyle({ radius: style.radius }));\n    marker.on('click', () => openSidePanel(coordKey, detailsByCountry.get(key) || []));\n    marker.addTo(map);\n    markersByCountry[coordKey] = marker;\n  });\n}\n\nfunction renderFilters(filters) {\n  const optionsDiv = document.getElementById('filter-menu-options');\n  optionsDiv.innerHTML = '';\n  const columns = document.createElement('div');\n  columns.id = 'filter-columns';\n  const categories = [\n    { key: 'date', label: 'Date \\uD83D\\uDCC5' },\n    { key: 'source', label: 'Source \\uD83D\\uDCF1' },\n    { key: 'label', label: 'Label \\uD83C\\uDFF7\\uFE0F' },\n    { key: 'event_type', label: 'Type \\uD83D\\uDCDD' },\n  ];\n  categories.forEach(cat => {\n    const col = document.createElement('div');\n    col.className = 'filter-col';\n    const title = document.createElement('div');\n    title.className = 'filter-col-title';\n    title.textContent = cat.label;\n    col.appendChild(title);\n    const list = document.createElement('div');\n    list.className = 'filter-options-list';\n    const values = filters[cat.key] || [];\n    if (!values.length) {\n      list.textContent = 'Aucune option.';\n    } else {\n      values.forEach(val => {\n        const label = document.createElement('label');\n        const checkbox = document.createElement('input');\n        checkbox.type = 'checkbox';\n        checkbox.value = val;\n        checkbox.checked = selected[cat.key].has(val);\n        checkbox.addEventListener('change', () => {\n          if (checkbox.checked) {\n            selected[cat.key].add(val);\n          } else {\n            selected[cat.key].delete(val);\n          }\n          window.__refresh();\n        });\n        label.appendChild(checkbox);\n        label.appendChild(document.createTextNode(val));\n        list.appendChild(label);\n      });\n    }\n    col.appendChild(list);\n    columns.appendChild(col);\n  });\n  optionsDiv.appendChild(columns);\n}\n\nfunction openFilterMenu(opener) {\n  filterMenu.style.display = 'block';\n  if (opener === 'panel') {\n    filterMenu.style.position = 'fixed';\n    filterMenu.style.top = '80px';\n    filterMenu.style.right = '420px';\n    filterMenu.style.left = '';\n    filterMenu.style.transform = 'none';\n  } else {\n    filterMenu.style.position = 'fixed';\n    filterMenu.style.top = '60px';\n    filterMenu.style.left = '80px';\n    filterMenu.style.right = '';\n    filterMenu.style.transform = 'none';\n  }\n}\n\nfunction closeFilterMenu() {\n  filterMenu.style.display = 'none';\n}\n\nfilterBtn.addEventListener('click', () => {\n  if (filterMenu.style.display === 'block') {\n    closeFilterMenu();\n  } else {\n    openFilterMenu('global');\n  }\n});\n\nif (filterBtnPanel) {\n  filterBtnPanel.addEventListener('click', () => {\n    if (filterMenu.style.display === 'block') {\n      closeFilterMenu();\n    } else {\n      openFilterMenu('panel');\n    }\n  });\n}\n\nfilterClose.addEventListener('click', closeFilterMenu);\n\nasync function init() {\n  initMap();\n  const [countriesResp, eventsResp] = await Promise.all([\n    fetch('./static/data/countries.json'),\n    fetch('./static/data/events.json'),\n  ]);\n  const countries = await countriesResp.json();\n  const dataset = await eventsResp.json();\n  const coords = countries.coordinates || {};\n  const aliases = countries.aliases || {};\n  const events = dataset.events || [];\n  const details = dataset.details || [];\n  allDetails = details;\n  const detailsByCountry = new Map();\n  details.forEach(d => {\n    if (!d.country) return;\n    if (!detailsByCountry.has(d.country)) detailsByCountry.set(d.country, []);\n    detailsByCountry.get(d.country).push(d);\n  });\n\n  renderFilters(dataset.filters || {});\n\n  const openAndRender = (value) => {\n    searchQuery = value || '';\n    openSearchPanel();\n    renderSearchResults(searchQuery, allDetails);\n  };\n  if (staticSearchInputPanel) {\n    staticSearchInputPanel.addEventListener('focus', () => openAndRender(staticSearchInputPanel.value));\n    staticSearchInputPanel.addEventListener('click', () => openAndRender(staticSearchInputPanel.value));\n    staticSearchInputPanel.addEventListener('input', () => {\n      setSearchValue(staticSearchInputPanel.value);\n      openAndRender(staticSearchInputPanel.value);\n    });\n    staticSearchInputPanel.addEventListener('keydown', (e) => {\n      if (e.key === 'Escape') {\n        setSearchValue('');\n        searchQuery = '';\n        closeSidePanel();\n      }\n    });\n  }\n  if (staticSearchBtn) {\n    staticSearchBtn.addEventListener('click', () => {\n      openSearchPanel();\n      if (staticSearchInputPanel) {\n        staticSearchInputPanel.focus();\n        openAndRender(staticSearchInputPanel.value);\n      } else {\n        eventsContainer.textContent = 'Saisissez une recherche.';\n      }\n    });\n  }\n\n  window.__refresh = () => {\n    const filtered = applyFilters(events);\n    renderMarkers(filtered, coords, aliases, detailsByCountry);\n    if (sidepanel.classList.contains('visible')) {\n      if (searchQuery) {\n        renderSearchResults(searchQuery, allDetails);\n      } else if (currentCountryKey) {\n        renderEvents(buildCountryEvents(currentCountryKey, detailsByCountry.get(currentCountryKey) || []));\n      }\n    }\n  };\n  window.__refresh();\n}\n\ninit();\n""",
        encoding="utf-8",
    )

    (JS_DIR / "static_map.js").write_text(
        """export let map;\nexport let markersByCountry = {};\n\nconst IS_MOBILE = window.matchMedia('(max-width: 768px)').matches;\n\nexport function initMap() {\n  map = L.map('map', { worldCopyJump: true, minZoom: 2, maxZoom: 8, tapTolerance: 30 }).setView([20, 0], 2);\n  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { attribution: '&copy; CARTO', noWrap: true }).addTo(map);\n}\n\nexport function clearMarkers() {\n  Object.values(markersByCountry).forEach(m => map.removeLayer(m));\n  markersByCountry = {};\n}\n\nexport function markerStyle(count) {\n  const n = Math.max(1, count || 1);\n  const minRadius = IS_MOBILE ? 8 : 4;\n  const maxRadius = IS_MOBILE ? 13 : 7;\n  const maxCount = 30;\n  const ratio = Math.min(n / maxCount, 1);\n  const radius = minRadius + (maxRadius - minRadius) * ratio;\n  let color = '#22c55e';\n  if (n >= 5 && n < 15) color = '#eab308';\n  if (n >= 15) color = '#f97316';\n  return { radius, color, fillColor: color, fillOpacity: 0.85, weight: IS_MOBILE ? 2 : 1 };\n}\n""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    build_static_site()
