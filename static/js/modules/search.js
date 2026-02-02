// modules/search.js
import { NON_GEOREF_KEY } from "./sidepanel.js";


// Load country aliases/coordinates for search result navigation
let COUNTRY_ALIASES = {};
let COUNTRY_COORDS = {};
fetch('/static/data/countries.json')
    .then(r => r.json())
    .then(data => {
        COUNTRY_ALIASES = data.aliases || {};
        COUNTRY_COORDS = data.coordinates || {};
    });

export function setupSearch() {
    // Attach search handlers to the header input
    const input = document.getElementById('search-input');
    if (!input) return;

    function normalize(str) {
        // Remove diacritics and lowercase for comparisons
        return str.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
    }
    // Highlight query matches (case/diacritic-insensitive)
    function highlightQuery(text, query) {
        if (!query) return text;
        // Normalize for accent-insensitive comparisons
        const norm = s => s.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
        const normText = norm(text);
        const normQuery = norm(query);
        if (!normQuery) return text;
        let result = '';
        let i = 0;
        while (i < text.length) {
            // Find next normalized match position
            let found = -1;
            for (let j = i; j <= text.length - query.length; j++) {
                if (normText.substr(j, normQuery.length) === normQuery) {
                    found = j;
                    break;
                }
            }
            if (found === -1) {
                result += text.slice(i);
                break;
            }
            result += text.slice(i, found) + `<span class="search-hl">` + text.slice(found, found + query.length) + '</span>';
            i = found + query.length;
        }
        return result;
    }

    async function doSearch() {
        const q = input.value.trim();
        if (!q) return;
        input.disabled = true;
        try {
            const resp = await fetch(`/api/search/events?q=${encodeURIComponent(q)}`);
            if (!resp.ok) throw new Error('Erreur API');
            const results = await resp.json();
            if (results.length === 0) {
                alert('Aucun résultat.');
            } else {
                // Render results in a modal with highlighted matches
                const html = results.map((m, i) =>
                    `<div class='search-result-item' data-country="${encodeURIComponent(m.country || '')}" data-country-norm="${encodeURIComponent(m.country_norm || '')}" data-region="${encodeURIComponent(m.region || '')}" data-location="${encodeURIComponent(m.location || '')}" data-msgid="${m.id}" tabindex="0">
                        <b>${highlightQuery((m.country || '') + ' ' + (m.region || '') + ' ' + (m.location || ''), q)}</b><br>
                        <span class='search-result-label'>${highlightQuery(m.label || '', q)}</span><br>
                        ${highlightQuery(m.translated_text || '', q)}
                    </div>`
                ).join('');
                showSearchModal(html);
            }
        } catch (e) {
            alert('Erreur recherche: ' + e.message);
        } finally {
            input.disabled = false;
        }
    }
    input.addEventListener('keydown', e => {
        if (e.key === 'Enter') doSearch();
    });

    // Modal container for search results
    function showSearchModal(html) {
        let modal = document.getElementById('search-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'search-modal';
            modal.className = 'search-modal';
            modal.innerHTML = `<button id='close-search-modal' class='search-modal-close'>×</button><div id='search-modal-content' class='search-modal-content'></div>`;
            document.body.appendChild(modal);
            modal.querySelector('#close-search-modal').onclick = () => modal.remove();
        }
        modal.querySelector('#search-modal-content').innerHTML = html;
        // Attach click/keyboard handlers to each result item
        modal.querySelectorAll('.search-result-item').forEach(item => {
            // Prefer country_norm; fall back to raw country with alias/coord matching
            const countryNorm = decodeURIComponent(item.dataset.country_norm || '');
            const countryRaw = decodeURIComponent(item.dataset.country || '');
            let country = countryNorm;
            if (!country) {
                // Try alias lookup with lowercase keys
                const key = countryRaw.trim().toLowerCase();
                if (COUNTRY_ALIASES[key]) {
                    country = COUNTRY_ALIASES[key];
                } else {
                    // Fallback: try matching coordinates keys by suffix
                    for (const k in COUNTRY_COORDS) {
                        if (k.toLowerCase().endsWith(countryRaw.toLowerCase())) {
                            country = k;
                            break;
                        }
                    }
                }
            }
            if (!country) {
                country = NON_GEOREF_KEY;
            }
            console.log('[Recherche] country_norm:', countryNorm, '| country:', countryRaw, '| utilisé pour openSidePanel:', country);
            item.onclick = () => {
                const msgId = item.dataset.msgid;
                if (window.openSidePanel && country) {
                    console.log('[Recherche] Ouverture du panneau latéral pour le pays :', country);
                    window.openSidePanel(country);
                    // Wait for events to render before scrolling/highlighting
                    function openAllZones() {
                        document.querySelectorAll('.zone-header').forEach(header => {
                            const btn = header.querySelector('.toggle-btn');
                            const listId = header.getAttribute('data-idx');
                            const listEl = document.getElementById(`zone-list-${listId}`);
                            if (listEl && listEl.style.display === 'none') {
                                header.click();
                            }
                        });
                    }
                    let tries = 0;
                    function tryHighlight() {
                        openAllZones();
                        const evt = document.querySelector(`[data-msg-id='${msgId}']`);
                        if (evt) {
                            evt.scrollIntoView({behavior:'smooth', block:'center'});
                            evt.classList.add('search-match');
                            setTimeout(()=>{evt.classList.remove('search-match');}, 2000);
                        } else if (tries < 30) { // jusqu'à 3 secondes
                            tries++;
                            setTimeout(tryHighlight, 100);
                        } else {
                            console.warn('Événement non trouvé dans le DOM après 3s', msgId);
                        }
                    }
                    tryHighlight();
                } else {
                    alert(`Impossible d'ouvrir le panneau latéral : pays non reconnu pour l'événement ${msgId} (country='${country}')`);
                }
                modal.remove();
            };
            item.onkeydown = (e) => { if (e.key === 'Enter') item.click(); };
        });
    }

    // Inject styles for highlighting matches (one-time)
    if (!document.getElementById('search-match-style')) {
        const style = document.createElement('style');
        style.id = 'search-match-style';
        style.innerHTML = `
            .search-match { background: #2e5c8a !important; color: #fff !important; box-shadow: 0 0 0 3px #22c55e; transition: background 0.2s; }
            .search-hl { background: #ffe066; color: #222; border-radius: 3px; padding: 0 2px; }
        `;
        document.head.appendChild(style);
    }
}
