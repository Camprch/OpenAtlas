import { initMap, markerStyle, clearMarkers, map, markersByCountry } from './static_map.js';
import { renderFilters, setupFilterMenuHandlers } from './static_filters.js';
import { buildCountryEvents, renderEvents } from './static_sidepanel.js';
import { renderSearchResults } from './static_search.js';
import { renderMarkers } from './static_map_ui.js';

const filterMenu = document.getElementById('filter-menu');
const filterClose = document.getElementById('filter-menu-close');
const filterMenuOptions = document.getElementById('filter-menu-options');
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

const selected = { date: new Set(), source: new Set(), label: new Set() };
let currentCountryKey = null;
let searchQuery = '';
let allDetails = [];
let cachedFilters = null;
let sidepanelHandlersBound = false;
let refreshFn = () => {};

const isMobile = () => window.matchMedia('(max-width: 768px)').matches;

function setSearchValue(value) {
  if (staticSearchInputPanel) staticSearchInputPanel.value = value;
}

function openSearchPanel() {
  closeFilterMenu();
  panelCountryText.textContent = 'Search Results';
  currentCountryKey = null;
  sidepanel.classList.add('visible');
  sidepanelBackdrop.classList.add('visible');
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
  return events.filter(e => {
    if (selected.date.size && (!e.date || !selected.date.has(e.date))) return false;
    if (selected.source.size && (!e.source || !selected.source.has(e.source))) return false;
    if (selected.label.size && (!e.label || !selected.label.has(e.label))) return false;
    return true;
  });
}

function applyFiltersToDetails(details) {
  return details.filter(item => {
    if (selected.date.size && (!item.timestamp || !selected.date.has(item.timestamp))) return false;
    if (selected.source.size && (!item.source || !selected.source.has(item.source))) return false;
    if (selected.label.size && (!item.label || !selected.label.has(item.label))) return false;
    return true;
  });
}

function openSidePanel(countryKey, details) {
  if (countryKey === NON_GEOREF_KEY) {
    panelCountryText.textContent = NON_GEOREF_LABEL;
    currentCountryKey = countryKey;
    setSearchValue('');
    searchQuery = '';
    renderEvents(buildCountryEvents(countryKey, details, selected), eventsContainer);
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
  renderEvents(buildCountryEvents(countryKey, details, selected), eventsContainer);
  sidepanel.classList.add('visible');
  sidepanelBackdrop.classList.add('visible');
  bindSidepanelCloseOnEmpty();
}

function closeSidePanel() {
  sidepanel.classList.remove('visible');
  sidepanelBackdrop.classList.remove('visible');
}

function openFilterMenu() {
  filterMenu.style.display = 'flex';
  if (cachedFilters) {
    renderFilters(cachedFilters, selected, refreshFn);
  }
  if (isMobile()) {
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

function setupSidepanelHandlers() {
  sidepanelClose.addEventListener('click', closeSidePanel);
  sidepanelBackdrop.addEventListener('click', closeSidePanel);
}

function setupSearchHandlers(openAndRender, detailsByCountry) {
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
      if (isMobile() && sidepanel.classList.contains('visible')) {
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
      if (isMobile() && sidepanel.classList.contains('visible')) {
        closeSidePanel();
        return;
      }
      openSidePanel(NON_GEOREF_KEY, detailsByCountry.get(NON_GEOREF_KEY) || []);
    });
  }
}

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
    const key = d.country || NON_GEOREF_KEY;
    if (!detailsByCountry.has(key)) detailsByCountry.set(key, []);
    detailsByCountry.get(key).push(d);
  });

  refreshFn = () => {
    const filtered = applyFilters(events);
    renderMarkers(filtered, coords, aliases, detailsByCountry, {
      markerStyle,
      clearMarkers,
      map,
      markersByCountry,
      isMobile,
      openSidePanel,
    });
    if (sidepanel.classList.contains('visible')) {
      if (searchQuery) {
        renderSearchResults(searchQuery, allDetails, eventsContainer, applyFiltersToDetails);
      } else if (currentCountryKey) {
        renderEvents(buildCountryEvents(currentCountryKey, detailsByCountry.get(currentCountryKey) || [], selected), eventsContainer);
      }
    }
  };

  cachedFilters = dataset.filters || {};
  renderFilters(cachedFilters, selected, refreshFn);

  const openAndRender = (value) => {
    searchQuery = value || '';
    openSearchPanel();
    renderSearchResults(searchQuery, allDetails, eventsContainer, applyFiltersToDetails);
  };

  setupSearchHandlers(openAndRender, detailsByCountry);

  window.__refresh = refreshFn;
  refreshFn();
}

setupSidepanelHandlers();
setupFilterMenuHandlers({
  filterMenu,
  filterBtn,
  filterClose,
  filterMenuOptions,
  mapEl,
  onOpen: openFilterMenu,
  onClose: closeFilterMenu,
});
init();
