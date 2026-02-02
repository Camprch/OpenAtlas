import { containsQuery, highlightQuery, toggleTextBlock } from './static_utils.js';

export function renderSearchResults(query, details, eventsContainer, applyFiltersToDetails) {
  const q = (query || '').trim();
  if (!q) {
    eventsContainer.textContent = 'Enter a search query.';
    return;
  }
  const filtered = applyFiltersToDetails(details).filter(item => {
    const haystack = [
      item.title,
      item.text,
      item.country,
      item.region,
      item.location,
      item.source,
      item.label,
    ].filter(Boolean).join(' ');
    return containsQuery(haystack, q);
  });
  if (!filtered.length) {
    eventsContainer.textContent = 'No results found.';
    return;
  }
  const itemsHtml = filtered.map(item => {
    const title = highlightQuery(item.title || '(No title)', q);
    const fullText = highlightQuery(item.text || '', q);
    const where = [item.country, item.region, item.location].filter(Boolean).join(' – ');
    const orientation = item.orientation ? ` • ${item.orientation}` : '';
    const rawTime = item.timestamp || item.created_at;
    const timeStr = rawTime ? new Date(rawTime).toLocaleString() : '';
    const source = item.source || '';
    const postLink = (item.channel && item.telegram_message_id)
      ? `<a href="https://t.me/${item.channel}/${item.telegram_message_id}" target="_blank">post n° ${item.telegram_message_id}</a>`
      : '';
    const metaParts = [];
    if (source) metaParts.push(`<span class="evt-source">${source}${orientation}</span>`);
    if (timeStr) metaParts.push(`<span class="evt-time">${timeStr}</span>`);
    if (where) metaParts.push(`<span class="evt-location">${highlightQuery(where, q)}</span>`);
    if (postLink) metaParts.push(`<span class="evt-link">${postLink}</span>`);
    const meta = metaParts.length ? `<div class="evt-meta">${metaParts.join('')}</div>` : '';
    return `
            <li class="event" data-msg-id="${item.id}">
                <div class="evt-title">${title}</div>
                <div class="evt-text is-open">
                    ${fullText}
                    ${meta}
                </div>
            </li>
        `;
  }).join('');
  eventsContainer.innerHTML = `<div class="search-results-count">${filtered.length} résultat(s)</div><ul class="event-list search-results">${itemsHtml}</ul>`;
  eventsContainer.querySelectorAll('.evt-title').forEach(titleEl => {
    if (!titleEl.dataset.listener) {
      titleEl.addEventListener('click', function(e) {
        e.stopPropagation();
        const text = this.nextElementSibling;
        toggleTextBlock(text);
      });
      titleEl.dataset.listener = '1';
    }
  });
}
