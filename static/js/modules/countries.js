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

export async function loadActiveCountries(currentGlobalDate) {
    let url = "/api/countries/active";
    if (Array.isArray(currentGlobalDate) && currentGlobalDate.length > 0) {
        // Plusieurs dates sélectionnées : ?date=YYYY-MM-DD&date=YYYY-MM-DD
        const params = currentGlobalDate.map(d => `date=${encodeURIComponent(d)}`).join('&');
        url += `?${params}`;
    } else if (typeof currentGlobalDate === 'string' && currentGlobalDate !== "ALL") {
        url += `?date=${encodeURIComponent(currentGlobalDate)}`;
    }
    // Si currentGlobalDate est null/undefined/[] => pas de paramètre, on affiche tout
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
        if (window.IS_MOBILE === false) {
            marker.bindPopup(`<b>${key}</b><br>Événements : ${count}`);
        }
        interactiveCircle.on("mouseover", function (e) {
            marker.setStyle({ radius: style.radius * 1.15 });
            if (window.IS_MOBILE === false) {
                marker.openPopup && marker.openPopup();
            }
        });
        interactiveCircle.on("mouseout", function (e) {
            marker.setStyle({ radius: style.radius });
            if (window.IS_MOBILE === false) {
                marker.closePopup && marker.closePopup();
            }
        });
        interactiveCircle.on("click", () => openSidePanel(key));
        interactiveCircle.addTo(map);
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

