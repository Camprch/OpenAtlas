import { initMap, markerStyle, clearMarkers, map, markersByCountry } from './static_map.js';

const filterMenu = document.getElementById('filter-menu');
const filterClose = document.getElementById('filter-menu-close');
const filterBtn = document.getElementById('filter-btn-global');
const filterBtnPanel = document.getElementById('filter-btn-panel');
const sidepanel = document.getElementById('sidepanel');
const sidepanelBackdrop = document.getElementById('sidepanel-backdrop');
const sidepanelClose = document.getElementById('close-panel');
const panelCountryText = document.getElementById('panel-country-text');
const eventsContainer = document.getElementById('events');
const staticSearchInputPanel = document.getElementById('static-search-input-panel');
const staticSearchBtn = document.getElementById('static-search-btn');

const selected = { date: new Set(), source: new Set(), label: new Set(), event_type: new Set() };
let currentCountryKey = null;
let searchQuery = '';
let allDetails = [];
const isMobile = window.matchMedia('(max-width: 768px)').matches;

function normalize(str) {
  return (str || '').normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
}

function containsQuery(text, query) {
  if (!query) return false;
  return normalize(text).includes(normalize(query));
}

function highlightQuery(text, query) {
  if (!query) return text || '';
  const raw = text || '';
  const normText = normalize(raw);
  const normQuery = normalize(query);
  if (!normQuery) return raw;
  let result = '';
  let i = 0;
  while (i < raw.length) {
    let found = -1;
    for (let j = i; j <= raw.length - normQuery.length; j++) {
      if (normText.substr(j, normQuery.length) === normQuery) {
        found = j;
        break;
      }
    }
    if (found === -1) {
      result += raw.slice(i);
      break;
    }
    result += raw.slice(i, found) + `<span class="search-hl" style="background:#ffe066;color:#222;border-radius:3px;padding:0 2px;">` + raw.slice(found, found + normQuery.length) + '</span>';
    i = found + normQuery.length;
  }
  return result;
}

function applyFilters(events) {
  return events.filter(e => {
    if (selected.date.size && (!e.date || !selected.date.has(e.date))) return false;
    if (selected.source.size && (!e.source || !selected.source.has(e.source))) return false;
    if (selected.label.size && (!e.label || !selected.label.has(e.label))) return false;
    if (selected.event_type.size && (!e.event_type || !selected.event_type.has(e.event_type))) return false;
    return true;
  });
}

function applyFiltersToDetails(details) {
  return details.filter(item => {
    if (selected.date.size && (!item.timestamp || !selected.date.has(item.timestamp))) return false;
    if (selected.source.size && (!item.source || !selected.source.has(item.source))) return false;
    if (selected.label.size && (!item.label || !selected.label.has(item.label))) return false;
    if (selected.event_type.size && (!item.event_type || !selected.event_type.has(item.event_type))) return false;
    return true;
  });
}

function buildCountryEvents(countryKey, details) {
  const filtered = applyFiltersToDetails(details);
  const buckets = new Map();
  filtered.forEach(item => {
    const key = `${item.region || ''}||${item.location || ''}`;
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(item);
  });

  const zones = [];
  buckets.forEach((items, key) => {
    const [region, location] = key.split('||');
    items.sort((a, b) => (b.timestamp || '').localeCompare(a.timestamp || ''));
    const messages = items.map(m => {
      const text = m.text || '';
      const preview = text.length > 280 ? text.slice(0, 277) + '...' : text;
      const url = (m.channel && m.telegram_message_id) ? `https://t.me/${m.channel}/${m.telegram_message_id}` : null;
      return {
        id: m.id,
        telegram_message_id: m.telegram_message_id,
        channel: m.channel,
        title: m.title,
        source: m.source,
        orientation: m.orientation,
        event_timestamp: m.timestamp,
        created_at: m.created_at,
        url,
        translated_text: text,
        preview,
      };
    });
    zones.push({
      region: region || null,
      location: location || null,
      messages_count: messages.length,
      messages,
    });
  });

  zones.sort((a, b) => b.messages_count - a.messages_count);
  return {
    date: selected.date.size ? Array.from(selected.date)[0] : new Date().toISOString().slice(0, 10),
    country: countryKey,
    zones,
  };
}

function setSearchValue(value) {
  if (staticSearchInputPanel) staticSearchInputPanel.value = value;
}

function openSearchPanel() {
  closeFilterMenu();
  panelCountryText.textContent = 'Recherche';
  currentCountryKey = null;
  sidepanel.classList.add('visible');
  sidepanelBackdrop.classList.add('visible');
}

function renderSearchResults(query, details) {
  const q = (query || '').trim();
  if (!q) {
    eventsContainer.textContent = 'Saisissez une recherche.';
    return;
  }
  const filtered = applyFiltersToDetails(details).filter(item => {
    const haystack = [
      item.title,
      item.text,
      item.country,
      item.region,
      item.location,
      item.source,
      item.label,
      item.event_type,
    ].filter(Boolean).join(' ');
    return containsQuery(haystack, q);
  });
  if (!filtered.length) {
    eventsContainer.textContent = 'Aucun résultat.';
    return;
  }
  const itemsHtml = filtered.map(item => {
    const title = highlightQuery(item.title || '(Sans titre)', q);
    const fullText = highlightQuery(item.text || '', q);
    const where = [item.country, item.region, item.location].filter(Boolean).join(' – ');
    const orientation = item.orientation ? ` • ${item.orientation}` : '';
    const rawTime = item.timestamp || item.created_at;
    const timeStr = rawTime ? new Date(rawTime).toLocaleString() : '';
    const source = item.source || '';
    const postLink = (item.channel && item.telegram_message_id)
      ? `<a href="https://t.me/${item.channel}/${item.telegram_message_id}" target="_blank">post n° ${item.telegram_message_id}</a>`
      : '';
    const metaParts = [];
    if (source) metaParts.push(`<span class="evt-source">${source}${orientation}</span>`);
    if (timeStr) metaParts.push(`<span class="evt-time">${timeStr}</span>`);
    if (where) metaParts.push(`<span class="evt-location" style="color:#aaa;">${highlightQuery(where, q)}</span>`);
    if (postLink) metaParts.push(`<span class="evt-link">${postLink}</span>`);
    const meta = metaParts.length ? `<div class="evt-meta">${metaParts.join('')}</div>` : '';
    return `
            <li class="event" data-msg-id="${item.id}">
                <div class="evt-title" style="cursor:pointer;">${title}</div>
                <div class="evt-text" style="display:block;">
                    ${fullText}
                    ${meta}
                </div>
            </li>
        `;
  }).join('');
  eventsContainer.innerHTML = `<div style="margin-bottom:8px;color:#bbb;">${filtered.length} résultat(s)</div><ul class="event-list" style="display:block;">${itemsHtml}</ul>`;
  eventsContainer.querySelectorAll('.evt-title').forEach(titleEl => {
    if (!titleEl.dataset.listener) {
      titleEl.addEventListener('click', function(e) {
        e.stopPropagation();
        const text = this.nextElementSibling;
        if (text.style.display === 'none' || !text.style.display) {
          text.style.display = 'block';
        } else {
          text.style.display = 'none';
        }
      });
      titleEl.dataset.listener = '1';
    }
  });
}

function renderEvents(data) {
  const eventsContainer = document.getElementById('events');
  if (!data || !data.zones || data.zones.length === 0) {
    eventsContainer.textContent = 'Aucun événement.';
    return;
  }
  const html = data.zones.map((zone, idx) => {
    const header = [zone.region, zone.location].filter(Boolean).join(' – ') || 'Zone inconnue';
    const msgs = zone.messages.map((m, mIdx) => {
      const title = m.title || '(Sans titre)';
      const fullText = m.translated_text || '';
      const orientation = m.orientation ? ` • ${m.orientation}` : '';
      const postLink = m.url ? `<a href="${m.url}" target="_blank">post n° ${m.telegram_message_id}</a>` : '';
      const timeStr = new Date(m.event_timestamp || m.created_at).toLocaleString();
      return `\n            <li class="event" data-msg-id="${m.id}">\n                <div class="evt-title" data-zone="${idx}" data-msg="${mIdx}" style="cursor:pointer;">${title}</div>\n                <div class="evt-text" style="display:none;">\n                    ${fullText}\n                    <div class="evt-meta">\n                        <span class="evt-source">${m.source}${orientation}</span>\n                        <span class="evt-time">${timeStr}</span>\n                        <span class="evt-link">${postLink}</span>\n                    </div>\n                </div>\n            </li>\n        `;
    }).join('');
    return `\n            <section class="zone-block">\n                <h4 class="zone-header" data-idx="${idx}">\n                    <span class="toggle-btn">▶</span> ${header}\n                    <span class="evt-count">(${zone.messages_count})</span>\n                </h4>\n                <ul class="event-list" id="zone-list-${idx}" style="display:none;">\n                    ${msgs}\n                </ul>\n            </section>\n        `;
  }).join('');
  eventsContainer.innerHTML = html;
  data.zones.forEach((zone, idx) => {
    const headerEl = document.querySelector(`.zone-header[data-idx='${idx}']`);
    const listEl = document.getElementById(`zone-list-${idx}`);
    const btn = headerEl.querySelector('.toggle-btn');
    headerEl.addEventListener('click', () => {
      if (listEl.style.display === 'none') {
        listEl.style.display = '';
        btn.textContent = '▼';
        listEl.querySelectorAll('.evt-title').forEach(titleEl => {
          if (!titleEl.dataset.listener) {
            titleEl.addEventListener('click', function(e) {
              e.stopPropagation();
              const text = this.nextElementSibling;
              if (text.style.display === 'none' || !text.style.display) {
                text.style.display = 'block';
              } else {
                text.style.display = 'none';
              }
            });
            titleEl.dataset.listener = '1';
          }
        });
      } else {
        listEl.style.display = 'none';
        btn.textContent = '▶';
      }
    });
  });
}

function openSidePanel(countryKey, details) {
  panelCountryText.textContent = countryKey.replace(/^[^\p{L}\p{N}]+/u, '').trim();
  currentCountryKey = countryKey;
  setSearchValue('');
  searchQuery = '';
  renderEvents(buildCountryEvents(countryKey, details));
  sidepanel.classList.add('visible');
  sidepanelBackdrop.classList.add('visible');
}

function closeSidePanel() {
  sidepanel.classList.remove('visible');
  sidepanelBackdrop.classList.remove('visible');
}

sidepanelClose.addEventListener('click', closeSidePanel);
sidepanelBackdrop.addEventListener('click', closeSidePanel);

function renderMarkers(events, coords, aliases, detailsByCountry) {
  clearMarkers();
  const counts = new Map();
  events.forEach(e => {
    if (!e.country) return;
    const key = e.country;
    counts.set(key, (counts.get(key) || 0) + 1);
  });

  counts.forEach((count, key) => {
    let coordKey = key;
    if (!coords[coordKey] && aliases[key] && coords[aliases[key]]) {
      coordKey = aliases[key];
    }
    if (!coords[coordKey]) return;
    const [lat, lon] = coords[coordKey];
    const style = markerStyle(count);
    const marker = L.circleMarker([lat, lon], style);
    let flag = '';
    if (/^\p{Emoji}/u.test(coordKey)) {
      flag = coordKey.split(' ')[0];
    } else {
      for (const alias in aliases) {
        if (aliases[alias] === coordKey && /^\p{Emoji}/u.test(alias)) {
          flag = alias.split(' ')[0];
          break;
        }
      }
    }
    // Popup with flag + country name (desktop only)
    if (!isMobile) {
      const countryName = coordKey.replace(/^[^\p{L}\p{N}]+/u, '').trim();
      marker.bindPopup(`<div style='text-align:center;min-width:70px;'><span style='font-size:2.2em;line-height:1;'>${flag}</span><br><b>${countryName}</b></div>`);
      marker.on('mouseover', () => marker.openPopup && marker.openPopup());
      marker.on('mouseout', () => marker.closePopup && marker.closePopup());
    }
    marker.on('mouseover', () => marker.setStyle({ radius: style.radius * 1.15 }));
    marker.on('mouseout', () => marker.setStyle({ radius: style.radius }));
    marker.on('click', () => openSidePanel(coordKey, detailsByCountry.get(key) || []));
    marker.addTo(map);
    if (flag) {
      const emojiMarker = L.marker([lat, lon], {
        icon: L.divIcon({
          className: 'country-emoji-marker',
          html: `<span>${flag}</span>`,
          iconSize: [0, 0],
          iconAnchor: [0, 0],
        }),
        interactive: false,
      });
      emojiMarker.setZIndexOffset(1000);
      emojiMarker.addTo(map);
      markersByCountry[coordKey] = { marker, emoji: emojiMarker };
    } else {
      markersByCountry[coordKey] = marker;
    }
  });
}

function renderFilters(filters) {
  const optionsDiv = document.getElementById('filter-menu-options');
  optionsDiv.innerHTML = '';
  const columns = document.createElement('div');
  columns.id = 'filter-columns';
  const categories = [
    { key: 'date', label: 'Date \uD83D\uDCC5' },
    { key: 'source', label: 'Source \uD83D\uDCF1' },
    { key: 'label', label: 'Label \uD83C\uDFF7\uFE0F' },
    { key: 'event_type', label: 'Type \uD83D\uDCDD' },
  ];
  categories.forEach(cat => {
    const col = document.createElement('div');
    col.className = 'filter-col';
    const title = document.createElement('div');
    title.className = 'filter-col-title';
    title.textContent = cat.label;
    col.appendChild(title);
    const list = document.createElement('div');
    list.className = 'filter-options-list';
    const values = filters[cat.key] || [];
    if (!values.length) {
      list.textContent = 'Aucune option.';
    } else {
      values.forEach(val => {
        const label = document.createElement('label');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = val;
        checkbox.checked = selected[cat.key].has(val);
        checkbox.addEventListener('change', () => {
          if (checkbox.checked) {
            selected[cat.key].add(val);
          } else {
            selected[cat.key].delete(val);
          }
          window.__refresh();
        });
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(val));
        list.appendChild(label);
      });
    }
    col.appendChild(list);
    columns.appendChild(col);
  });
  optionsDiv.appendChild(columns);
}

function openFilterMenu(opener) {
  filterMenu.style.display = 'block';
  if (opener === 'panel') {
    filterMenu.style.position = 'fixed';
    filterMenu.style.top = '80px';
    filterMenu.style.right = '420px';
    filterMenu.style.left = '';
    filterMenu.style.transform = 'none';
  } else {
    filterMenu.style.position = 'fixed';
    filterMenu.style.top = '60px';
    filterMenu.style.left = '80px';
    filterMenu.style.right = '';
    filterMenu.style.transform = 'none';
  }
}

function closeFilterMenu() {
  filterMenu.style.display = 'none';
}

filterBtn.addEventListener('click', () => {
  if (filterMenu.style.display === 'block') {
    closeFilterMenu();
  } else {
    openFilterMenu('global');
  }
});

if (filterBtnPanel) {
  filterBtnPanel.addEventListener('click', () => {
    if (filterMenu.style.display === 'block') {
      closeFilterMenu();
    } else {
      openFilterMenu('panel');
    }
  });
}

filterClose.addEventListener('click', closeFilterMenu);

async function init() {
  initMap();
  const [countriesResp, eventsResp] = await Promise.all([
    fetch('./static/data/countries.json'),
    fetch('./static/data/events.json'),
  ]);
  const countries = await countriesResp.json();
  const dataset = await eventsResp.json();
  const coords = countries.coordinates || {};
  const aliases = countries.aliases || {};
  const events = dataset.events || [];
  const details = dataset.details || [];
  allDetails = details;
  const detailsByCountry = new Map();
  details.forEach(d => {
    if (!d.country) return;
    if (!detailsByCountry.has(d.country)) detailsByCountry.set(d.country, []);
    detailsByCountry.get(d.country).push(d);
  });

  renderFilters(dataset.filters || {});

  const openAndRender = (value) => {
    searchQuery = value || '';
    openSearchPanel();
    renderSearchResults(searchQuery, allDetails);
  };
  if (staticSearchInputPanel) {
    staticSearchInputPanel.addEventListener('focus', () => openAndRender(staticSearchInputPanel.value));
    staticSearchInputPanel.addEventListener('click', () => openAndRender(staticSearchInputPanel.value));
    staticSearchInputPanel.addEventListener('input', () => {
      setSearchValue(staticSearchInputPanel.value);
      openAndRender(staticSearchInputPanel.value);
    });
    staticSearchInputPanel.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        setSearchValue('');
        searchQuery = '';
        closeSidePanel();
      }
    });
  }
  if (staticSearchBtn) {
    staticSearchBtn.addEventListener('click', () => {
      openSearchPanel();
      if (staticSearchInputPanel) {
        staticSearchInputPanel.focus();
        openAndRender(staticSearchInputPanel.value);
      } else {
        eventsContainer.textContent = 'Saisissez une recherche.';
      }
    });
  }

  window.__refresh = () => {
    const filtered = applyFilters(events);
    renderMarkers(filtered, coords, aliases, detailsByCountry);
    if (sidepanel.classList.contains('visible')) {
      if (searchQuery) {
        renderSearchResults(searchQuery, allDetails);
      } else if (currentCountryKey) {
        renderEvents(buildCountryEvents(currentCountryKey, detailsByCountry.get(currentCountryKey) || []));
      }
    }
  };
  window.__refresh();
}

init();
