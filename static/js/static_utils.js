export function normalize(str) {
  // Fold accents/diacritics for a more forgiving search.
  return (str || '').normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
}

export function containsQuery(text, query) {
  if (!query) return false;
  return normalize(text).includes(normalize(query));
}

export function highlightQuery(text, query) {
  // Wrap matching ranges with a highlighted span without altering original casing.
  if (!query) return text || '';
  const raw = text || '';
  const normText = normalize(raw);
  const normQuery = normalize(query);
  if (!normQuery) return raw;
  let result = '';
  let i = 0;
  while (i < raw.length) {
    let found = -1;
    for (let j = i; j <= raw.length - normQuery.length; j++) {
      if (normText.substr(j, normQuery.length) === normQuery) {
        found = j;
        break;
      }
    }
    if (found === -1) {
      result += raw.slice(i);
      break;
    }
    result += raw.slice(i, found) + `<span class="search-hl">` + raw.slice(found, found + normQuery.length) + '</span>';
    i = found + normQuery.length;
  }
  return result;
}

export function toggleTextBlock(textEl) {
  if (!textEl) return;
  if (textEl.classList.contains('is-collapsed')) {
    textEl.classList.remove('is-collapsed');
    textEl.classList.add('is-open');
  } else {
    textEl.classList.add('is-collapsed');
    textEl.classList.remove('is-open');
  }
}
