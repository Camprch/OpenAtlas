// modules/sidepanel.js
import { loadEvents } from "./events.js";

export const NON_GEOREF_KEY = "__NO_COUNTRY__";
const NON_GEOREF_LABEL = "Ungeoref";

export let currentCountry = null;
window.currentCountry = null;

let sidepanelHandlersBound = false;

function isBlankSidepanelTarget(target) {
    if (!(target instanceof Element)) return false;
    if (target.id === 'sidepanel' || target.id === 'sidepanel-content' || target.id === 'events') {
        return true;
    }
    return false;
}

function bindSidepanelCloseOnEmpty(sidepanel, sidepanelContent, backdrop, closePanel) {
    if (sidepanelHandlersBound) return;
    backdrop.onclick = closePanel;
    sidepanel.onclick = (e) => {
        if (isBlankSidepanelTarget(e.target)) {
            closePanel();
        }
    };
    if (sidepanelContent) {
        sidepanelContent.onclick = (e) => {
            if (isBlankSidepanelTarget(e.target)) {
                closePanel();
            }
        };
    }
    sidepanelHandlersBound = true;
}

export function openSidePanel(country) {
    // Open the side panel and load events for the selected country
    const sidepanel = document.getElementById('sidepanel');
    const backdrop = document.getElementById('sidepanel-backdrop');
    const closeBtn = document.getElementById('close-panel');
    const countryName = document.getElementById('panel-country-text');
    const sidepanelContent = document.getElementById('sidepanel-content');
    if (!sidepanel || !backdrop || !closeBtn || !countryName) return;
    currentCountry = country;
    window.currentCountry = country;
    countryName.textContent = country === NON_GEOREF_KEY ? NON_GEOREF_LABEL : country;
    sidepanel.classList.add('visible');
    backdrop.style.display = 'block';
    document.body.classList.add('no-scroll');
    // Always load events with the currently selected filters
    const selectedDates = window.selectedFilters?.date || [];
    const selectedSources = window.selectedFilters?.source || [];
    const selectedLabels = window.selectedFilters?.label || [];
    loadEvents(
        country,
        selectedDates.length > 0 ? selectedDates[0] : null,
        selectedSources.length > 0 ? selectedSources : null,
        selectedLabels.length > 0 ? selectedLabels : null,
        null
    );
    function closePanel() {
        // Close panel and re-enable page scroll
        sidepanel.classList.remove('visible');
        backdrop.style.display = 'none';
        document.body.classList.remove('no-scroll');
    }
    closeBtn.onclick = closePanel;
    bindSidepanelCloseOnEmpty(sidepanel, sidepanelContent, backdrop, closePanel);
}
