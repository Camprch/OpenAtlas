export function renderMarkers(events, coords, aliases, detailsByCountry, {
  markerStyle,
  clearMarkers,
  map,
  markersByCountry,
  isMobile,
  openSidePanel
}) {
  clearMarkers();
  const counts = new Map();
  events.forEach(e => {
    if (!e.country) return;
    const key = e.country;
    counts.set(key, (counts.get(key) || 0) + 1);
  });

  counts.forEach((count, key) => {
    let coordKey = key;
    if (!coords[coordKey] && aliases[key] && coords[aliases[key]]) {
      coordKey = aliases[key];
    }
    if (!coords[coordKey]) return;
    const [lat, lon] = coords[coordKey];
    const style = markerStyle(count);
    const hitRadius = style.radius + (isMobile() ? 10 : 6);
    const hitCircle = L.circleMarker([lat, lon], {
      radius: hitRadius,
      color: "transparent",
      fillColor: "transparent",
      fillOpacity: 0,
      weight: 0,
      interactive: true,
      pane: "markerPane",
    });
    const marker = L.circleMarker([lat, lon], style);
    let flag = '';
    if (/^\p{Emoji}/u.test(coordKey)) {
      flag = coordKey.split(' ')[0];
    } else {
      for (const alias in aliases) {
        if (aliases[alias] === coordKey && /^\p{Emoji}/u.test(alias)) {
          flag = alias.split(' ')[0];
          break;
        }
      }
    }
    if (!isMobile()) {
      const countryName = coordKey.replace(/^[^\p{L}\p{N}]+/u, '').trim();
      marker.bindPopup(`<div class="map-popup"><span class="map-popup-flag">${flag}</span><br><b>${countryName}</b></div>`);
      marker.on('mouseover', () => marker.openPopup && marker.openPopup());
      marker.on('mouseout', () => marker.closePopup && marker.closePopup());
    }
    marker.on('mouseover', () => marker.setStyle({ radius: style.radius * 1.15 }));
    marker.on('mouseout', () => marker.setStyle({ radius: style.radius }));
    marker.on('click', () => openSidePanel(coordKey, detailsByCountry.get(key) || []));
    hitCircle.on('click', () => openSidePanel(coordKey, detailsByCountry.get(key) || []));
    hitCircle.on('mouseover', () => marker.setStyle({ radius: style.radius * 1.15 }));
    hitCircle.on('mouseout', () => marker.setStyle({ radius: style.radius }));
    hitCircle.addTo(map);
    marker.addTo(map);
    if (flag) {
      const emojiMarker = L.marker([lat, lon], {
        icon: L.divIcon({
          className: 'country-emoji-marker',
          html: `<span>${flag}</span>`,
          iconSize: [0, 0],
          iconAnchor: [0, 0],
        }),
        interactive: false,
      });
      emojiMarker.setZIndexOffset(1000);
      emojiMarker.addTo(map);
      markersByCountry[coordKey] = { marker, emoji: emojiMarker, hit: hitCircle };
    } else {
      markersByCountry[coordKey] = { marker, hit: hitCircle };
    }
  });
}
