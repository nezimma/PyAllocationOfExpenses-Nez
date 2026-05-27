// ─── CHALLENGES MODULE ────────────────────────────────────────────────────────

let CHALLENGES = [];
let ALL_ACHIEVEMENTS = [];
let USER_ACHIEVEMENTS = [];

// ── API helpers ──

async function apiGetChallenges(telegramId) {
  const r = await fetch(`${API_BASE}/api/challenges/${telegramId}`, { headers: _hdrs });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

async function apiGetAchievements(telegramId) {
  const r = await fetch(`${API_BASE}/api/achievements/${telegramId}`, { headers: _hdrs });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

async function apiDeleteChallenge(challengeId) {
  const r = await fetch(`${API_BASE}/api/challenge/${challengeId}`, {
    method: 'DELETE', headers: _hdrs,
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
}

// ── Load ──

async function loadChallenges() {
  const telegramId = getTelegramId();
  if (!telegramId) {
    CHALLENGES = [];
    ALL_ACHIEVEMENTS = [];
    USER_ACHIEVEMENTS = [];
    renderChallengesTab();
    return;
  }
  try {
    CHALLENGES = await apiGetChallenges(telegramId);
  } catch (e) {
    console.warn('Challenges API unavailable:', e);
    CHALLENGES = [];
  }
  try {
    const ach = await apiGetAchievements(telegramId);
    ALL_ACHIEVEMENTS = ach.all || [];
    USER_ACHIEVEMENTS = ach.earned || [];
  } catch (e) {
    console.warn('Achievements API unavailable:', e);
    ALL_ACHIEVEMENTS = [];
    USER_ACHIEVEMENTS = [];
  }
  renderChallengesTab();
}

// ── Render ──

function renderChallengesTab() {
  renderActiveChallenges();
  renderAchievements();
}

function renderActiveChallenges() {
  const container = document.getElementById('challengesList');
  if (!container) return;

  const active = CHALLENGES.filter(c => c.status === 'active');
  const past   = CHALLENGES.filter(c => c.status !== 'active').slice(0, 5);

  if (active.length === 0 && past.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state__icon">🎯</div>
        <div class="empty-state__text">Нет вызовов.<br>Запиши несколько трат — бот предложит цель автоматически!</div>
      </div>`;
    return;
  }

  let html = '';
  if (active.length > 0) {
    html += `<div class="challenges-section-title">Активные</div>`;
    html += active.map(buildChallengeCard).join('');
  }
  if (past.length > 0) {
    html += `<div class="challenges-section-title challenges-section-title--past">Завершённые</div>`;
    html += past.map(buildChallengeCard).join('');
  }
  container.innerHTML = html;

  // Cancel buttons
  container.querySelectorAll('.challenge-card__cancel').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = +btn.dataset.id;
      if (!confirm('Отменить вызов?')) return;
      try {
        await apiDeleteChallenge(id);
        await loadChallenges();
      } catch (e) {
        alert('Ошибка отмены: ' + e.message);
      }
    });
  });
}

function buildChallengeCard(c) {
  const target  = parseFloat(c.target_amount) || 0;
  const spent   = parseFloat(c.spent_amount)  || 0;
  const pct     = target > 0 ? Math.min(100, Math.round(spent / target * 100)) : 0;
  const remaining = Math.max(0, target - spent);
  const sym     = CURRENCY_SYMBOLS[c.currency] || 'Br';

  const statusIcon = { active: '🎯', success: '🏆', failed: '💸', cancelled: '🚫' }[c.status] || '🎯';
  const statusLabel = { active: 'активный', success: 'выполнен', failed: 'провален', cancelled: 'отменён' }[c.status] || '';

  const periodEnd = c.period_end ? new Date(c.period_end) : null;
  const daysLeft  = periodEnd
    ? Math.max(0, Math.ceil((periodEnd - Date.now()) / 86400000))
    : 0;

  const barColor = pct >= 90 ? '#FF6B6B' : pct >= 70 ? '#F7DC6F' : 'var(--accent)';
  const isActive = c.status === 'active';

  return `
    <div class="challenge-card challenge-card--${c.status}">
      <div class="challenge-card__header">
        <span class="challenge-card__icon">${statusIcon}</span>
        <div class="challenge-card__meta">
          <span class="challenge-card__title">${c.category_label}</span>
          <span class="challenge-card__status">${statusLabel}</span>
        </div>
        ${isActive ? `<span class="challenge-card__days">${daysLeft} дн.</span>` : ''}
      </div>
      <div class="challenge-card__progress">
        <div class="challenge-card__bar-bg">
          <div class="challenge-card__bar-fill" style="width:${pct}%;background:${barColor}"></div>
        </div>
        <span class="challenge-card__pct">${pct}%</span>
      </div>
      <div class="challenge-card__amounts">
        <span class="challenge-card__spent">${spent.toLocaleString('ru-RU', {maximumFractionDigits:0})} ${sym}</span>
        <span class="challenge-card__sep">из</span>
        <span class="challenge-card__target">${target.toLocaleString('ru-RU', {maximumFractionDigits:0})} ${sym}</span>
        ${isActive ? `<span class="challenge-card__remaining">· осталось ${remaining.toLocaleString('ru-RU', {maximumFractionDigits:0})} ${sym}</span>` : ''}
      </div>
      ${isActive ? `<button class="challenge-card__cancel" data-id="${c.challenge_id}">✕ Отменить</button>` : ''}
    </div>`;
}

function renderAchievements() {
  const container = document.getElementById('achievementsList');
  if (!container) return;

  if (ALL_ACHIEVEMENTS.length === 0) {
    container.innerHTML = '';
    return;
  }

  const earnedCodes = new Set(USER_ACHIEVEMENTS.map(a => a.code));

  container.innerHTML = ALL_ACHIEVEMENTS.map(a => {
    const isEarned = earnedCodes.has(a.code);
    return `
      <div class="achievement-badge ${isEarned ? 'achievement-badge--earned' : 'achievement-badge--locked'}"
           title="${a.description}">
        <span class="achievement-badge__icon">${isEarned ? a.icon : '🔒'}</span>
        <span class="achievement-badge__title">${a.title}</span>
      </div>`;
  }).join('');
}

// ── Page navigation (патчим обработчик из reminders.js) ──
// Вызывается из обновлённого reminders.js при переключении на вкладку 'challenges'
