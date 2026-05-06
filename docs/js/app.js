// ─── APP ─────────────────────────────────────

let state = {
  search: '',
  selectedCats: new Set(['all']),
  multiSelect: false,
  sort: 'date-desc',
  editingId: null,
  periodOffset: 0,  // 0 = current period, -1 = previous, etc.
};

// ── Telegram Mini App init ──
if (window.Telegram?.WebApp) {
  const tg = window.Telegram.WebApp;
  tg.ready();
  tg.expand();
  const tgTheme = tg.colorScheme;
  if (tgTheme) document.documentElement.dataset.theme = tgTheme;
}

// ── Theme toggle ──
document.getElementById('themeToggle').addEventListener('click', () => {
  const curr = document.documentElement.dataset.theme;
  document.documentElement.dataset.theme = curr === 'dark' ? 'light' : 'dark';
  renderChart(currentChartType, getFiltered(), getActivePeriod());
});

// ── Period buttons ──
document.querySelectorAll('.period-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.periodOffset = 0;
    render();
  });
});

// ── Period navigation ──
document.getElementById('periodPrev').addEventListener('click', () => {
  state.periodOffset -= 1;
  render();
});

document.getElementById('periodNext').addEventListener('click', () => {
  if (state.periodOffset < 0) {
    state.periodOffset += 1;
    render();
  }
});

// ── Chart tab buttons ──
document.querySelectorAll('.chart-tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.chart-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderChart(btn.dataset.chart, getFiltered(), getActivePeriod());
  });
});

// ── Multi-select toggle ──
document.getElementById('multiSelectToggle').addEventListener('change', e => {
  state.multiSelect = e.target.checked;
  if (!state.multiSelect) {
    const cats = [...state.selectedCats].filter(c => c !== 'all');
    state.selectedCats = new Set([cats[cats.length - 1] || 'all']);
    updateChips();
    render();
  }
});

// ── Category chips ──
document.getElementById('categoryChips').addEventListener('click', e => {
  const chip = e.target.closest('.chip');
  if (!chip) return;
  const cat = chip.dataset.cat;

  if (!state.multiSelect) {
    state.selectedCats = new Set([cat]);
  } else {
    if (cat === 'all') {
      state.selectedCats = new Set(['all']);
    } else {
      state.selectedCats.delete('all');
      if (state.selectedCats.has(cat)) {
        state.selectedCats.delete(cat);
        if (state.selectedCats.size === 0) state.selectedCats.add('all');
      } else {
        state.selectedCats.add(cat);
      }
    }
  }

  updateChips();
  render();
});

function updateChips() {
  document.querySelectorAll('.chip').forEach(chip => {
    chip.classList.toggle('active', state.selectedCats.has(chip.dataset.cat));
  });
}

// ── Search ──
const searchInput = document.getElementById('searchInput');
const searchClear = document.getElementById('searchClear');

searchInput.addEventListener('input', e => {
  state.search = e.target.value.trim().toLowerCase();
  searchClear.classList.toggle('visible', state.search.length > 0);
  render();
});

searchClear.addEventListener('click', () => {
  searchInput.value = '';
  state.search = '';
  searchClear.classList.remove('visible');
  render();
});

// ── Sort ──
document.getElementById('sortBtn').addEventListener('click', () => {
  state.sort = state.sort === 'date-desc' ? 'amount-desc' : 'date-desc';
  document.getElementById('sortBtn').innerHTML = `
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg>
    ${state.sort === 'date-desc' ? 'По дате' : 'По сумме'}
  `;
  render();
});

// ── Period helpers ──
function getActivePeriod() {
  return document.querySelector('.period-btn.active')?.dataset.period || 'month';
}

function getPeriodRange(period, offset = 0) {
  const now = new Date();

  if (period === 'week') {
    const dow = now.getDay(); // 0=Sun
    const daysToMonday = dow === 0 ? -6 : 1 - dow;
    const monday = new Date(now);
    monday.setDate(now.getDate() + daysToMonday + offset * 7);
    monday.setHours(0, 0, 0, 0);
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    sunday.setHours(23, 59, 59, 999);
    return { start: monday, end: sunday };
  }

  if (period === 'month') {
    const start = new Date(now.getFullYear(), now.getMonth() + offset, 1, 0, 0, 0, 0);
    const end = new Date(now.getFullYear(), now.getMonth() + offset + 1, 0, 23, 59, 59, 999);
    return { start, end };
  }

  // year
  const year = now.getFullYear() + offset;
  return {
    start: new Date(year, 0, 1, 0, 0, 0, 0),
    end:   new Date(year, 11, 31, 23, 59, 59, 999),
  };
}

function getPeriodLabel(period, offset) {
  const { start } = getPeriodRange(period, offset);

  if (period === 'week') {
    const { end } = getPeriodRange(period, offset);
    const fmt = d => d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
    return `${fmt(start)} — ${fmt(end)}`;
  }
  if (period === 'month') {
    return start.toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' });
  }
  return String(start.getFullYear());
}

// ── Filtering ──
function getFiltered() {
  const period = getActivePeriod();
  const { start, end } = getPeriodRange(period, state.periodOffset);

  let list = EXPENSES.filter(e => {
    const d = new Date(e.date);
    return d >= start && d <= end;
  });

  if (!state.selectedCats.has('all')) {
    list = list.filter(e => state.selectedCats.has(e.cat));
  }

  if (state.search) {
    list = list.filter(e =>
      e.name.toLowerCase().includes(state.search) ||
      CATEGORIES[e.cat]?.label.toLowerCase().includes(state.search)
    );
  }

  if (state.sort === 'date-desc') {
    list.sort((a, b) => b.date.localeCompare(a.date));
  } else {
    list.sort((a, b) => b.amount - a.amount);
  }

  return list;
}

// ── Delta calculation ──
function updateDelta() {
  const period = getActivePeriod();
  const offset = state.periodOffset;

  const { start: s1, end: e1 } = getPeriodRange(period, offset);
  const { start: s2, end: e2 } = getPeriodRange(period, offset - 1);

  const sumPeriod = (s, e) =>
    EXPENSES.filter(exp => { const d = new Date(exp.date); return d >= s && d <= e; })
            .reduce((acc, exp) => acc + exp.amount, 0);

  const current  = sumPeriod(s1, e1);
  const previous = sumPeriod(s2, e2);

  const deltaEl = document.querySelector('.total-card__delta');

  if (previous === 0) {
    deltaEl.innerHTML = `<span class="delta" style="opacity:.6">— нет данных за прошлый период</span>`;
    return;
  }

  const pct = Math.round((current - previous) / previous * 100);
  const up  = pct >= 0;
  deltaEl.innerHTML = `
    <span class="delta delta--${up ? 'up' : 'down'}">${up ? '↑' : '↓'} ${Math.abs(pct)}%</span>
    по сравнению с прошлым периодом
  `;
}

// ── Render ──
function render() {
  const period = getActivePeriod();
  const filtered = getFiltered();

  // Period nav label + next button state
  document.getElementById('periodLabel').textContent = getPeriodLabel(period, state.periodOffset);
  document.getElementById('periodNext').disabled = state.periodOffset >= 0;

  renderChart(currentChartType, filtered, period);
  renderList(filtered);

  const total = filtered.reduce((a, e) => a + e.amount, 0);
  document.getElementById('totalAmount').textContent = total.toLocaleString('ru-RU');
  document.getElementById('expensesCount').textContent =
    filtered.length + ' ' + pluralize(filtered.length, 'запись', 'записи', 'записей');

  updateDelta();
}

function renderList(items) {
  const ul = document.getElementById('expensesList');

  if (items.length === 0) {
    ul.innerHTML = `
      <div class="empty-state">
        <div class="empty-state__icon">🔍</div>
        <div class="empty-state__text">Ничего не найдено.<br>Попробуйте другой запрос или категорию.</div>
      </div>`;
    return;
  }

  ul.innerHTML = items.map((e, i) => {
    const cat = CATEGORIES[e.cat];
    const dt = new Date(e.date);
    const timeStr = dt.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    const dateStr = dt.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
    return `
      <li class="expense-item" data-id="${e.id}" style="animation-delay:${i * 0.03}s">
        <div class="expense-item__emoji" style="background:${cat.color}20">
          ${cat.emoji}
        </div>
        <div class="expense-item__info">
          <div class="expense-item__name">${e.name}</div>
          <div class="expense-item__meta">
            <span class="expense-item__cat-badge" style="background:${cat.color}22;color:${cat.color}">${cat.label}</span>
          </div>
        </div>
        <div class="expense-item__right">
          <div class="expense-item__amount">${e.amount.toLocaleString('ru-RU')} Br</div>
          <div class="expense-item__time">${dateStr}, ${timeStr}</div>
        </div>
        <span class="expense-item__edit-hint">✎</span>
      </li>`;
  }).join('');

  ul.querySelectorAll('.expense-item').forEach(item => {
    item.addEventListener('click', () => openModal(+item.dataset.id));
  });
}

// ── Modal ──
const modalOverlay = document.getElementById('modalOverlay');

function openModal(id) {
  const expense = EXPENSES.find(e => e.id === id);
  if (!expense) return;
  state.editingId = id;

  document.getElementById('editName').value    = expense.name;
  document.getElementById('editAmount').value  = expense.amount;
  document.getElementById('editCategory').value = expense.cat;
  document.getElementById('editDate').value    = expense.date;

  modalOverlay.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  modalOverlay.classList.remove('open');
  document.body.style.overflow = '';
  state.editingId = null;
}

document.getElementById('modalClose').addEventListener('click', closeModal);
document.getElementById('modalCancel').addEventListener('click', closeModal);
modalOverlay.addEventListener('click', e => { if (e.target === modalOverlay) closeModal(); });

document.getElementById('modalSave').addEventListener('click', () => {
  if (!state.editingId) return;
  const idx = EXPENSES.findIndex(e => e.id === state.editingId);
  if (idx === -1) return;

  EXPENSES[idx] = {
    ...EXPENSES[idx],
    name:   document.getElementById('editName').value,
    amount: +document.getElementById('editAmount').value,
    cat:    document.getElementById('editCategory').value,
    date:   document.getElementById('editDate').value,
  };

  closeModal();
  render();
});

// ── Helpers ──
function pluralize(n, one, few, many) {
  const mod10 = n % 10, mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few;
  return many;
}

// ── Init ──
(async () => {
  await loadExpenses();
  render();
})();
