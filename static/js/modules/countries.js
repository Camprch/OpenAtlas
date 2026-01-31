// modules/countries.js
import { map, markersByCountry, clearMarkers, markerStyle } from "./map.js";
import { openSidePanel } from "./sidepanel.js";

export let countryCoords = {};
export let countryAliases = {};

export async function loadCountryData() {
    // Load coordinates and aliases used to place markers on the map
    const resp = await fetch("/static/data/countries.json");
    const data = await resp.json();
    countryCoords = data.coordinates || {};
    countryAliases = data.aliases || {};
}

export async function loadActiveCountries(currentGlobalDate, sources = null, labels = null, event_types = null) {
    // Fetch active countries with optional filters and render markers
    let url = "/api/countries/active";
    const params = [];
    if (Array.isArray(currentGlobalDate) && currentGlobalDate.length > 0) {
        params.push(...currentGlobalDate.map(d => `date=${encodeURIComponent(d)}`));
    } else if (typeof currentGlobalDate === 'string' && currentGlobalDate !== "ALL") {
        params.push(`date=${encodeURIComponent(currentGlobalDate)}`);
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
        url += `?${params.join('&')}`;
    }
    const resp = await fetch(url);
    if (!resp.ok) {
        console.error("Erreur /api/countries/active", resp.status);
        return;
    }
    const apiData = await resp.json();
    const countries = apiData.countries || [];
    const ignored = apiData.ignored_countries || [];
    // Reset existing markers before rendering the new set
    clearMarkers();
    const missing = [];
    const alert = document.getElementById("dashboard-alert");
    countries.forEach((c) => {
        let normName = c.country;
        const count = c.events_count;
        let key = normName;
        // Resolve aliases to coordinates; track missing geocodes for alerting
        if (!(key in countryCoords)) {
            if (countryAliases[normName] && countryCoords[countryAliases[normName]]) {
                key = countryAliases[normName];
            } else {
                missing.push(normName);
                return;
            }
        }
        const [lat, lon] = countryCoords[key];
        if (markersByCountry[key]) {
            return;
        }
        const style = markerStyle(count);
        // Invisible circle for a larger click target on dense markers
        const clickableRadius = style.radius * 2.5;
        const interactiveCircle = L.circleMarker([lat, lon], {
            radius: clickableRadius,
            color: 'transparent',
            fillColor: 'transparent',
            fillOpacity: 0,
            weight: 0,
            interactive: true,
            pane: 'markerPane',
        });
        const marker = L.circleMarker([lat, lon], style);
        // Extract flag emoji from the country key or its aliases
        let flag = '';
        if (key.match(/^\p{Emoji}/u)) {
            flag = key.split(' ')[0];
        } else {
            // Fallback: search aliases for an emoji-prefixed key
            for (const alias in countryAliases) {
                if (countryAliases[alias] === key && alias.match(/^\p{Emoji}/u)) {
                    flag = alias.split(' ')[0];
                    break;
                }
            }
        }
        // Show a popup with the flag and clean country name (desktop only)
        if (window.IS_MOBILE === false) {
            // Strip leading emojis/symbols for display
            const countryName = key.replace(/^[^\p{L}\p{N}]+/u, '').trim();
            marker.bindPopup(`<div style='text-align:center;min-width:70px;'><span style='font-size:2.2em;line-height:1;'>${flag}</span><br><b>${countryName}</b></div>`);
        }
        // Hover and click interactions
        marker.on("mouseover", function (e) {
            marker.setStyle({ radius: style.radius * 1.15 });
            if (window.IS_MOBILE === false) {
                marker.openPopup && marker.openPopup();
            }
        });
        marker.on("mouseout", function (e) {
            marker.setStyle({ radius: style.radius });
            if (window.IS_MOBILE === false) {
                marker.closePopup && marker.closePopup();
            }
        });
        marker.on("click", () => openSidePanel(key));
        marker.addTo(map);
        markersByCountry[key] = marker;
    });
    if (alert) {
        // Surface missing or unrecognized countries to the user
        let alertMsg = "";
        if (missing.length > 0) {
            alertMsg += `⚠️ Pays non géolocalisés : ${missing.join(", ")}`;
        }
        if (ignored.length > 0) {
            if (alertMsg) alertMsg += " | ";
            alertMsg += `⚠️ Pays non reconnus côté backend : ${ignored.join(", ")}`;
        }
        if (alertMsg) {
            alert.textContent = alertMsg;
            alert.style.display = "block";
        } else {
            alert.style.display = "none";
        }
    }
}
