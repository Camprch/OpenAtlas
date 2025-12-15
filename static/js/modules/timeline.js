// modules/timeline.js
export let timelineDates = [];
export let currentGlobalDate = null;
export let currentPanelDate = null;

export async function loadTimeline(fillSelectCb) {
    const resp = await fetch("/api/dates");
    const data = await resp.json();
    timelineDates = data.dates || [];
    currentGlobalDate = "ALL";
    currentPanelDate = "ALL";
    fillSelectCb(timelineDates, currentGlobalDate, currentPanelDate);
}
