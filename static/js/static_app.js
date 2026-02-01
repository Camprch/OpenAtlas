// static/js/static_app.js
// Lightweight static-mode app that reads prebuilt JSON without backend APIs.

const IS_MOBILE = window.matchMedia("(max-width: 768px)").matches;

let map;
let markersByCountry = {};
let countryCoords = {};
let countryAliases = {};
let staticData = { events: [], filters: {}, details: [] };

if (!window.selectedFilters) {
    window.selectedFilters = {
        date: [],
        source: [],
        label: [],
        event_type: []
    };
}

function initMap() {
    map = L.map("map", {
        worldCopyJump: true,
        minZoom: 2,
        maxZoom: 8,
        tapTolerance: 30
    }).setView([20, 0], 2);

    L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        {
            attribution: "&copy; CARTO",
            noWrap: true
        }
    ).addTo(map);
}

function markerStyle(count) {
    const n = Math.max(1, count || 1);
    const minRadius = IS_MOBILE ? 8 : 4;
    const maxRadius = IS_MOBILE ? 13 : 7;
    const maxCount = 30;
    const ratio = Math.min(n / maxCount, 1);
    const radius = minRadius + (maxRadius - minRadius) * ratio;
    let color;
    if (n < 5) {
        color = "#22c55e";
    } else if (n < 15) {
        color = "#eab308";
    } else {
        color = "#f97316";
    }
    return {
        radius,
        color,
        fillColor: color,
        fillOpacity: 0.85,
        weight: IS_MOBILE ? 2 : 1
    };
}

function clearMarkers() {
    Object.values(markersByCountry).forEach((m) => map.removeLayer(m));
    markersByCountry = {};
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function dateKey(value) {
    if (!value) return null;
    if (typeof value === "string") {
        return value.slice(0, 10);
    }
    if (value instanceof Date && !Number.isNaN(value.valueOf())) {
        return value.toISOString().slice(0, 10);
    }
    return null;
}

function matchesFilter(selected, value) {
    if (!selected || selected.length === 0) return true;
    if (!value) return false;
    return selected.includes(value);
}

function eventMatchesFilters(evt) {
    const selected = window.selectedFilters;
    if (!matchesFilter(selected.source, evt.source || null)) return false;
    if (!matchesFilter(selected.label, evt.label || null)) return false;
    if (!matchesFilter(selected.event_type, evt.event_type || null)) return false;
    if (selected.date && selected.date.length > 0) {
        if (!evt.date) return false;
        if (!selected.date.includes(evt.date)) return false;
    }
    return true;
}

function detailMatchesFilters(detail) {
    const selected = window.selectedFilters;
    if (!matchesFilter(selected.source, detail.source || null)) return false;
    if (!matchesFilter(selected.label, detail.label || null)) return false;
    if (!matchesFilter(selected.event_type, detail.event_type || null)) return false;
    if (selected.date && selected.date.length > 0) {
        const dKey = dateKey(detail.timestamp || detail.created_at);
        if (!dKey) return false;
        if (!selected.date.includes(dKey)) return false;
    }
    return true;
}

function resolveCountryKey(name) {
    if (!name) return null;
    if (countryCoords[name]) return name;
    const lower = name.toLowerCase();
    if (countryAliases[lower] && countryCoords[countryAliases[lower]]) {
        return countryAliases[lower];
    }
    return null;
}

function renderMap() {
    const alert = document.getElementById("dashboard-alert");
    const missing = [];
    clearMarkers();

    const counts = new Map();
    staticData.events.forEach((evt) => {
        if (!eventMatchesFilters(evt)) return;
        if (!evt.country) return;
        const current = counts.get(evt.country) || 0;
        counts.set(evt.country, current + 1);
    });

    counts.forEach((count, country) => {
        const key = resolveCountryKey(country);
        if (!key) {
            missing.push(country);
            return;
        }
        const coords = countryCoords[key];
        if (!coords) return;
        const [lat, lon] = coords;
        const style = markerStyle(count);
        const clickableRadius = style.radius * 2.5;
        const interactiveCircle = L.circleMarker([lat, lon], {
            radius: clickableRadius,
            color: "transparent",
            fillColor: "transparent",
            fillOpacity: 0,
            weight: 0,
            interactive: true,
            pane: "markerPane"
        });
        const marker = L.circleMarker([lat, lon], style);
        let flag = "";
        if (/^\p{Emoji}/u.test(key)) {
            flag = key.split(" ")[0];
        } else {
            for (const alias in countryAliases) {
                if (countryAliases[alias] === key && /^\p{Emoji}/u.test(alias)) {
                    flag = alias.split(" ")[0];
                    break;
                }
            }
        }
        if (IS_MOBILE === false) {
            const countryName = key.replace(/^[^\p{L}\p{N}]+/u, "").trim();
            marker.bindPopup(
                `<div style="text-align:center;min-width:70px;"><span style="font-size:2.2em;line-height:1;">${flag}</span><br><b>${escapeHtml(countryName)}</b></div>`
            );
        }
        marker.on("mouseover", function () {
            marker.setStyle({ radius: style.radius * 1.15 });
            if (IS_MOBILE === false) marker.openPopup && marker.openPopup();
        });
        marker.on("mouseout", function () {
            marker.setStyle({ radius: style.radius });
            if (IS_MOBILE === false) marker.closePopup && marker.closePopup();
        });
        marker.on("click", () => openSidePanel(key));
        interactiveCircle.on("click", () => openSidePanel(key));
        interactiveCircle.addTo(map);
        marker.addTo(map);
        markersByCountry[key] = marker;
    });

    if (alert) {
        if (missing.length > 0) {
            alert.textContent = `⚠️ Pays non géolocalisés : ${missing.join(", ")}`;
            alert.style.display = "block";
        } else {
            alert.style.display = "none";
        }
    }
}

function renderEvents(details) {
    const eventsContainer = document.getElementById("events");
    if (!eventsContainer) return;
    if (!details || details.length === 0) {
        eventsContainer.textContent = "Aucun événement.";
        return;
    }

    const zones = new Map();
    details.forEach((detail) => {
        const region = detail.region || "";
        const location = detail.location || "";
        const key = `${region}||${location}`;
        if (!zones.has(key)) {
            zones.set(key, { region, location, messages: [] });
        }
        zones.get(key).messages.push(detail);
    });

    const html = Array.from(zones.values())
        .map((zone, idx) => {
            const header =
                [zone.region, zone.location].filter(Boolean).join(" – ") ||
                "Zone inconnue";
            const msgs = zone.messages
                .sort((a, b) => {
                    const da = new Date(a.timestamp || a.created_at || 0).valueOf();
                    const db = new Date(b.timestamp || b.created_at || 0).valueOf();
                    return db - da;
                })
                .map((m, mIdx) => {
                    const title = m.title || "(Sans titre)";
                    const fullText = m.text || "";
                    const orientation = m.orientation ? ` • ${m.orientation}` : "";
                    const dateValue = m.timestamp || m.created_at;
                    const timeStr = dateValue
                        ? new Date(dateValue).toLocaleString()
                        : "";
                    return `
            <li class="event" data-msg-id="${escapeHtml(m.id)}">
                <div class="evt-title" data-zone="${idx}" data-msg="${mIdx}" style="cursor:pointer;">${escapeHtml(title)}</div>
                <div class="evt-text" style="display:none;">
                    ${escapeHtml(fullText)}
                    <div class="evt-meta">
                        <span class="evt-source">${escapeHtml(m.source || "")}${escapeHtml(orientation)}</span>
                        <span class="evt-time">${escapeHtml(timeStr)}</span>
                    </div>
                </div>
            </li>
        `;
                })
                .join("");
            return `
            <section class="zone-block">
                <h4 class="zone-header" data-idx="${idx}">
                    <span class="toggle-btn">▶</span> ${escapeHtml(header)}
                    <span class="evt-count">(${zone.messages.length})</span>
                </h4>
                <ul class="event-list" id="zone-list-${idx}" style="display:none;">
                    ${msgs}
                </ul>
            </section>
        `;
        })
        .join("");

    eventsContainer.innerHTML = html;
    Array.from(zones.values()).forEach((zone, idx) => {
        const headerEl = document.querySelector(
            `.zone-header[data-idx='${idx}']`
        );
        const listEl = document.getElementById(`zone-list-${idx}`);
        if (!headerEl || !listEl) return;
        const btn = headerEl.querySelector(".toggle-btn");
        headerEl.addEventListener("click", () => {
            if (listEl.style.display === "none") {
                listEl.style.display = "";
                if (btn) btn.textContent = "▼";
                listEl.querySelectorAll(".evt-title").forEach((titleEl) => {
                    if (!titleEl.dataset.listener) {
                        titleEl.addEventListener("click", function (e) {
                            e.stopPropagation();
                            const text = this.nextElementSibling;
                            if (text.style.display === "none" || !text.style.display) {
                                text.style.display = "block";
                            } else {
                                text.style.display = "none";
                            }
                        });
                        titleEl.dataset.listener = "1";
                    }
                });
            } else {
                listEl.style.display = "none";
                if (btn) btn.textContent = "▶";
            }
        });
    });
}

function openSidePanel(country) {
    const sidepanel = document.getElementById("sidepanel");
    const backdrop = document.getElementById("sidepanel-backdrop");
    const closeBtn = document.getElementById("close-panel");
    const countryName = document.getElementById("panel-country-text");
    if (!sidepanel || !backdrop || !closeBtn || !countryName) return;
    window.currentCountry = country;
    countryName.textContent = country;
    sidepanel.classList.add("visible");
    backdrop.style.display = "block";
    document.body.classList.add("no-scroll");
    renderSidePanel(country);
    function closePanel() {
        sidepanel.classList.remove("visible");
        backdrop.style.display = "none";
        document.body.classList.remove("no-scroll");
    }
    closeBtn.onclick = closePanel;
    backdrop.onclick = closePanel;
}

function renderSidePanel(country) {
    const details = staticData.details.filter((detail) => {
        if (detail.country !== country) return false;
        return detailMatchesFilters(detail);
    });
    renderEvents(details);
}

function renderAllFilterOptions() {
    const optionsDiv = document.getElementById("filter-menu-options");
    if (!optionsDiv) return;
    optionsDiv.innerHTML = "";

    const columns = document.createElement("div");
    columns.id = "filter-columns";
    const categories = [
        { key: "date", label: "Date 🗓️" },
        { key: "source", label: "Source 📡" },
        { key: "label", label: "Label 🏷️" },
        { key: "event_type", label: "Type 📝" }
    ];
    categories.forEach((cat) => {
        const col = document.createElement("div");
        col.className = "filter-col";
        const title = document.createElement("div");
        title.className = "filter-col-title";
        title.textContent = cat.label;
        col.appendChild(title);
        const list = document.createElement("div");
        list.className = "filter-options-list";
        const values = staticData.filters[cat.key] || [];
        if (values.length === 0) {
            list.textContent = "Aucune option.";
        } else {
            values.forEach((val) => {
                const label = document.createElement("label");
                const checkbox = document.createElement("input");
                checkbox.type = "checkbox";
                checkbox.value = val;
                checkbox.checked = window.selectedFilters[cat.key].includes(val);
                label.appendChild(checkbox);
                label.appendChild(document.createTextNode(val));
                list.appendChild(label);
                checkbox.addEventListener("change", () => {
                    const selected = window.selectedFilters[cat.key] || [];
                    if (checkbox.checked) {
                        if (!selected.includes(val)) selected.push(val);
                    } else {
                        window.selectedFilters[cat.key] = selected.filter((v) => v !== val);
                    }
                    renderMap();
                    if (window.currentCountry) {
                        renderSidePanel(window.currentCountry);
                    }
                });
            });
        }
        col.appendChild(list);
        columns.appendChild(col);
    });
    optionsDiv.appendChild(columns);
}

function setupFilterMenuSync() {
    const filterBtnGlobal = document.getElementById("filter-btn-global");
    const filterBtnPanel = document.getElementById("filter-btn-panel");
    const filterMenu = document.getElementById("filter-menu");
    const filterMenuClose = document.getElementById("filter-menu-close");
    let lastOpener = null;

    function openMenu(opener) {
        if (!filterMenu) return;
        filterMenu.style.display = "flex";
        lastOpener = opener;
        if (opener === "panel") {
            filterMenu.style.position = "fixed";
            filterMenu.style.top = "80px";
            filterMenu.style.right = "420px";
            filterMenu.style.left = "";
            filterMenu.style.transform = "none";
            document.body.appendChild(filterMenu);
        } else {
            filterMenu.style.position = "fixed";
            filterMenu.style.top = "60px";
            filterMenu.style.left = "80px";
            filterMenu.style.right = "";
            filterMenu.style.transform = "none";
            document.body.appendChild(filterMenu);
        }
        renderAllFilterOptions();
    }

    function closeMenu() {
        if (!filterMenu) return;
        filterMenu.style.display = "none";
        lastOpener = null;
    }

    if (filterBtnGlobal) {
        filterBtnGlobal.addEventListener("click", () => {
            if (filterMenu.style.display === "flex" && lastOpener === "global") {
                closeMenu();
            } else {
                openMenu("global");
            }
        });
    }
    if (filterBtnPanel) {
        filterBtnPanel.addEventListener("click", () => {
            if (filterMenu.style.display === "flex" && lastOpener === "panel") {
                closeMenu();
            } else {
                openMenu("panel");
            }
        });
    }
    if (filterMenuClose) {
        filterMenuClose.addEventListener("click", closeMenu);
    }
    document.addEventListener("mousedown", (e) => {
        if (
            filterMenu &&
            filterMenu.style.display === "flex" &&
            !filterMenu.contains(e.target) &&
            e.target !== filterBtnGlobal &&
            e.target !== filterBtnPanel
        ) {
            closeMenu();
        }
    });
}

function setupStaticSearch() {
    const searchBtn = document.getElementById("static-search-btn");
    if (!searchBtn) return;
    searchBtn.addEventListener("click", () => {
        const query = window.prompt("Rechercher un pays");
        if (!query) return;
        const lower = query.trim().toLowerCase();
        if (!lower) return;
        const match = staticData.events.find((evt) =>
            (evt.country || "").toLowerCase().includes(lower)
        );
        if (match) {
            openSidePanel(match.country);
        }
    });
}

async function loadStaticData() {
    const [eventsResp, countriesResp] = await Promise.all([
        fetch("/static/data/events.json"),
        fetch("/static/data/countries.json")
    ]);
    staticData = await eventsResp.json();
    const countries = await countriesResp.json();
    countryCoords = countries.coordinates || {};
    countryAliases = countries.aliases || {};
}

async function init() {
    initMap();
    await loadStaticData();
    renderMap();
    setupFilterMenuSync();
    setupStaticSearch();
}

window.addEventListener("load", () => {
    init();
});
