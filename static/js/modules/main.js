// modules/main.js
import { initMap } from "./map.js";
import { loadCountryData, loadActiveCountries } from "./countries.js";
import { loadTimeline, timelineDates, currentGlobalDate, currentPanelDate } from "./timeline.js";
import { pipelinePolling, pipelineRunning, startPipeline, stopPipeline } from "./pipeline.js";
import { renderEvents } from "./events.js";
import { openSidePanel, currentCountry } from "./sidepanel.js";

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
            // Si aucun pipeline en cours, on assigne le bouton normalement
            if (!resumed) {
                pipelineBarBtn.onclick = () => m.startPipeline(
                    pipelineBarBtn, pipelineBarFill, pipelineBarLabel,
                    () => m.stopPipeline(pipelineBarBtn, pipelineBarLabel),
                    () => m.startPipeline(pipelineBarBtn, pipelineBarFill, pipelineBarLabel, () => m.stopPipeline(pipelineBarBtn, pipelineBarLabel))
                );
            }
        });
    }
    await loadTimeline((dates, globalDate, panelDate) => {
        const selectGlobal = document.getElementById("timeline-global");
        const selectPanel = document.getElementById("timeline-panel");
        window.currentGlobalDate = globalDate;
        window.currentPanelDate = panelDate;
        if (selectGlobal) fillSelect(selectGlobal, globalDate, dates);
        if (selectPanel) fillSelect(selectPanel, panelDate, dates);

        // Synchronisation des deux sélecteurs
        if (selectGlobal && selectPanel) {
            selectGlobal.addEventListener("change", () => {
                window.currentGlobalDate = selectGlobal.value;
                window.currentPanelDate = window.currentGlobalDate;
                selectPanel.value = window.currentPanelDate;
                loadActiveCountries(window.currentGlobalDate);
                if (window.currentCountry) {
                    import("./events.js").then(m => m.loadEvents(window.currentCountry, window.currentPanelDate));
                }
            });
            selectPanel.addEventListener("change", () => {
                window.currentPanelDate = selectPanel.value;
                window.currentGlobalDate = window.currentPanelDate;
                selectGlobal.value = window.currentGlobalDate;
                loadActiveCountries(window.currentGlobalDate);
                if (window.currentCountry) {
                    import("./events.js").then(m => m.loadEvents(window.currentCountry, window.currentPanelDate));
                }
            });
        }
    });
    await loadActiveCountries(window.currentGlobalDate);
    if (pipelineBarBtn) pipelineBarBtn.onclick = () => startPipeline(
        pipelineBarBtn, pipelineBarFill, pipelineBarLabel,
        () => stopPipeline(pipelineBarBtn, pipelineBarLabel),
        () => startPipeline(pipelineBarBtn, pipelineBarFill, pipelineBarLabel, () => stopPipeline(pipelineBarBtn, pipelineBarLabel))
    );
}

window.addEventListener("load", init);
