import { toggleTextBlock } from './static_utils.js';

export function buildCountryEvents(countryKey, details, selected) {
  const filtered = details.filter(item => {
    if (selected.date.size && (!item.timestamp || !selected.date.has(item.timestamp))) return false;
    if (selected.source.size && (!item.source || !selected.source.has(item.source))) return false;
    if (selected.label.size && (!item.label || !selected.label.has(item.label))) return false;
    return true;
  });
  const buckets = new Map();
  filtered.forEach(item => {
    const key = `${item.region || ''}||${item.location || ''}`;
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(item);
  });

  const zones = [];
  buckets.forEach((items, key) => {
    const [region, location] = key.split('||');
    items.sort((a, b) => (b.timestamp || '').localeCompare(a.timestamp || ''));
    const messages = items.map(m => {
      const text = m.text || '';
      const preview = text.length > 280 ? text.slice(0, 277) + '...' : text;
      const url = (m.channel && m.telegram_message_id) ? `https://t.me/${m.channel}/${m.telegram_message_id}` : null;
      return {
        id: m.id,
        telegram_message_id: m.telegram_message_id,
        channel: m.channel,
        title: m.title,
        source: m.source,
        orientation: m.orientation,
        event_timestamp: m.timestamp,
        created_at: m.created_at,
        url,
        translated_text: text,
        preview,
      };
    });
    zones.push({
      region: region || null,
      location: location || null,
      messages_count: messages.length,
      messages,
    });
  });

  zones.sort((a, b) => b.messages_count - a.messages_count);
  return {
    date: selected.date.size ? Array.from(selected.date)[0] : new Date().toISOString().slice(0, 10),
    country: countryKey,
    zones,
  };
}

export function renderEvents(data, eventsContainer) {
  if (!data || !data.zones || data.zones.length === 0) {
    eventsContainer.textContent = 'Aucun événement.';
    return;
  }
  const html = data.zones.map((zone, idx) => {
    const header = [zone.region, zone.location].filter(Boolean).join(' – ') || 'Zone inconnue';
    const msgs = zone.messages.map((m, mIdx) => {
      const title = m.title || '(Sans titre)';
      const fullText = m.translated_text || '';
      const orientation = m.orientation ? ` • ${m.orientation}` : '';
      const postLink = m.url ? `<a href="${m.url}" target="_blank">post n° ${m.telegram_message_id}</a>` : '';
      const timeStr = new Date(m.event_timestamp || m.created_at).toLocaleString();
      return `\n            <li class="event" data-msg-id="${m.id}">\n                <div class="evt-title" data-zone="${idx}" data-msg="${mIdx}">${title}</div>\n                <div class="evt-text is-collapsed">\n                    ${fullText}\n                    <div class="evt-meta">\n                        <span class="evt-source">${m.source}${orientation}</span>\n                        <span class="evt-time">${timeStr}</span>\n                        <span class="evt-link">${postLink}</span>\n                    </div>\n                </div>\n            </li>\n        `;
    }).join('');
    return `\n            <section class="zone-block">\n                <h4 class="zone-header" data-idx="${idx}">\n                    <span class="toggle-btn">▶</span> ${header}\n                    <span class="evt-count">(${zone.messages_count})</span>\n                </h4>\n                <ul class="event-list is-collapsed" id="zone-list-${idx}">\n                    ${msgs}\n                </ul>\n            </section>\n        `;
  }).join('');
  eventsContainer.innerHTML = html;
  data.zones.forEach((zone, idx) => {
    const headerEl = document.querySelector(`.zone-header[data-idx='${idx}']`);
    const listEl = document.getElementById(`zone-list-${idx}`);
    const btn = headerEl.querySelector('.toggle-btn');
    headerEl.addEventListener('click', () => {
      if (listEl.classList.contains('is-collapsed')) {
        listEl.classList.remove('is-collapsed');
        btn.textContent = '▼';
        listEl.querySelectorAll('.evt-title').forEach(titleEl => {
          if (!titleEl.dataset.listener) {
            titleEl.addEventListener('click', function(e) {
              e.stopPropagation();
              const text = this.nextElementSibling;
              toggleTextBlock(text);
            });
            titleEl.dataset.listener = '1';
          }
        });
      } else {
        listEl.classList.add('is-collapsed');
        btn.textContent = '▶';
      }
    });
  });
}
