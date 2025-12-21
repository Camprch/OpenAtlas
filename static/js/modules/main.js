import { setupSearch } from "./search.js";
// modules/main.js
import { initMap } from "./map.js";
import { loadCountryData, loadActiveCountries } from "./countries.js";
import { loadTimeline, timelineDates, currentGlobalDate, currentPanelDate } from "./timeline.js";
import { pipelinePolling, pipelineRunning, startPipeline, stopPipeline } from "./pipeline.js";
import { renderEvents } from "./events.js";
import { openSidePanel, currentCountry } from "./sidepanel.js";
import { setupFilterMenuSync } from "./filter.js";

window.IS_MOBILE = window.matchMedia("(max-width: 768px)").matches;

const pipelineBarBtn = document.getElementById('pipeline-bar-btn');
const pipelineBarFill = document.getElementById('pipeline-bar-fill');
const pipelineBarLabel = document.getElementById('pipeline-bar-label');


function fillSelect(select, value, dates) {
    select.innerHTML = "";
    const allOpt = document.createElement("option");
    allOpt.value = "ALL";
    allOpt.textContent = "Toutes les dates";
    select.appendChild(allOpt);
    dates.forEach((dateStr) => {
        const opt = document.createElement("option");
        opt.value = dateStr;
        opt.textContent = dateStr;
        select.appendChild(opt);
    });
    select.value = value || "ALL";
}


async function init() {
    initMap();
    await loadCountryData();

    // Affiche tous les événements sur la carte au chargement
    await loadActiveCountries();

    setupFilterMenuSync();

    setupSearch();

    // Expose openSidePanel pour la recherche (search.js)
    window.openSidePanel = openSidePanel;

    // Reprise de l'état pipeline au chargement via pipeline.js
    if (pipelineBarBtn && pipelineBarFill && pipelineBarLabel) {
        import("./pipeline.js").then(async m => {
            const resumed = await m.resumePipelineIfRunning(
                pipelineBarBtn,
                pipelineBarFill,
                pipelineBarLabel,
                () => m.startPipeline(
                    pipelineBarBtn, pipelineBarFill, pipelineBarLabel,
                    () => m.stopPipeline(pipelineBarBtn, pipelineBarLabel),
                    () => m.startPipeline(pipelineBarBtn, pipelineBarFill, pipelineBarLabel, () => m.stopPipeline(pipelineBarBtn, pipelineBarLabel))
                ),
                () => m.stopPipeline(pipelineBarBtn, pipelineBarLabel)
            );
            // Log pour vérifier l'assignation du onclick
            console.log('[main.js] pipelineBarBtn.onclick:', pipelineBarBtn.onclick);
            // Si pipeline running, force l'assignation du callback d'annulation
            if (window.pipelineRunning) {
                pipelineBarBtn.onclick = () => m.stopPipeline(pipelineBarBtn, pipelineBarLabel);
                console.log('[main.js] Forçage du callback d\'annulation sur le bouton pipelineBarBtn');
            } else if (!resumed) {
                pipelineBarBtn.onclick = () => m.startPipeline(
                    pipelineBarBtn, pipelineBarFill, pipelineBarLabel,
                    () => m.stopPipeline(pipelineBarBtn, pipelineBarLabel),
                    () => m.startPipeline(pipelineBarBtn, pipelineBarFill, pipelineBarLabel, () => m.stopPipeline(pipelineBarBtn, pipelineBarLabel))
                );
            }
        });
    }
}

window.addEventListener("load", init);


