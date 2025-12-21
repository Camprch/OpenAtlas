// modules/countries.js
import { map, markersByCountry, clearMarkers, markerStyle } from "./map.js";
import { openSidePanel } from "./sidepanel.js";

export let countryCoords = {};
export let countryAliases = {};

export async function loadCountryData() {
    const resp = await fetch("/static/data/countries.json");
    const data = await resp.json();
    countryCoords = data.coordinates || {};
    countryAliases = data.aliases || {};
}

export async function loadActiveCountries(currentGlobalDate, sources = null, labels = null, event_types = null) {
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
    clearMarkers();
    const missing = [];
    const alert = document.getElementById("dashboard-alert");
    countries.forEach((c) => {
        let normName = c.country;
        const count = c.events_count;
        let key = normName;
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
        // Récupère l'emoji drapeau à partir du nom du pays (clé)
        let flag = '';
        if (key.match(/^\p{Emoji}/u)) {
            flag = key.split(' ')[0];
        } else {
            // fallback: essaie de trouver dans les aliases
            for (const alias in countryAliases) {
                if (countryAliases[alias] === key && alias.match(/^\p{Emoji}/u)) {
                    flag = alias.split(' ')[0];
                    break;
                }
            }
        }
        // Affiche un popup avec le drapeau (gros) et le nom du pays sans drapeau
        if (window.IS_MOBILE === false) {
            // Nettoie le nom du pays pour enlever l'emoji drapeau au début
            // Supprime tous les emojis et caractères non-lettres/digits/espaces au début
            const countryName = key.replace(/^[^\p{L}\p{N}]+/u, '').trim();
            marker.bindPopup(`<div style='text-align:center;min-width:70px;'><span style='font-size:2.2em;line-height:1;'>${flag}</span><br><b>${countryName}</b></div>`);
        }
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

