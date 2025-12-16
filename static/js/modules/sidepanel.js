// modules/sidepanel.js
import { loadEvents } from "./events.js";

export let currentCountry = null;
window.currentCountry = null;

export function openSidePanel(country) {
    const sidepanel = document.getElementById('sidepanel');
    const backdrop = document.getElementById('sidepanel-backdrop');
    const closeBtn = document.getElementById('close-panel');
    const countryName = document.getElementById('panel-country-text');
    if (!sidepanel || !backdrop || !closeBtn || !countryName) return;
    currentCountry = country;
    window.currentCountry = country;
    countryName.textContent = country;
    sidepanel.classList.add('visible');
    backdrop.style.display = 'block';
    document.body.classList.add('no-scroll');
    // Toujours charger tous les événements par défaut (aucun filtre date)
    loadEvents(country, null);
    function closePanel() {
        sidepanel.classList.remove('visible');
        backdrop.style.display = 'none';
        document.body.classList.remove('no-scroll');
    }
    closeBtn.onclick = closePanel;
    backdrop.onclick = closePanel;
}
