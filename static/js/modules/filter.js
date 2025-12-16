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
        label: []
    };
}

// Gestion du menu de filtres synchronisé (header & sidepanel) + affichage dynamique des cases à cocher

const FILTER_VALUES = {
    date: [], // sera chargé dynamiquement
    source: [], // sera chargé dynamiquement
    label: [], // sera chargé dynamiquement
    event_type: ["Attaque", "Manifestation", "Annonce"]
};

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

export async function renderFilterOptions(category) {
    // Charge dynamiquement les valeurs de label si besoin
    if (category === 'label' && FILTER_VALUES.label.length === 0) {
        await fetchLabels();
    }
    const optionsDiv = document.getElementById('filter-menu-options');
    optionsDiv.innerHTML = '';
    if (category === 'date' && FILTER_VALUES.date.length === 0) {
        await fetchDates();
    }
    if (category === 'source' && FILTER_VALUES.source.length === 0) {
        await fetchSources();
    }
    const values = FILTER_VALUES[category] || [];
    if (values.length === 0) {
        optionsDiv.textContent = 'Aucune option.';
        return;
    }
    for (const val of values) {
        const label = document.createElement('label');
        label.style.display = 'block';
        label.style.marginBottom = '6px';
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = val;
        checkbox.style.marginRight = '8px';
        // Synchronise l'état coché avec window.selectedFilters
        checkbox.checked = window.selectedFilters[category] && window.selectedFilters[category].includes(val);
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(val));
        optionsDiv.appendChild(label);

        checkbox.addEventListener('change', async () => {
            if (checkbox.checked) {
                if (!window.selectedFilters[category].includes(val)) {
                    window.selectedFilters[category].push(val);
                }
            } else {
                window.selectedFilters[category] = window.selectedFilters[category].filter(v => v !== val);
            }
            document.querySelectorAll('input[type=checkbox][value="' + val + '"]')
                .forEach(cb => { if (cb !== checkbox) cb.checked = checkbox.checked; });
            const selectedDates = window.selectedFilters.date;
            const selectedSources = window.selectedFilters.source;
            const selectedLabels = window.selectedFilters.label;
            await loadActiveCountries(
                selectedDates.length > 0 ? selectedDates : null,
                selectedSources.length > 0 ? selectedSources : null,
                selectedLabels.length > 0 ? selectedLabels : null
            );
            if (window.lastFilterOpener === "panel" && currentCountry) {
                const allDates = FILTER_VALUES.date;
                const allChecked = selectedDates.length === allDates.length;
                if (selectedDates.length === 0 || allChecked) {
                    await loadEvents(currentCountry, null, selectedSources.length > 0 ? selectedSources : null, selectedLabels.length > 0 ? selectedLabels : null);
                } else {
                    await loadEvents(currentCountry, selectedDates[0], selectedSources.length > 0 ? selectedSources : null, selectedLabels.length > 0 ? selectedLabels : null);
                }
            }
        });
    }
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
        // Affiche la catégorie 'source' par défaut à chaque ouverture
        renderFilterOptions('source');
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

    // Ajout de l'écoute sur les boutons de catégorie
    const categoryBtns = document.querySelectorAll('.filter-category-btn');
    categoryBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            const cat = btn.getAttribute('data-category');
            await renderFilterOptions(cat);
        });
    });
}
