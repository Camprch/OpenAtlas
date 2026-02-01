// modules/sidepanel.js
import { loadEvents } from "./events.js";

export const NON_GEOREF_KEY = "__NO_COUNTRY__";
const NON_GEOREF_LABEL = "Ungeoref";

export let currentCountry = null;
window.currentCountry = null;
let frozenScrollY = 0;
let bodyWasFixed = false;

function freezeBodyScroll() {
    if (bodyWasFixed) return;
    frozenScrollY = window.scrollY || window.pageYOffset || 0;
    document.body.style.position = 'fixed';
    document.body.style.top = `-${frozenScrollY}px`;
    document.body.style.left = '0';
    document.body.style.right = '0';
    document.body.style.width = '100%';
    bodyWasFixed = true;
}

function restoreBodyScroll() {
    if (!bodyWasFixed) return;
    document.body.style.position = '';
    document.body.style.top = '';
    document.body.style.left = '';
    document.body.style.right = '';
    document.body.style.width = '';
    window.scrollTo(0, frozenScrollY);
    bodyWasFixed = false;
}

let sidepanelHandlersBound = false;

function bindSidepanelCloseOnEmpty(sidepanel, sidepanelContent, backdrop, closePanel) {
    if (sidepanelHandlersBound) return;
    backdrop.onclick = closePanel;
    sidepanel.onclick = (e) => {
        if (e.target === sidepanel) {
            closePanel();
        }
    };
    sidepanel.ontouchstart = (e) => {
        if (e.target === sidepanel) {
            e.preventDefault();
            closePanel();
        }
    };
    if (sidepanelContent) {
        sidepanelContent.onclick = (e) => {
            if (e.target === sidepanelContent) {
                closePanel();
            }
        };
        sidepanelContent.ontouchstart = (e) => {
            if (e.target === sidepanelContent) {
                e.preventDefault();
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
    freezeBodyScroll();
    // Always load events with the currently selected filters
    const selectedDates = window.selectedFilters?.date || [];
    const selectedSources = window.selectedFilters?.source || [];
    const selectedLabels = window.selectedFilters?.label || [];
    const selectedEventTypes = window.selectedFilters?.event_type || [];
    loadEvents(
        country,
        selectedDates.length > 0 ? selectedDates[0] : null,
        selectedSources.length > 0 ? selectedSources : null,
        selectedLabels.length > 0 ? selectedLabels : null,
        selectedEventTypes.length > 0 ? selectedEventTypes : null
    );
    function closePanel() {
        // Close panel and re-enable page scroll
        sidepanel.classList.remove('visible');
        backdrop.style.display = 'none';
        document.body.classList.remove('no-scroll');
        restoreBodyScroll();
    }
    closeBtn.onclick = closePanel;
    bindSidepanelCloseOnEmpty(sidepanel, sidepanelContent, backdrop, closePanel);
}
