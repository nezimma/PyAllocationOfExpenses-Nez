// ─── REMINDERS MODULE ─────────────────────────

// ── API helpers ──
function getTelegramId() {
  return window.Telegram?.WebApp?.initDataUnsafe?.user?.id || null;
}

const _hdrs = { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' };

async function apiGetReminders(telegramId) {
  const r = await fetch(`${API_BASE}/api/reminders/${telegramId}`, { headers: _hdrs });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

async function apiCreateReminder(telegramId, payload) {
  const r = await fetch(`${API_BASE}/api/reminders/${telegramId}`, {
    method: 'POST', headers: _hdrs, body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

async function apiUpdateReminder(reminderId, payload) {
  const r = await fetch(`${API_BASE}/api/reminder/${reminderId}`, {
    method: 'PUT', headers: _hdrs, body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
}

async function apiDeleteReminder(reminderId) {
  const r = await fetch(`${API_BASE}/api/reminder/${reminderId}`, {
    method: 'DELETE', headers: _hdrs,
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
}

async function apiToggleReminder(reminderId) {
  const r = await fetch(`${API_BASE}/api/reminders/${reminderId}/toggle`, {
    method: 'PATCH', headers: _hdrs,
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

async function apiCheckin(reminderId, dateStr) {
  const r = await fetch(`${API_BASE}/api/reminders/${reminderId}/checkin`, {
    method: 'POST', headers: _hdrs,
    body: JSON.stringify({ date: dateStr }),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ── Data store ──
let REMINDERS = [];
let remState = { typeFilter: 'all', editingId: null };

// ── Load from API ──
async function loadReminders() {
  const telegramId = getTelegramId();
  if (!telegramId) {
    REMINDERS = [];
    renderReminders();
    return;
  }
  try {
    REMINDERS = await apiGetReminders(telegramId);
  } catch (e) {
    console.warn('Reminders API unavailable:', e);
    REMINDERS = [];
  }
  renderReminders();
}

// ── Page navigation ──
const expensesPage   = document.getElementById('expensesPage');
const remindersPage  = document.getElementById('remindersPage');
const challengesPage = document.getElementById('challengesPage');
const expensePeriodControls = document.getElementById('expensePeriodControls');
const headerTitle    = document.getElementById('headerTitle');

document.querySelectorAll('.nav-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');

    const page = tab.dataset.page;
    expensesPage.classList.toggle('hidden', page !== 'expenses');
    remindersPage.classList.toggle('hidden', page !== 'reminders');
    if (challengesPage) challengesPage.classList.toggle('hidden', page !== 'challenges');
    expensePeriodControls.style.display = page === 'expenses' ? '' : 'none';

    if (page === 'expenses') {
      headerTitle.textContent = 'Расходы';
    } else if (page === 'reminders') {
      headerTitle.textContent = 'Напоминания';
      loadReminders();
    } else if (page === 'challenges') {
      headerTitle.textContent = 'Вызовы';
      loadChallenges();
    }
  });
});

// ── Type filter ──
document.querySelectorAll('.rem-type-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.rem-type-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    remState.typeFilter = tab.dataset.type;
    const titles = { all: 'Все напоминания', reminder: 'Разовые уведомления', habit: 'Привычки', goal: 'Цели' };
    document.getElementById('remListTitle').textContent = titles[remState.typeFilter];
    renderReminders();
  });
});

// ── Render reminders ──
function renderReminders() {
  updateStats();
  const list = document.getElementById('remindersList');
  const filtered = remState.typeFilter === 'all'
    ? REMINDERS
    : REMINDERS.filter(r => r.type === remState.typeFilter);

  if (filtered.length === 0) {
    list.innerHTML = `
      <div class="rem-empty">
        <div class="rem-empty__icon">🔔</div>
        <div class="rem-empty__text">Нет напоминаний.<br>Создайте первое!</div>
        <button class="rem-add-btn" style="margin:0 auto" onclick="openCreateReminder()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Создать
        </button>
      </div>`;
    return;
  }

  list.innerHTML = filtered.map((r, i) => buildCard(r, i)).join('');

  list.querySelectorAll('[data-action]').forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      const id = +btn.closest('[data-rid]').dataset.rid;
      const action = btn.dataset.action;
      if (action === 'toggle') toggleActive(id);
      else if (action === 'edit') openEditReminder(id);
      else if (action === 'delete') deleteReminder(id);
      else if (action === 'view') openGoalDetail(id);
    });
  });
}

function buildCard(r, i) {
  const typeIcon   = { reminder: '🔔', habit: '🔁', goal: '🎯' }[r.type];
  const iconClass  = { reminder: '', habit: 'rem-card__icon--habit', goal: 'rem-card__icon--goal' }[r.type];
  const badgeClass = `rem-card__badge--${r.type}`;
  const typeLabel  = { reminder: 'Разовое', habit: 'Привычка', goal: 'Цель' }[r.type];

  let extraMeta = '';
  let extra = '';

  if (r.type === 'habit') {
    const streak = calcStreak(r);
    extraMeta = `<span>каждые ${r.interval} д.</span>`;
    extra = `<div class="habit-streak">🔥 ${streak} дней подряд</div>`;
  }

  if (r.type === 'goal') {
    const { pct, daysLeft, total, done } = calcGoalProgress(r);
    extraMeta = `<span>до ${fmtDate(r.endDate)}</span>`;
    extra = `
      <div class="goal-progress">
        <div class="goal-progress__label">
          <span>Выполнено ${done} из ${total} раз</span>
          <span>${pct}%</span>
        </div>
        <div class="goal-progress__bar">
          <div class="goal-progress__fill" style="width:${pct}%"></div>
        </div>
      </div>`;
  }

  const activeLabel = r.active ? 'Вкл' : 'Выкл';
  const toggleClass = r.active ? 'on' : '';

  const viewBtn = r.type === 'goal'
    ? `<button class="rem-card__action rem-card__action--view" data-action="view">📊 Прогресс</button>`
    : '';

  return `
    <li class="rem-card ${r.active ? '' : 'rem-card--inactive'}" data-rid="${r.id}" style="animation-delay:${i * 0.04}s">
      <div class="rem-card__top">
        <div class="rem-card__icon ${iconClass}">${typeIcon}</div>
        <div class="rem-card__info">
          <div class="rem-card__title">${r.title}</div>
          <div class="rem-card__meta">
            <span class="rem-card__badge ${badgeClass}">${typeLabel}</span>
            <span>${fmtDate(r.date)} · ${r.time}</span>
            ${extraMeta}
          </div>
          ${extra}
        </div>
      </div>
      <div class="rem-card__actions">
        <button class="rem-card__action rem-card__action--toggle ${toggleClass}" data-action="toggle">
          ${r.active ? '⏸ ' + activeLabel : '▶ ' + activeLabel}
        </button>
        ${viewBtn}
        <button class="rem-card__action rem-card__action--edit" data-action="edit">✎ Изменить</button>
        <button class="rem-card__action--delete" data-action="delete">🗑</button>
      </div>
    </li>`;
}

// ── Stats ──
function updateStats() {
  const today = new Date().toISOString().slice(0, 10);
  document.getElementById('statTotal').textContent  = REMINDERS.length;
  document.getElementById('statActive').textContent = REMINDERS.filter(r => r.active).length;
  document.getElementById('statToday').textContent  = REMINDERS.filter(r => r.active && r.date === today).length;
}

// ── Helpers ──
function fmtDate(d) {
  if (!d) return '';
  const [y, m, day] = d.split('-');
  return `${day}.${m}.${y}`;
}

function calcStreak(r) {
  if (!r.checkins || r.checkins.length === 0) return 0;
  const sorted = [...r.checkins].sort().reverse();
  let streak = 0;
  let cur = new Date();
  for (const d of sorted) {
    const diff = Math.round((cur - new Date(d)) / 86400000);
    if (diff <= 1 + streak * (r.interval || 1)) streak++;
    else break;
  }
  return streak;
}

function calcGoalProgress(r) {
  if (!r.endDate) return { pct: 0, daysLeft: 0, total: 0, done: 0 };
  const start  = new Date(r.date);
  const end    = new Date(r.endDate);
  const today  = new Date();
  const totalDays = Math.round((end - start) / 86400000);
  const interval  = r.interval || 1;
  const total     = Math.ceil(totalDays / interval);
  const done      = (r.checkins || []).length;
  const pct       = total > 0 ? Math.min(100, Math.round(done / total * 100)) : 0;
  const daysLeft  = Math.max(0, Math.round((end - today) / 86400000));
  return { pct, daysLeft, total, done };
}

// ── Toggle active ──
async function toggleActive(id) {
  const r = REMINDERS.find(r => r.id === id);
  if (!r) return;
  if (r.type !== 'habit') return; // только привычки имеют active в БД

  try {
    const res = await apiToggleReminder(id);
    r.active = res.active;
  } catch (e) {
    console.error('Toggle failed:', e);
  }
  renderReminders();
}

// ── Delete ──
async function deleteReminder(id) {
  try {
    await apiDeleteReminder(id);
    REMINDERS = REMINDERS.filter(r => r.id !== id);
  } catch (e) {
    console.error('Delete failed:', e);
  }
  renderReminders();
}

// ── Create/Edit modal ──
const reminderModalOverlay = document.getElementById('reminderModalOverlay');
let currentStep = 1;
let selectedRType = 'reminder';

function openCreateReminder() {
  remState.editingId = null;
  currentStep = 1;
  selectedRType = 'reminder';
  document.getElementById('reminderModalTitle').textContent = 'Новое напоминание';

  document.getElementById('remTitle').value = '';
  document.getElementById('remDate').value  = '';
  document.getElementById('remTime').value  = '';
  document.getElementById('remInterval').value = '';
  document.getElementById('remEndDate').value  = '';
  document.getElementById('remStep1').classList.remove('hidden');
  document.getElementById('remStep2').classList.add('hidden');
  setModalStep(1);

  document.querySelectorAll('.rem-type-card').forEach(c => c.classList.remove('active'));
  document.querySelector('[data-rtype="reminder"]').classList.add('active');
  document.getElementById('remExtraFields').classList.add('hidden');
  document.getElementById('remEndDateField').classList.add('hidden');

  reminderModalOverlay.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function openEditReminder(id) {
  const r = REMINDERS.find(r => r.id === id);
  if (!r) return;
  remState.editingId = id;
  currentStep = 1;
  selectedRType = r.type;
  document.getElementById('reminderModalTitle').textContent = 'Изменить';

  document.getElementById('remTitle').value = r.title;
  document.getElementById('remDate').value  = r.date;
  document.getElementById('remTime').value  = r.time;
  document.getElementById('remInterval').value = r.interval || '';
  document.getElementById('remEndDate').value  = r.endDate || '';

  document.getElementById('remStep1').classList.remove('hidden');
  document.getElementById('remStep2').classList.add('hidden');
  setModalStep(1);

  reminderModalOverlay.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeReminderModal() {
  reminderModalOverlay.classList.remove('open');
  document.body.style.overflow = '';
  remState.editingId = null;
}

function setModalStep(step) {
  currentStep = step;
  document.querySelectorAll('.modal-step').forEach(s => {
    const n = +s.dataset.step;
    s.classList.remove('active', 'done');
    if (n === step) s.classList.add('active');
    else if (n < step) s.classList.add('done');
  });
}

document.getElementById('reminderModalClose').addEventListener('click', closeReminderModal);
reminderModalOverlay.addEventListener('click', e => { if (e.target === reminderModalOverlay) closeReminderModal(); });

document.getElementById('remStep1Next').addEventListener('click', () => {
  const title = document.getElementById('remTitle').value.trim();
  const date  = document.getElementById('remDate').value;
  const time  = document.getElementById('remTime').value;
  if (!title || !date || !time) {
    shakeField(title ? (date ? 'remTime' : 'remDate') : 'remTitle');
    return;
  }
  document.getElementById('remStep1').classList.add('hidden');
  document.getElementById('remStep2').classList.remove('hidden');
  setModalStep(2);

  document.querySelectorAll('.rem-type-card').forEach(c => c.classList.remove('active'));
  document.querySelector(`[data-rtype="${selectedRType}"]`).classList.add('active');
  updateExtraFields(selectedRType);
});

document.getElementById('remStep2Back').addEventListener('click', () => {
  document.getElementById('remStep2').classList.add('hidden');
  document.getElementById('remStep1').classList.remove('hidden');
  setModalStep(1);
});

document.querySelectorAll('.rem-type-card').forEach(card => {
  card.addEventListener('click', () => {
    document.querySelectorAll('.rem-type-card').forEach(c => c.classList.remove('active'));
    card.classList.add('active');
    selectedRType = card.dataset.rtype;
    updateExtraFields(selectedRType);
  });
});

function updateExtraFields(type) {
  const extra    = document.getElementById('remExtraFields');
  const endField = document.getElementById('remEndDateField');
  if (type === 'reminder') {
    extra.classList.add('hidden');
    endField.classList.add('hidden');
  } else {
    extra.classList.remove('hidden');
    endField.classList.toggle('hidden', type !== 'goal');
  }
}

function shakeField(id) {
  const el = document.getElementById(id);
  el.style.borderColor = '#F44336';
  el.focus();
  setTimeout(() => el.style.borderColor = '', 1500);
}

// ── Save ──
document.getElementById('remSave').addEventListener('click', async () => {
  const title    = document.getElementById('remTitle').value.trim();
  const date     = document.getElementById('remDate').value;
  const time     = document.getElementById('remTime').value;
  const interval = +document.getElementById('remInterval').value || 1;
  const endDate  = document.getElementById('remEndDate').value || null;

  if (!title || !date || !time) return;
  if ((selectedRType === 'habit' || selectedRType === 'goal') && !interval) {
    shakeField('remInterval'); return;
  }
  if (selectedRType === 'goal' && !endDate) {
    shakeField('remEndDate'); return;
  }

  const payload = {
    title, date, time, type: selectedRType,
    interval: selectedRType !== 'reminder' ? interval : 1,
    endDate:  selectedRType === 'goal' ? endDate : null,
  };

  const saveBtn = document.getElementById('remSave');
  saveBtn.disabled = true;

  try {
    if (remState.editingId) {
      await apiUpdateReminder(remState.editingId, payload);
      const idx = REMINDERS.findIndex(r => r.id === remState.editingId);
      if (idx !== -1) REMINDERS[idx] = { ...REMINDERS[idx], ...payload, id: remState.editingId };
    } else {
      const telegramId = getTelegramId();
      if (!telegramId) { console.error('No telegram user id'); return; }
      const res = await apiCreateReminder(telegramId, payload);
      REMINDERS.push({ id: res.id, active: true, checkins: [], ...payload });
    }
    closeReminderModal();
    renderReminders();
  } catch (e) {
    console.error('Save reminder failed:', e);
  } finally {
    saveBtn.disabled = false;
  }
});

// ── Goal detail modal ──
const goalModalOverlay = document.getElementById('goalModalOverlay');

function openGoalDetail(id) {
  const r = REMINDERS.find(r => r.id === id);
  if (!r || r.type !== 'goal') return;

  const { pct, daysLeft, total, done } = calcGoalProgress(r);
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (pct / 100) * circumference;

  document.getElementById('goalModalTitle').textContent = r.title;
  document.getElementById('goalModalBody').innerHTML = `
    <div class="goal-detail-ring">
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx="70" cy="70" r="54" fill="none" stroke="var(--bg-elevated)" stroke-width="12"/>
        <circle cx="70" cy="70" r="54" fill="none" stroke="url(#goalGrad)" stroke-width="12"
          stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"
          stroke-linecap="round" style="transition:stroke-dashoffset 0.8s ease"/>
        <defs>
          <linearGradient id="goalGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#F7DC6F"/>
            <stop offset="100%" stop-color="#f0a500"/>
          </linearGradient>
        </defs>
      </svg>
    </div>
    <div class="goal-ring-text">
      <div class="goal-ring-pct">${pct}%</div>
      <div class="goal-ring-label">выполнено</div>
    </div>
    <div class="goal-timeline">
      <div class="goal-timeline-item">
        <div class="goal-timeline-dot" style="background:#4CAF50"></div>
        <span>Выполнено раз: <strong>${done}</strong></span>
      </div>
      <div class="goal-timeline-item">
        <div class="goal-timeline-dot" style="background:var(--accent)"></div>
        <span>Всего раз по плану: <strong>${total}</strong></span>
      </div>
      <div class="goal-timeline-item">
        <div class="goal-timeline-dot" style="background:#F7DC6F"></div>
        <span>Осталось дней: <strong>${daysLeft}</strong></span>
      </div>
      <div class="goal-timeline-item">
        <div class="goal-timeline-dot" style="background:var(--text-dim)"></div>
        <span>Период: <strong>${fmtDate(r.date)} — ${fmtDate(r.endDate)}</strong></span>
      </div>
    </div>
    <button class="goal-checkin-btn" id="goalCheckinBtn">✅ Отметить выполнение сегодня</button>
  `;

  document.getElementById('goalCheckinBtn').addEventListener('click', async () => {
    const today = new Date().toISOString().slice(0, 10);
    const btn = document.getElementById('goalCheckinBtn');
    if (r.checkins.includes(today)) {
      btn.textContent = '✓ Уже отмечено сегодня';
      btn.style.opacity = '0.5';
      return;
    }
    btn.disabled = true;
    try {
      await apiCheckin(r.id, today);
      r.checkins.push(today);
      openGoalDetail(id);
      renderReminders();
    } catch (e) {
      console.error('Checkin failed:', e);
      btn.disabled = false;
    }
  });

  goalModalOverlay.classList.add('open');
  document.body.style.overflow = 'hidden';
}

document.getElementById('goalModalClose').addEventListener('click', () => {
  goalModalOverlay.classList.remove('open');
  document.body.style.overflow = '';
});
goalModalOverlay.addEventListener('click', e => {
  if (e.target === goalModalOverlay) {
    goalModalOverlay.classList.remove('open');
    document.body.style.overflow = '';
  }
});

// ── Expose for inline onclick ──
window.openCreateReminder = openCreateReminder;

// ── Bind create button ──
document.getElementById('openCreateReminder').addEventListener('click', openCreateReminder);
