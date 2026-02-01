import { NON_GEOREF_KEY } from "./sidepanel.js";

// Load and render events for a selected country
export async function loadEvents(country, currentPanelDate = null, sources = null, labels = null, event_types = null) {
    const eventsContainer = document.getElementById("events");

    // Fall back to the panel date selector when no date is provided
    if (!currentPanelDate) {
        const select = document.getElementById("timeline-panel");
        currentPanelDate = select ? select.value : null;
    }

    // Build endpoint and query parameters based on filters
    let url = "";
    const params = [];
    if (country === NON_GEOREF_KEY) {
        if (!currentPanelDate || currentPanelDate === "ALL") {
            url = `/api/non-georef/all-events`;
        } else {
            url = `/api/non-georef/events`;
            params.push(`date=${encodeURIComponent(currentPanelDate)}`);
        }
    } else {
        if (!currentPanelDate || currentPanelDate === "ALL") {
            url = `/api/countries/${encodeURIComponent(country)}/all-events`;
        } else {
            url = `/api/countries/${encodeURIComponent(country)}/events`;
            params.push(`date=${encodeURIComponent(currentPanelDate)}`);
        }
    }
    if (Array.isArray(sources) && sources.length > 0) {
        params.push(...sources.map(s => `sources=${encodeURIComponent(s)}`));
    }
    if (Array.isArray(labels) && labels.length > 0) {
        params.push(...labels.map(l => `labels=${encodeURIComponent(l)}`));
    }
    if (Array.isArray(event_types) && event_types.length > 0) {
        params.push(...event_types.map(e => `event_types=${encodeURIComponent(e)}`));
    }
    if (params.length > 0) {
        url += (url.includes("?") ? "&" : "?") + params.join('&');
    }

    eventsContainer.innerHTML = "Chargement...";
    const resp = await fetch(url);
    if (!resp.ok) {
        eventsContainer.textContent = "Erreur de chargement.";
        return;
    }
    const data = await resp.json();
    renderEvents(data);
}
// modules/events.js
export function renderEvents(data) {
    const eventsContainer = document.getElementById("events");
    if (!data || !data.zones || data.zones.length === 0) {
        eventsContainer.textContent = "Aucun événement.";
        return;
    }
    // Render zones and their messages as collapsible sections
    const html = data.zones
        .map((zone, idx) => {
            const header =
                [zone.region, zone.location].filter(Boolean).join(" – ") ||
                "Zone inconnue";
            const msgs = zone.messages
                .map((m, mIdx) => {
                    const title = m.title || "(Sans titre)";
                    // Always display translated text (even if empty)
                    const fullText = m.translated_text || "";
                    const orientation = m.orientation ? ` • ${m.orientation}` : "";
                    const postLink = m.url ? `<a href="${m.url}" target="_blank">post n° ${m.telegram_message_id}</a>` : "";
                    const timeStr = new Date(m.event_timestamp || m.created_at).toLocaleString();
                    return `
            <li class="event" data-msg-id="${m.id}">
                <div class="evt-title" data-zone="${idx}" data-msg="${mIdx}">${title}</div>
                <div class="evt-text is-collapsed">
                    ${fullText}
                    <div class="evt-meta">
                        <span class="evt-source">${m.source}${orientation}</span>
                        <span class="evt-time">${timeStr}</span>
                        <span class="evt-link">${postLink}</span>
                    </div>
                </div>
            </li>
        `;
                })
                .join("");
            return `
            <section class="zone-block">
                <h4 class="zone-header" data-idx="${idx}">
                    <span class="toggle-btn">▶</span> ${header}
                    <span class="evt-count">(${zone.messages_count})</span>
                </h4>
                <ul class="event-list is-collapsed" id="zone-list-${idx}">
                    ${msgs}
                </ul>
            </section>
        `;
        })
        .join("");
    eventsContainer.innerHTML = html;
    // Wire up click handlers to expand/collapse zones and messages
    data.zones.forEach((zone, idx) => {
        const headerEl = document.querySelector(
            `.zone-header[data-idx='${idx}']`
        );
        const listEl = document.getElementById(`zone-list-${idx}`);
        const btn = headerEl.querySelector(".toggle-btn");
        headerEl.addEventListener("click", () => {
            if (listEl.classList.contains("is-collapsed")) {
                listEl.classList.remove("is-collapsed");
                btn.textContent = "▼";
                // Attach message toggle listeners when the zone opens
                listEl.querySelectorAll('.evt-title').forEach(titleEl => {
                    if (!titleEl.dataset.listener) {
                        titleEl.addEventListener('click', function(e) {
                            e.stopPropagation();
                            const text = this.nextElementSibling;
                            if (!text) return;
                            if (text.classList.contains("is-collapsed")) {
                                text.classList.remove("is-collapsed");
                                text.classList.add("is-open");
                            } else {
                                text.classList.add("is-collapsed");
                                text.classList.remove("is-open");
                            }
                        });
                        titleEl.dataset.listener = "1";
                    }
                });
            } else {
                listEl.classList.add("is-collapsed");
                btn.textContent = "▶";
            }
        });
    });
}
