// Ajoute la fonction fetchDates pour charger les dates depuis l'API
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
// Synchronisation globale des filtres sélectionnés
if (!window.selectedFilters) {
    window.selectedFilters = {
        date: [],
        source: [],
        label: [],
        event_type: []
    };
}


// Gestion du menu de filtres synchronisé (header & sidepanel) + affichage dynamique des cases à cocher
const FILTER_VALUES = {
    date: [], // sera chargé dynamiquement
    source: [], // sera chargé dynamiquement
    label: [], // sera chargé dynamiquement
    event_type: [] // sera chargé dynamiquement
};

async function fetchEventTypes() {
    try {
        const resp = await fetch("/api/event_types");
        const data = await resp.json();
        if (Array.isArray(data)) {
            FILTER_VALUES.event_type = data;
        } else {
            FILTER_VALUES.event_type = [];
        }
    } catch (e) {
        FILTER_VALUES.event_type = [];
    }
}

async function fetchLabels() {
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


// Nouvelle version : affiche les 4 catégories côte à côte, chaque colonne avec ses options
export async function renderAllFilterOptions() {
    // Charge dynamiquement toutes les valeurs si besoin
    const fetchers = [];
    if (FILTER_VALUES.date.length === 0) fetchers.push(fetchDates());
    if (FILTER_VALUES.source.length === 0) fetchers.push(fetchSources());
    if (FILTER_VALUES.label.length === 0) fetchers.push(fetchLabels());
    if (FILTER_VALUES.event_type.length === 0) fetchers.push(fetchEventTypes());
    await Promise.all(fetchers);

    const optionsDiv = document.getElementById('filter-menu-options');
    optionsDiv.innerHTML = '';

    // Structure : 4 colonnes côte à côte
    const columns = document.createElement('div');
    columns.id = 'filter-columns';
    const categories = [
        { key: 'date', label: 'Date' },
        { key: 'source', label: 'Source' },
        { key: 'label', label: 'Label' },
        { key: 'event_type', label: 'Type' }
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
                    if (checkbox.checked) {
                        if (!window.selectedFilters[cat.key].includes(val)) {
                            window.selectedFilters[cat.key].push(val);
                        }
                    } else {
                        window.selectedFilters[cat.key] = window.selectedFilters[cat.key].filter(v => v !== val);
                    }
                    // Synchronise tous les checkboxes de même valeur/catégorie
                    document.querySelectorAll('.filter-options-list input[type=checkbox][value="' + val + '"]')
                        .forEach(cb => { if (cb !== checkbox) cb.checked = checkbox.checked; });
                    const selectedDates = window.selectedFilters.date;
                    const selectedSources = window.selectedFilters.source;
                    const selectedLabels = window.selectedFilters.label;
                    const selectedEventTypes = window.selectedFilters.event_type;
                    await loadActiveCountries(
                        selectedDates.length > 0 ? selectedDates : null,
                        selectedSources.length > 0 ? selectedSources : null,
                        selectedLabels.length > 0 ? selectedLabels : null,
                        selectedEventTypes.length > 0 ? selectedEventTypes : null
                    );
                    // Recharge le panneau latéral si ouvert et un pays sélectionné
                    const sidepanel = document.getElementById('sidepanel');
                    if (sidepanel && sidepanel.classList.contains('visible') && window.currentCountry) {
                        await loadEvents(
                            window.currentCountry,
                            selectedDates.length > 0 ? selectedDates[0] : null,
                            selectedSources.length > 0 ? selectedSources : null,
                            selectedLabels.length > 0 ? selectedLabels : null,
                            selectedEventTypes.length > 0 ? selectedEventTypes : null
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
        filterMenu.style.display = 'block';
        lastOpener = opener;
        window.lastFilterOpener = opener;
        if (opener === 'panel') {
            // Affichage centré dans le panneau latéral
            const sidepanel = document.getElementById('sidepanel');
            if (sidepanel) {
                filterMenu.style.position = 'absolute';
                filterMenu.style.top = '100px';
                filterMenu.style.left = '50%';
                filterMenu.style.transform = 'translateX(-50%)';
                sidepanel.appendChild(filterMenu);
            }
        } else {
            // Affichage classique sur la carte principale
            filterMenu.style.position = 'fixed';
            filterMenu.style.top = '60px';
            filterMenu.style.left = '80px';
            filterMenu.style.transform = 'none';
            document.body.appendChild(filterMenu);
        }
        // Affiche toutes les options de filtres en colonnes
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
    // Fermer le menu si clic en dehors
    document.addEventListener('mousedown', (e) => {
        if (filterMenu.style.display === 'block' && !filterMenu.contains(e.target) && e.target !== filterBtnGlobal && e.target !== filterBtnPanel) {
            closeMenu();
        }
    });
}
