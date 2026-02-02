import { setupSearch } from "./search.js";
// modules/main.js
import { initMap } from "./map.js";
import { loadCountryData, loadActiveCountries } from "./countries.js";
import { loadTimeline, timelineDates, currentGlobalDate, currentPanelDate } from "./timeline.js";
import { pipelinePolling, pipelineRunning, startPipeline, stopPipeline } from "./pipeline.js";
import { renderEvents } from "./events.js";
import { openSidePanel, currentCountry, NON_GEOREF_KEY } from "./sidepanel.js";
import { setupFilterMenuSync } from "./filter.js";

window.IS_MOBILE = window.matchMedia("(max-width: 768px)").matches;

const pipelineBarBtn = document.getElementById('pipeline-bar-btn');
const pipelineBarFill = document.getElementById('pipeline-bar-fill');
const pipelineBarLabel = document.getElementById('pipeline-bar-label');


function fillSelect(select, value, dates) {
    // Populate a select with available dates and an "ALL" option
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
    // Boot sequence for the dashboard
    initMap();
    await loadCountryData();

    // Load all events on the map at startup
    await loadActiveCountries();

    setupFilterMenuSync();

    setupSearch();

    // Expose openSidePanel for search results
    window.openSidePanel = openSidePanel;

    // Resume pipeline UI state on page load
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
            // Debug logging for button handlers
            console.log('[main.js] pipelineBarBtn.onclick:', pipelineBarBtn.onclick);
            // Ensure cancel callback is wired when pipeline is already running
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


window.addEventListener("load", () => {
    init();

    // Wire up the pipeline log panel toggle
    const logsToggle = document.getElementById('pipeline-logs-toggle');
    const logsPanel = document.getElementById('pipeline-logs-panel');
    const logsContent = document.getElementById('pipeline-logs-content');
    const logsClose = document.getElementById('pipeline-logs-close');
    let logsVisible = false;
    let logsStreamAbort = null;
    let logsStreamReader = null;
    if (logsToggle && logsPanel && logsContent) {
        logsToggle.addEventListener('click', async function() {
            if (!logsVisible) {
                logsPanel.style.display = 'block';
                logsVisible = true;
                logsContent.textContent = '';
                // Stream pipeline logs while panel is open
                logsStreamAbort = new AbortController();
                try {
                    const resp = await fetch('/api/pipeline-logs', { signal: logsStreamAbort.signal });
                    if (resp.body) {
                        const reader = resp.body.getReader();
                        logsStreamReader = reader;
                        const decoder = new TextDecoder('utf-8');
                        let buffer = '';
                        (async function readLogs() {
                            while (logsVisible) {
                                const { value, done } = await reader.read();
                                if (done) break;
                                buffer += decoder.decode(value, { stream: true });
                                let lines = buffer.split('\n');
                                buffer = lines.pop();
                                for (const line of lines) {
                                    logsContent.textContent += line + '\n';
                                }
                                logsContent.scrollTop = logsContent.scrollHeight;
                            }
                            if (buffer) {
                                logsContent.textContent += buffer + '\n';
                                logsContent.scrollTop = logsContent.scrollHeight;
                            }
                        })();
                    }
                } catch (e) {}
            } else {
                logsPanel.style.display = 'none';
                logsVisible = false;
                if (logsStreamAbort) logsStreamAbort.abort();
                logsStreamAbort = null;
                logsStreamReader = null;
            }
        });
    }
    if (logsClose && logsPanel) {
        logsClose.addEventListener('click', function() {
            logsPanel.style.display = 'none';
            logsVisible = false;
            if (logsStreamAbort) logsStreamAbort.abort();
            logsStreamAbort = null;
            logsStreamReader = null;
        });
    }

    const mapEl = document.getElementById('map');
    const sidepanel = document.getElementById('sidepanel');
    const filterMenu = document.getElementById('filter-menu');
    function isAllowedScrollTarget(target) {
        if (!mapEl || !target) return false;
        if (!(target instanceof Element)) return false;
        return (
            mapEl.contains(target) ||
            target.closest('#sidepanel-content') ||
            target.closest('#filter-menu') ||
            target.closest('#filter-menu-options')
        );
    }

    function isPanelOpen() {
        const sidepanel = document.getElementById('sidepanel');
        const filterMenu = document.getElementById('filter-menu');
        const filterOpen = filterMenu && window.getComputedStyle(filterMenu).display !== 'none';
        const sideOpen = sidepanel && sidepanel.classList.contains('visible');
        return Boolean(filterOpen || sideOpen);
    }

    function isZoomAllowed(target) {
        if (isPanelOpen()) return false;
        if (!(target instanceof Element)) return false;
        return mapEl && mapEl.contains(target);
    }

    function blockPinchOnElement(el) {
        if (!el) return;
        ['gesturestart', 'gesturechange', 'gestureend'].forEach(evt => {
            el.addEventListener(evt, (e) => e.preventDefault(), { passive: false });
        });
        el.addEventListener('touchstart', (e) => {
            if (e.touches && e.touches.length > 1) e.preventDefault();
        }, { passive: false });
        el.addEventListener('touchmove', (e) => {
            if (e.touches && e.touches.length > 1) e.preventDefault();
        }, { passive: false });
    }

    // Zoom/scroll blocking removed.

    blockPinchOnElement(sidepanel);
    blockPinchOnElement(filterMenu);


    // Wire up the "country == none" quick access button
    const nonGeorefToggle = document.getElementById('non-georef-toggle');
    if (nonGeorefToggle) {
        nonGeorefToggle.addEventListener('click', function() {
            const isMobile = window.matchMedia('(max-width: 768px)').matches;
            const sidepanel = document.getElementById('sidepanel');
            if (isMobile && sidepanel && sidepanel.classList.contains('visible')) {
                closeSidePanel();
                return;
            }
            openSidePanel(NON_GEOREF_KEY);
        });
    }
});
