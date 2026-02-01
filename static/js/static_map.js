export let map;
export let markersByCountry = {};

const IS_MOBILE = window.matchMedia('(max-width: 768px)').matches;

export function initMap() {
  map = L.map('map', { worldCopyJump: true, minZoom: 2, maxZoom: 8, tapTolerance: 30 }).setView([20, 0], 2);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { attribution: '&copy; CARTO', noWrap: true }).addTo(map);
}

export function clearMarkers() {
  Object.values(markersByCountry).forEach(m => {
    if (Array.isArray(m)) {
      m.forEach(layer => map.removeLayer(layer));
    } else if (m && m.marker) {
      map.removeLayer(m.marker);
      if (m.emoji) map.removeLayer(m.emoji);
    } else {
      map.removeLayer(m);
    }
  });
  markersByCountry = {};
}

export function markerStyle(count) {
  const n = Math.max(1, count || 1);
  const minRadius = IS_MOBILE ? 10 : 10;
  const maxRadius = IS_MOBILE ? 13 : 13;
  const maxCount = 25;
  const ratio = Math.min(n / maxCount, 1);
  const radius = minRadius + (maxRadius - minRadius) * ratio;
  let color = '#22c55e';
  if (n >= 5 && n < 15) color = '#eab308';
  if (n >= 15) color = '#f97316';
  return { radius, color, fillColor: color, fillOpacity: 0.85, weight: IS_MOBILE ? 2 : 1 };
}
