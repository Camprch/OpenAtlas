import { initMap, markerStyle, clearMarkers, map, markersByCountry } from './static_map.js';

// Shared UI elements.
const filterMenu = document.getElementById('filter-menu');
const filterClose = document.getElementById('filter-menu-close');
const filterMenuOptions = document.getElementById('filter-menu-options');
let filterColumns = null;
const filterBtn = document.getElementById('filter-btn-global');
const sidepanel = document.getElementById('sidepanel');
const sidepanelBackdrop = document.getElementById('sidepanel-backdrop');
const sidepanelClose = document.getElementById('close-panel');
const panelCountryText = document.getElementById('panel-country-text');
const eventsContainer = document.getElementById('events');
const staticSearchInputPanel = document.getElementById('static-search-input-panel');
const staticSearchBtn = document.getElementById('static-search-btn');
const staticNonGeorefToggle = document.getElementById('static-non-georef-toggle');
const mapEl = document.getElementById('map');

const NON_GEOREF_KEY = '__NO_COUNTRY__';
const NON_GEOREF_LABEL = 'Ungeoref';

// Current filter state (multi-select across categories).
const selected = { date: new Set(), source: new Set(), label: new Set() };
let currentCountryKey = null;
let searchQuery = '';
let allDetails = [];
let cachedFilters = null;
const isMobile = window.matchMedia('(max-width: 768px)').matches;
let sidepanelHandlersBound = false;

function normalize(str) {
  // Fold accents/diacritics for a more forgiving search.
  return (str || '').normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
}

function containsQuery(text, query) {
  if (!query) return false;
  return normalize(text).includes(normalize(query));
}

function highlightQuery(text, query) {
  // Wrap matching ranges with a highlighted span without altering original casing.
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
    result += raw.slice(i, found) + `<span class="search-hl">` + raw.slice(found, found + normQuery.length) + '</span>';
    i = found + normQuery.length;
  }
  return result;
}

function toggleTextBlock(textEl) {
  if (!textEl) return;
  if (textEl.classList.contains('is-collapsed')) {
    textEl.classList.remove('is-collapsed');
    textEl.classList.add('is-open');
  } else {
    textEl.classList.add('is-collapsed');
    textEl.classList.remove('is-open');
  }
}

function isBlankSidepanelTarget(target) {
  if (!(target instanceof Element)) return false;
  if (target.id === 'sidepanel' || target.id === 'sidepanel-content' || target.id === 'events') {
    return true;
  }
  return false;
}

function bindSidepanelCloseOnEmpty() {
  if (sidepanelHandlersBound) return;
  sidepanel.onclick = (e) => {
    if (isBlankSidepanelTarget(e.target)) {
      closeSidePanel();
    }
  };
  const sidepanelContent = document.getElementById('sidepanel-content');
  if (sidepanelContent) {
    sidepanelContent.onclick = (e) => {
      if (isBlankSidepanelTarget(e.target)) {
        closeSidePanel();
      }
    };
  }
  sidepanelHandlersBound = true;
}
function applyFilters(events) {
  // Apply global filters to the map markers list.
  return events.filter(e => {
    if (selected.date.size && (!e.date || !selected.date.has(e.date))) return false;
    if (selected.source.size && (!e.source || !selected.source.has(e.source))) return false;
    if (selected.label.size && (!e.label || !selected.label.has(e.label))) return false;
    // event_type filter removed
    return true;
  });
}

function applyFiltersToDetails(details) {
  // Apply global filters to detailed rows used by the sidepanel/search.
  return details.filter(item => {
    if (selected.date.size && (!item.timestamp || !selected.date.has(item.timestamp))) return false;
    if (selected.source.size && (!item.source || !selected.source.has(item.source))) return false;
    if (selected.label.size && (!item.label || !selected.label.has(item.label))) return false;
    // event_type filter removed
    return true;
  });
}

function buildCountryEvents(countryKey, details) {
  // Group detail rows by (region, location) to match the panel layout.
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
    // Newest first inside each bucket.
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
  // Re-use the sidepanel as a global search surface.
  closeFilterMenu();
  panelCountryText.textContent = 'Search Results';
  currentCountryKey = null;
  sidepanel.classList.add('visible');
  sidepanelBackdrop.classList.add('visible');
}

function renderSearchResults(query, details) {
  // Full-text search over detail rows with highlighted matches.
  const q = (query || '').trim();
  if (!q) {
    eventsContainer.textContent = 'Enter a search query.';
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
    ].filter(Boolean).join(' ');
    return containsQuery(haystack, q);
  });
  if (!filtered.length) {
    eventsContainer.textContent = 'No results found.';
    return;
  }
  const itemsHtml = filtered.map(item => {
    const title = highlightQuery(item.title || '(No title)', q);
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
    if (where) metaParts.push(`<span class="evt-location">${highlightQuery(where, q)}</span>`);
    if (postLink) metaParts.push(`<span class="evt-link">${postLink}</span>`);
    const meta = metaParts.length ? `<div class="evt-meta">${metaParts.join('')}</div>` : '';
    return `
            <li class="event" data-msg-id="${item.id}">
                <div class="evt-title">${title}</div>
                <div class="evt-text is-open">
                    ${fullText}
                    ${meta}
                </div>
            </li>
        `;
  }).join('');
  eventsContainer.innerHTML = `<div class="search-results-count">${filtered.length} résultat(s)</div><ul class="event-list search-results">${itemsHtml}</ul>`;
  eventsContainer.querySelectorAll('.evt-title').forEach(titleEl => {
    if (!titleEl.dataset.listener) {
      // Toggle per-item text display without re-rendering the list.
      titleEl.addEventListener('click', function(e) {
        e.stopPropagation();
        const text = this.nextElementSibling;
        toggleTextBlock(text);
      });
      titleEl.dataset.listener = '1';
    }
  });
}

function renderEvents(data) {
  // Render the sidepanel grouped by zone.
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
      return `\n            <li class="event" data-msg-id="${m.id}">\n                <div class="evt-title" data-zone="${idx}" data-msg="${mIdx}">${title}</div>\n                <div class="evt-text is-collapsed">\n                    ${fullText}\n                    <div class="evt-meta">\n                        <span class="evt-source">${m.source}${orientation}</span>\n                        <span class="evt-time">${timeStr}</span>\n                        <span class="evt-link">${postLink}</span>\n                    </div>\n                </div>\n            </li>\n        `;
    }).join('');
    return `\n            <section class="zone-block">\n                <h4 class="zone-header" data-idx="${idx}">\n                    <span class="toggle-btn">▶</span> ${header}\n                    <span class="evt-count">(${zone.messages_count})</span>\n                </h4>\n                <ul class="event-list is-collapsed" id="zone-list-${idx}">\n                    ${msgs}\n                </ul>\n            </section>\n        `;
  }).join('');
  eventsContainer.innerHTML = html;
  data.zones.forEach((zone, idx) => {
    const headerEl = document.querySelector(`.zone-header[data-idx='${idx}']`);
    const listEl = document.getElementById(`zone-list-${idx}`);
    const btn = headerEl.querySelector('.toggle-btn');
    headerEl.addEventListener('click', () => {
      if (listEl.classList.contains('is-collapsed')) {
        listEl.classList.remove('is-collapsed');
        btn.textContent = '▼';
        // Attach message toggles lazily to keep initial render cheap.
        listEl.querySelectorAll('.evt-title').forEach(titleEl => {
          if (!titleEl.dataset.listener) {
            titleEl.addEventListener('click', function(e) {
              e.stopPropagation();
              const text = this.nextElementSibling;
              toggleTextBlock(text);
            });
            titleEl.dataset.listener = '1';
          }
        });
      } else {
        listEl.classList.add('is-collapsed');
        btn.textContent = '▶';
      }
    });
  });
}

function openSidePanel(countryKey, details) {
  // Open sidepanel focused on a specific country (emoji + name if present).
  if (countryKey === NON_GEOREF_KEY) {
    panelCountryText.textContent = NON_GEOREF_LABEL;
    currentCountryKey = countryKey;
    setSearchValue('');
    searchQuery = '';
    renderEvents(buildCountryEvents(countryKey, details));
    sidepanel.classList.add('visible');
    sidepanelBackdrop.classList.add('visible');
    return;
  }
  const rawName = countryKey || '';
  const flagMatch = rawName.match(/^(\p{Regional_Indicator}{2})/u);
  const flag = flagMatch ? flagMatch[1] : '';
  const name = rawName.replace(/^[^\p{L}\p{N}]+/u, '').trim();
  panelCountryText.textContent = '';
  if (flag) {
    const flagSpan = document.createElement('span');
    flagSpan.textContent = `${flag} `;
    panelCountryText.appendChild(flagSpan);
  }
  panelCountryText.appendChild(document.createTextNode(name || rawName));
  currentCountryKey = countryKey;
  setSearchValue('');
  searchQuery = '';
  renderEvents(buildCountryEvents(countryKey, details));
  sidepanel.classList.add('visible');
  sidepanelBackdrop.classList.add('visible');
  bindSidepanelCloseOnEmpty();
}

function closeSidePanel() {
  sidepanel.classList.remove('visible');
  sidepanelBackdrop.classList.remove('visible');
}

sidepanelClose.addEventListener('click', closeSidePanel);
sidepanelBackdrop.addEventListener('click', closeSidePanel);

function renderMarkers(events, coords, aliases, detailsByCountry) {
  // Rebuild map markers from the currently filtered list.
  clearMarkers();
  const counts = new Map();
  events.forEach(e => {
    if (!e.country) return;
    const key = e.country;
    counts.set(key, (counts.get(key) || 0) + 1);
  });

  counts.forEach((count, key) => {
    // Resolve alias -> canonical country key if needed.
    let coordKey = key;
    if (!coords[coordKey] && aliases[key] && coords[aliases[key]]) {
      coordKey = aliases[key];
    }
    if (!coords[coordKey]) return;
    const [lat, lon] = coords[coordKey];
    const style = markerStyle(count);
    const hitRadius = style.radius + (isMobile ? 10 : 6);
    const hitCircle = L.circleMarker([lat, lon], {
      radius: hitRadius,
      color: "transparent",
      fillColor: "transparent",
      fillOpacity: 0,
      weight: 0,
      interactive: true,
      pane: "markerPane",
    });
    const marker = L.circleMarker([lat, lon], style);
    let flag = '';
    // Attempt to extract the flag emoji from the country label.
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
      marker.bindPopup(`<div class="map-popup"><span class="map-popup-flag">${flag}</span><br><b>${countryName}</b></div>`);
      marker.on('mouseover', () => marker.openPopup && marker.openPopup());
      marker.on('mouseout', () => marker.closePopup && marker.closePopup());
    }
    marker.on('mouseover', () => marker.setStyle({ radius: style.radius * 1.15 }));
    marker.on('mouseout', () => marker.setStyle({ radius: style.radius }));
    marker.on('click', () => openSidePanel(coordKey, detailsByCountry.get(key) || []));
    hitCircle.on('click', () => openSidePanel(coordKey, detailsByCountry.get(key) || []));
    hitCircle.on('mouseover', () => marker.setStyle({ radius: style.radius * 1.15 }));
    hitCircle.on('mouseout', () => marker.setStyle({ radius: style.radius }));
    hitCircle.addTo(map);
    marker.addTo(map);
    if (flag) {
      // Separate emoji marker so the circle remains clickable underneath.
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
      markersByCountry[coordKey] = { marker, emoji: emojiMarker, hit: hitCircle };
    } else {
      markersByCountry[coordKey] = { marker, hit: hitCircle };
    }
  });
}

function renderFilters(filters) {
  // Build the filter menu UI from the dataset's filter lists.
  const optionsDiv = document.getElementById('filter-menu-options');
  optionsDiv.innerHTML = '';
  const columns = document.createElement('div');
  columns.id = 'filter-columns';
  filterColumns = columns;
  const categories = [
    { key: 'active', label: 'Activ \u2728' },
    { key: 'date', label: 'Date \uD83D\uDCC5' },
    { key: 'source', label: 'Source \uD83D\uDCF1' },
    { key: 'label', label: 'Label \uD83C\uDFF7\uFE0F' },
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
    if (cat.key === 'active') {
      const activePairs = [];
      for (const k of ['date', 'source', 'label']) {
        const vals = Array.from(selected[k] || []);
        for (const v of vals) {
          activePairs.push({ key: k, value: v });
        }
      }
      if (activePairs.length === 0) {
        list.textContent = 'Aucun filtre actif.';
      } else {
        activePairs.forEach(item => {
          const chip = document.createElement('button');
          chip.type = 'button';
          chip.className = 'filter-active-chip';
          chip.textContent = item.value;
          chip.addEventListener('click', (e) => {
            if (e && e.stopPropagation) e.stopPropagation();
            selected[item.key].delete(item.value);
            window.__refresh();
            renderFilters(filters);
          });
          list.appendChild(chip);
        });
      }
      col.appendChild(list);
      columns.appendChild(col);
      return;
    }
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
          // Update the Set, then refresh map + sidepanel.
          if (checkbox.checked) {
            selected[cat.key].add(val);
          } else {
            selected[cat.key].delete(val);
          }
          window.__refresh();
          renderFilters(filters);
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

function openFilterMenu() {
  // Use a single placement for all openers.
  filterMenu.style.display = 'flex';
  if (cachedFilters) {
    renderFilters(cachedFilters);
  }
  if (isMobile) {
    filterMenu.style.position = 'fixed';
    filterMenu.style.top = '70px';
    filterMenu.style.left = '10px';
    filterMenu.style.right = '10px';
    filterMenu.style.transform = 'none';
    return;
  }
  filterMenu.style.position = 'fixed';
  filterMenu.style.top = '60px';
  filterMenu.style.left = '80px';
  filterMenu.style.right = '';
  filterMenu.style.transform = 'none';
}

function closeFilterMenu() {
  filterMenu.style.display = 'none';
}

function handleFilterMenuClick(e) {
  const target = e.target;
  if (target instanceof Element && target.closest('.filter-active-chip')) {
    return;
  }
  if (
    target === filterMenu ||
    target === filterMenuOptions ||
    target === filterColumns ||
    (target instanceof Element && target.classList.contains('filter-options-list'))
  ) {
    closeFilterMenu();
  }
}

filterBtn.addEventListener('click', () => {
  if (filterMenu.style.display !== 'none' && filterMenu.style.display !== '') {
    closeFilterMenu();
  } else {
    openFilterMenu();
  }
});


filterClose.addEventListener('click', closeFilterMenu);
filterMenu.addEventListener('click', handleFilterMenuClick);
document.addEventListener('click', (e) => {
  if (filterMenu.style.display === 'none' || filterMenu.style.display === '') return;
  const target = e.target;
  if (target === filterBtn || filterBtn.contains(target)) return;
  if (target === filterMenu || filterMenu.contains(target)) return;
  closeFilterMenu();
});

// Close filter menu when clicking on the map
if (mapEl) {
  mapEl.addEventListener('mousedown', () => {
    if (filterMenu.style.display !== 'none' && filterMenu.style.display !== '') {
      closeFilterMenu();
    }
  });
}

async function init() {
  // Load data and render initial state.
  initMap();
  blockPinchOnElement(sidepanel);
  blockPinchOnElement(filterMenu);
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
    const key = d.country || NON_GEOREF_KEY;
    if (!detailsByCountry.has(key)) detailsByCountry.set(key, []);
    detailsByCountry.get(key).push(d);
  });

  renderFilters(dataset.filters || {});
  cachedFilters = dataset.filters || {};

  const openAndRender = (value) => {
    searchQuery = value || '';
    openSearchPanel();
    renderSearchResults(searchQuery, allDetails);
  };
  if (staticSearchInputPanel) {
    // Mirror inputs between header search and sidepanel search.
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
      if (isMobile && sidepanel.classList.contains('visible')) {
        closeSidePanel();
        return;
      }
      openSearchPanel();
      if (staticSearchInputPanel) {
        staticSearchInputPanel.focus();
        openAndRender(staticSearchInputPanel.value);
      } else {
        eventsContainer.textContent = 'Saisissez une recherche.';
      }
    });
  }
  if (staticNonGeorefToggle) {
    staticNonGeorefToggle.addEventListener('click', () => {
      if (isMobile && sidepanel.classList.contains('visible')) {
        closeSidePanel();
        return;
      }
      openSidePanel(NON_GEOREF_KEY, detailsByCountry.get(NON_GEOREF_KEY) || []);
    });
  }

  window.__refresh = () => {
    // Refresh all UI parts that depend on filter state.
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

function isAllowedScrollTarget(target) {
  if (!mapEl || !target) return false;
  const el = (target instanceof Element) ? target : target.parentElement;
  if (!el) return false;
  return (
    mapEl.contains(el) ||
    el.closest('#sidepanel-content') ||
    el.closest('#filter-menu') ||
    el.closest('#filter-menu-options') ||
    el.closest('.filter-options-list')
  );
}

function getScrollTargetFromEvent(e) {
  if (e && e.touches && e.touches.length) {
    const touch = e.touches[0];
    const el = document.elementFromPoint(touch.clientX, touch.clientY);
    if (el) return el;
  }
  return e ? e.target : null;
}

function isSidepanelOpen() {
  return sidepanel && sidepanel.classList.contains('visible');
}

function isFilterMenuOpen() {
  if (!filterMenu) return false;
  return filterMenu.style.display !== 'none' && filterMenu.style.display !== '';
}

function blockPinchOnElement(el) {
  if (!el) return;
  ['gesturestart', 'gesturechange', 'gestureend'].forEach(evt => {
    el.addEventListener(evt, (e) => e.preventDefault(), { passive: false });
  });
  el.addEventListener('touchstart', (e) => {
    if (e.touches && e.touches.length > 1) e.preventDefault();
  }, { passive: false });
  el.addEventListener('touchmove', (e) => {
    if (e.touches && e.touches.length > 1) e.preventDefault();
  }, { passive: false });
}

function isZoomAllowed(target) {
  if (isSidepanelOpen() || isFilterMenuOpen()) return false;
  const el = (target instanceof Element) ? target : target?.parentElement;
  if (!el) return false;
  return mapEl && mapEl.contains(el);
}

// Zoom/scroll blocking removed.
