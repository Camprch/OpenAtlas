export function renderFilters(filters, selected, onChange) {
  const optionsDiv = document.getElementById('filter-menu-options');
  optionsDiv.innerHTML = '';
  const columns = document.createElement('div');
  columns.id = 'filter-columns';
  const categories = [
    { key: 'active', label: 'Activ ✨' },
    { key: 'date', label: 'Date 📅' },
    { key: 'source', label: 'Source 📱' },
    { key: 'label', label: 'Label 🏷️' },
  ];
  categories.forEach(cat => {
    const col = document.createElement('div');
    col.className = 'filter-col';
    const title = document.createElement('div');
    title.className = 'filter-col-title';
    title.textContent = cat.label;
    col.appendChild(title);
    const list = document.createElement('div');
    list.className = 'filter-options-list';
    if (cat.key === 'active') {
      const activePairs = [];
      for (const k of ['date', 'source', 'label']) {
        const vals = Array.from(selected[k] || []);
        for (const v of vals) {
          activePairs.push({ key: k, value: v });
        }
      }
      if (activePairs.length === 0) {
        list.textContent = 'Aucun filtre actif.';
      } else {
        activePairs.forEach(item => {
          const chip = document.createElement('button');
          chip.type = 'button';
          chip.className = 'filter-active-chip';
          chip.textContent = item.value;
          chip.addEventListener('click', (e) => {
            if (e && e.stopPropagation) e.stopPropagation();
            selected[item.key].delete(item.value);
            onChange();
            renderFilters(filters, selected, onChange);
          });
          list.appendChild(chip);
        });
      }
      col.appendChild(list);
      columns.appendChild(col);
      return;
    }
    const values = filters[cat.key] || [];
    if (!values.length) {
      list.textContent = 'Aucune option.';
    } else {
      values.forEach(val => {
        const label = document.createElement('label');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = val;
        checkbox.checked = selected[cat.key].has(val);
        checkbox.addEventListener('change', () => {
          if (checkbox.checked) {
            selected[cat.key].add(val);
          } else {
            selected[cat.key].delete(val);
          }
          onChange();
          renderFilters(filters, selected, onChange);
        });
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(val));
        list.appendChild(label);
      });
    }
    col.appendChild(list);
    columns.appendChild(col);
  });
  optionsDiv.appendChild(columns);
}

export function setupFilterMenuHandlers({ filterMenu, filterBtn, filterClose, filterMenuOptions, mapEl, onOpen, onClose }) {
  let filterColumns = null;

  function handleFilterMenuClick(e) {
    const target = e.target;
    if (target instanceof Element && target.closest('.filter-active-chip')) {
      return;
    }
    if (
      target === filterMenu ||
      target === filterMenuOptions ||
      target === filterColumns ||
      (target instanceof Element && target.classList.contains('filter-options-list'))
    ) {
      onClose();
    }
  }

  filterBtn.addEventListener('click', () => {
    const open = filterMenu.style.display !== 'none' && filterMenu.style.display !== '';
    if (open) {
      onClose();
    } else {
      onOpen();
      filterColumns = document.getElementById('filter-columns');
    }
  });

  filterClose.addEventListener('click', onClose);
  filterMenu.addEventListener('click', handleFilterMenuClick);
  document.addEventListener('click', (e) => {
    if (filterMenu.style.display === 'none' || filterMenu.style.display === '') return;
    const target = e.target;
    if (target === filterBtn || filterBtn.contains(target)) return;
    if (target === filterMenu || filterMenu.contains(target)) return;
    onClose();
  });

  if (mapEl) {
    mapEl.addEventListener('mousedown', () => {
      if (filterMenu.style.display !== 'none' && filterMenu.style.display !== '') {
        onClose();
      }
    });
  }
}
