// modules/filter.js
// Gestion du menu de filtres synchronisé (header & sidepanel) + affichage dynamique des cases à cocher


const FILTER_VALUES = {
    date: [], // sera chargé dynamiquement
    source: ["Twitter", "Telegram", "RSS"],
    label: ["Sécurité", "Politique", "Économie"],
    event_type: ["Attaque", "Manifestation", "Annonce"]
};

async function fetchDates() {
    try {
        const resp = await fetch("/api/dates");
        const data = await resp.json();
        // L'API peut retourner un tableau ou un objet {dates: [...]}
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


import { loadActiveCountries } from "./countries.js";
import { currentCountry } from "./sidepanel.js";
import { loadEvents } from "./events.js";

export async function renderFilterOptions(category) {
    const optionsDiv = document.getElementById('filter-menu-options');
    optionsDiv.innerHTML = '';
    if (category === 'date' && FILTER_VALUES.date.length === 0) {
        await fetchDates();
    }
    const values = FILTER_VALUES[category] || [];
    if (values.length === 0) {
        optionsDiv.textContent = 'Aucune option.';
        return;
    }
    values.forEach(val => {
        const label = document.createElement('label');
        label.style.display = 'block';
        label.style.marginBottom = '6px';
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = val;
        checkbox.style.marginRight = '8px';
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(val));
        optionsDiv.appendChild(label);
        // Ajout du comportement pour la catégorie date
        if (category === 'date') {
            checkbox.addEventListener('change', async () => {
                // Récupère toutes les dates cochées
                const checkedBoxes = optionsDiv.querySelectorAll('input[type=checkbox]:checked');
                const selectedDates = Array.from(checkedBoxes).map(cb => cb.value);
                // Si aucun filtre n'est coché, on affiche tout (pas de filtre)
                await loadActiveCountries(selectedDates.length > 0 ? selectedDates : null);
                // Synchronise aussi le contenu du sidepanel si ouvert
                if (currentCountry) {
                    // Si toutes les dates sont cochées, ou aucune, on affiche tout
                    const allDates = FILTER_VALUES.date;
                    const allChecked = selectedDates.length === allDates.length;
                    if (selectedDates.length === 0 || allChecked) {
                        await loadEvents(currentCountry, null);
                    } else {
                        await loadEvents(currentCountry, selectedDates[0]);
                    }
                }
            });
        }
    });
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
