// Fetch available dates from the API
async function fetchDates() {
    try {
        const resp = await fetch("/api/dates");
        const data = await resp.json();
        if (Array.isArray(data)) {
            FILTER_VALUES.date = data;
        } else if (data && Array.isArray(data.dates)) {
            FILTER_VALUES.date = data.dates;
        } else {
            FILTER_VALUES.date = [];
        }
    } catch (e) {
        FILTER_VALUES.date = [];
    }
}
// modules/filter.js


window.lastFilterOpener = "global";
// Global sync object for selected filters across UI components
if (!window.selectedFilters) {
    window.selectedFilters = {
        date: [],
        source: [],
        label: []
    };
}


// Filter values are loaded on demand and rendered in a shared menu
const FILTER_VALUES = {
    date: [], // sera chargé dynamiquement
    source: [], // sera chargé dynamiquement
    label: [], // sera chargé dynamiquement
    event_type: [] // removed
};

// event_type filter removed (no-op)

async function fetchLabels() {
    // Load label values from the API
    try {
        const resp = await fetch("/api/labels");
        const data = await resp.json();
        if (Array.isArray(data)) {
            FILTER_VALUES.label = data;
        } else {
            FILTER_VALUES.label = [];
        }
    } catch (e) {
        FILTER_VALUES.label = [];
    }
}

async function fetchSources() {
    // Load human-readable sources from the API
    try {
        const resp = await fetch("/api/sources");
        const data = await resp.json();
        if (Array.isArray(data)) {
            FILTER_VALUES.source = data;
        } else {
            FILTER_VALUES.source = [];
        }
    } catch (e) {
        FILTER_VALUES.source = [];
    }
}

import { loadActiveCountries } from "./countries.js";
import { currentCountry } from "./sidepanel.js";
import { loadEvents } from "./events.js";


// Render the filter menu with four categories side by side
export async function renderAllFilterOptions() {
    // Load values only when needed
    const fetchers = [];
    if (FILTER_VALUES.date.length === 0) fetchers.push(fetchDates());
    if (FILTER_VALUES.source.length === 0) fetchers.push(fetchSources());
    if (FILTER_VALUES.label.length === 0) fetchers.push(fetchLabels());
    // event_type filter removed
    await Promise.all(fetchers);

    const optionsDiv = document.getElementById('filter-menu-options');
    optionsDiv.innerHTML = '';

    // Layout: four columns of filter options
    const columns = document.createElement('div');
    columns.id = 'filter-columns';
    const categories = [
        { key: 'date', label: 'Date 🗓️' },
        { key: 'source', label: 'Source 📡' },
        { key: 'label', label: 'Label 🏷️' },
    ];
    for (const cat of categories) {
        const col = document.createElement('div');
        col.className = 'filter-col';
        const title = document.createElement('div');
        title.className = 'filter-col-title';
        title.textContent = cat.label;
        col.appendChild(title);
        const list = document.createElement('div');
        list.className = 'filter-options-list';
        const values = FILTER_VALUES[cat.key] || [];
        if (!window.selectedFilters[cat.key]) window.selectedFilters[cat.key] = [];
        if (values.length === 0) {
            list.textContent = 'Aucune option.';
        } else {
            for (const val of values) {
                const label = document.createElement('label');
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.value = val;
                checkbox.checked = window.selectedFilters[cat.key].includes(val);
                label.appendChild(checkbox);
                label.appendChild(document.createTextNode(val));
                list.appendChild(label);

                checkbox.addEventListener('change', async () => {
                    if (!window.selectedFilters[cat.key]) window.selectedFilters[cat.key] = [];
                    // Update selected filters for this category
                    if (checkbox.checked) {
                        if (!window.selectedFilters[cat.key].includes(val)) {
                            window.selectedFilters[cat.key].push(val);
                        }
                    } else {
                        window.selectedFilters[cat.key] = window.selectedFilters[cat.key].filter(v => v !== val);
                    }
                    // Keep same-value checkboxes in sync across menus
                    document.querySelectorAll('.filter-options-list input[type=checkbox][value="' + val + '"]')
                        .forEach(cb => { if (cb !== checkbox) cb.checked = checkbox.checked; });
                    const selectedDates = window.selectedFilters.date;
                    const selectedSources = window.selectedFilters.source;
                    const selectedLabels = window.selectedFilters.label;
        // event_type filter removed
                    // Refresh map markers based on current filters
                    await loadActiveCountries(
                        selectedDates.length > 0 ? selectedDates : null,
                        selectedSources.length > 0 ? selectedSources : null,
                        selectedLabels.length > 0 ? selectedLabels : null,
                        null
                    );
                    // Reload side panel if it is visible and a country is selected
                    const sidepanel = document.getElementById('sidepanel');
                    if (sidepanel && sidepanel.classList.contains('visible') && window.currentCountry) {
                        await loadEvents(
                            window.currentCountry,
                            selectedDates.length > 0 ? selectedDates[0] : null,
                            selectedSources.length > 0 ? selectedSources : null,
                            selectedLabels.length > 0 ? selectedLabels : null,
                            null
                        );
                    }
                });
            }
        }
        col.appendChild(list);
        columns.appendChild(col);
    }
    optionsDiv.appendChild(columns);
}


export function setupFilterMenuSync() {
    const filterBtnGlobal = document.getElementById('filter-btn-global');
    const filterBtnPanel = document.getElementById('filter-btn-panel');
    const filterMenu = document.getElementById('filter-menu');
    const filterMenuClose = document.getElementById('filter-menu-close');
    let lastOpener = null; // "global" ou "panel"

    function openMenu(opener) {
        // Position the menu based on where it was opened from
        filterMenu.style.display = 'flex';
        lastOpener = opener;
        window.lastFilterOpener = opener;
        if (opener === 'panel') {
            // Align next to the side panel
            filterMenu.style.position = 'fixed';
            filterMenu.style.top = '80px';
            filterMenu.style.right = '420px'; // largeur du sidepanel
            filterMenu.style.left = '';
            filterMenu.style.transform = 'none';
            document.body.appendChild(filterMenu);
        } else {
            // Default placement on the main map
            filterMenu.style.position = 'fixed';
            filterMenu.style.top = '60px';
            filterMenu.style.left = '80px';
            filterMenu.style.right = '';
            filterMenu.style.transform = 'none';
            document.body.appendChild(filterMenu);
        }
        // Render filter options in columns
        renderAllFilterOptions();
    }
    function closeMenu() {
        filterMenu.style.display = 'none';
        lastOpener = null;
    }
    if (filterBtnGlobal) {
        filterBtnGlobal.addEventListener('click', () => {
            if (filterMenu.style.display === 'block' && lastOpener === 'global') {
                closeMenu();
            } else {
                openMenu('global');
            }
        });
    }
    if (filterBtnPanel) {
        filterBtnPanel.addEventListener('click', () => {
            if (filterMenu.style.display === 'block' && lastOpener === 'panel') {
                closeMenu();
            } else {
                openMenu('panel');
            }
        });
    }
    if (filterMenuClose) {
        filterMenuClose.addEventListener('click', closeMenu);
    }
    function isMenuOpen() {
        const inline = filterMenu.style.display;
        if (inline) return inline !== 'none';
        return window.getComputedStyle(filterMenu).display !== 'none';
    }

    // Fermer le menu si clic en dehors
    document.addEventListener('mousedown', (e) => {
        if (isMenuOpen() && !filterMenu.contains(e.target) && e.target !== filterBtnGlobal && e.target !== filterBtnPanel) {
            closeMenu();
        }
    });

    // Close filter menu when clicking on the map
    const mapEl = document.getElementById('map');
    if (mapEl) {
        mapEl.addEventListener('mousedown', () => {
            if (isMenuOpen()) {
                closeMenu();
            }
        });
    }
}
