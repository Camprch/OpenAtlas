// modules/map.js
export let map;
export let markersByCountry = {};

const IS_MOBILE = window.matchMedia("(max-width: 768px)").matches;

export function initMap() {
    // Initialize the Leaflet map with sensible defaults for the dashboard
    map = L.map("map", {
        worldCopyJump: true,
        minZoom: 2,
        maxZoom: 8,
        tapTolerance: 30,
    }).setView([20, 0], 2);

    L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        {
            attribution: "&copy; CARTO",
            noWrap: true,
        }
    ).addTo(map);
}

export function clearMarkers() {
    // Remove all markers currently rendered on the map
    Object.values(markersByCountry).forEach((m) => {
        if (Array.isArray(m)) {
            m.forEach((layer) => map.removeLayer(layer));
        } else if (m && m.marker) {
            map.removeLayer(m.marker);
            if (m.emoji) map.removeLayer(m.emoji);
            if (m.hit) map.removeLayer(m.hit);
        } else {
            map.removeLayer(m);
        }
    });
    markersByCountry = {};
}

export function markerStyle(count) {
    // Derive a marker radius and color based on event count
    const n = Math.max(1, count || 1);
    const minRadius = IS_MOBILE ? 10 : 10;
    const maxRadius = IS_MOBILE ? 13 : 13;
    const maxCount = 25;
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
        weight: IS_MOBILE ? 2 : 1,
    };
}
