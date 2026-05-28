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

// ═══════════════════════════════════════════════════════
//  PET MINI-SCENE — full animated alien inside the tab
// ═══════════════════════════════════════════════════════

// ── API ──
async function apiGetPet(telegramId) {
  const r = await fetch(`${API_BASE}/api/pet/${telegramId}`, { headers: _hdrs });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ── Stage palettes (mirrors pet.html) ──
const PW_STAGES = {
  1: { name:'НЛО',      bodyMid:'#8090b0',bodyDark:'#505a80',bodyLight:'#c0ccf0',
       bodyGlow:'rgba(100,160,255,.5)',orb:'#88ccff',pupil:'#102050',
       cheek:'rgba(160,200,255,.3)',xpA:'#44aaff',xpB:'#88ddff',dot:'#44aaff',
       petGlow:'rgba(100,180,255,.4)' },
  2: { name:'Малыш',    bodyMid:'#5cbe67',bodyDark:'#2e7a36',bodyLight:'#a8e6ad',
       bodyGlow:'rgba(92,190,103,.55)',orb:'#aaff88',pupil:'#1a4a20',
       cheek:'rgba(255,130,130,.38)',xpA:'#5cbe67',xpB:'#a8e6ad',dot:'#5cbe67',
       petGlow:'rgba(92,190,103,.4)' },
  3: { name:'Странник', bodyMid:'#3a9ee8',bodyDark:'#1355a0',bodyLight:'#90caf9',
       bodyGlow:'rgba(58,158,232,.55)',orb:'#66d4ff',pupil:'#0a2d5a',
       cheek:'rgba(100,200,255,.3)',xpA:'#3a9ee8',xpB:'#90caf9',dot:'#3a9ee8',
       petGlow:'rgba(58,158,232,.4)' },
  4: { name:'Маг',      bodyMid:'#b44fd4',bodyDark:'#6a1a8a',bodyLight:'#e0b0f0',
       bodyGlow:'rgba(180,79,212,.55)',orb:'#dd99ff',pupil:'#3d0a5a',
       cheek:'rgba(220,120,255,.32)',xpA:'#b44fd4',xpB:'#e0b0f0',dot:'#b44fd4',
       petGlow:'rgba(180,79,212,.4)' },
  5: { name:'Лорд',     bodyMid:'#f0c030',bodyDark:'#b06000',bodyLight:'#fff0a0',
       bodyGlow:'rgba(240,192,48,.6)',orb:'#fffacc',pupil:'#5a2800',
       cheek:'rgba(255,190,60,.38)',xpA:'#f0c030',xpB:'#fff0a0',dot:'#f0c030',
       petGlow:'rgba(240,192,48,.45)' },
};

function xpForLevel(n) { return 50 * n * (n - 1); }

// ── State ──
let _petCanvasRAF   = null;   // requestAnimationFrame id for stars
let _petIdleTimer   = null;   // idle variety timeout
let _petSceneReady  = false;  // canvas initialised at least once

// ── Main entry point (called from reminders.js on tab switch) ──
async function loadPetPage() {
  const telegramId = getTelegramId();

  // Fetch pet data
  let petData = null;
  if (telegramId) {
    try { petData = await apiGetPet(telegramId); }
    catch (e) { console.warn('Pet API unavailable:', e); }
  }
  if (!petData) {
    petData = { level:1, xp:0, xp_in_level:0, xp_for_next_level:100,
                day_streak:0, entries_this_week:0, stage:2, env:0, animation:'idle' };
  }
  petData.stage = Math.max(1, Math.min(5, petData.stage || 2));

  // Apply visuals
  applyPetMiniStage(petData.stage, petData.env);
  renderPetInfoBar(petData);
  playPetMiniAnimation(petData.animation || 'idle');

  // Init canvas on first show (needs layout to be visible for correct size)
  if (!_petSceneReady) {
    setTimeout(() => { initPetMiniCanvas(petData.env, petData.stage); _petSceneReady = true; }, 60);
  }

  // Idle charm timer (restart each time tab is opened)
  clearTimeout(_petIdleTimer);
  schedulePetIdleCharm();

  // Tap/click interaction
  const wrap = document.getElementById('petMiniWrap');
  if (wrap && !wrap._tapBound) {
    wrap._tapBound = true;
    wrap.addEventListener('click', () => {
      const anim = wrap.dataset.anim || 'idle';
      if (['pw-eating','pw-celebrating','pw-sleeping','pw-levelup'].some(c => wrap.classList.contains(c))) return;
      wrap.classList.add('pw-tap');
      spawnPetHearts(document.getElementById('petMiniParticles'), 5);
      setTimeout(() => wrap.classList.remove('pw-tap'), 520);
    });
  }

  // Load challenges & achievements in parallel
  if (telegramId) {
    try { CHALLENGES = await apiGetChallenges(telegramId); }
    catch (e) { CHALLENGES = []; }
    try {
      const ach = await apiGetAchievements(telegramId);
      ALL_ACHIEVEMENTS = ach.all || [];
      USER_ACHIEVEMENTS = ach.earned || [];
    } catch (e) { ALL_ACHIEVEMENTS = []; USER_ACHIEVEMENTS = []; }
  }
  renderActiveChallenges();
  renderAchievements();
}

// ── Apply stage colors & show UFO or alien ──
function applyPetMiniStage(stage, env) {
  const st  = PW_STAGES[stage] || PW_STAGES[2];
  const css = document.documentElement.style;
  css.setProperty('--pw-body-mid',   st.bodyMid);
  css.setProperty('--pw-body-dark',  st.bodyDark);
  css.setProperty('--pw-body-light', st.bodyLight);
  css.setProperty('--pw-body-glow',  st.bodyGlow);
  css.setProperty('--pw-orb',        st.orb);
  css.setProperty('--pw-pupil',      st.pupil);
  css.setProperty('--pw-cheek',      st.cheek);
  css.setProperty('--pw-pet-glow',   st.petGlow);
  css.setProperty('--pw-xp-a',       st.xpA);
  css.setProperty('--pw-xp-b',       st.xpB);
  css.setProperty('--pw-dot',        st.dot);

  const ufoEl  = document.getElementById('petMiniUfo');
  const charEl = document.getElementById('petMiniChar');
  if (stage === 1) {
    ufoEl?.classList.add('active');
    charEl?.classList.remove('active');
  } else {
    ufoEl?.classList.remove('active');
    charEl?.classList.add('active');
    charEl?.setAttribute('data-stage', stage);
  }

  // Environment
  document.getElementById('petSceneNebula')?.classList.toggle('visible', (env||0) >= 2);
  document.getElementById('petScenePlanet')?.classList.toggle('visible', (env||0) >= 1);

  // Name badge
  const nameEl = document.getElementById('petSceneName');
  if (nameEl) nameEl.textContent = `NEBULA-${stage} · ${st.name}`;
}

// ── Render XP bar + week dots below the card ──
function renderPetInfoBar(data) {
  const level   = data.level || 1;
  const xp      = data.xp || 0;
  const streak  = data.day_streak || 0;
  const entries = data.entries_this_week || 0;

  // Overlay: level + streak
  const lvlEl = document.getElementById('petSceneLevel');
  const strEl = document.getElementById('petSceneStreak');
  if (lvlEl) lvlEl.textContent = `Уровень ${level}`;
  if (strEl) {
    const icon = streak >= 14 ? '🔥' : streak >= 7 ? '🌟' : streak >= 3 ? '✨' : '💫';
    strEl.textContent = `${streak} дн. ${icon}`;
    strEl.classList.toggle('hot', streak >= 7);
  }

  // XP bar (animate from 0)
  const xpFill  = document.getElementById('petInfoXpFill');
  const xpLabel = document.getElementById('petInfoXpLabel');
  const xpCur   = xpForLevel(level);
  const xpNext  = xpForLevel(level + 1);
  const pct     = xpNext > xpCur ? Math.min(100, Math.round((xp - xpCur) / (xpNext - xpCur) * 100)) : 100;
  if (xpFill)  { xpFill.style.width = '0%'; setTimeout(() => { xpFill.style.width = pct + '%'; }, 350); }
  if (xpLabel) xpLabel.textContent = `${xp} / ${xpNext} XP`;

  // Week dots
  const weekCont = document.getElementById('petInfoWeekDots');
  if (weekCont) {
    weekCont.querySelectorAll('.pet-info-bar__week-dot').forEach((d, i) => {
      setTimeout(() => d.classList.toggle('filled', i < entries), 500 + i * 110);
    });
  }
}

// ── Star canvas for the scene card ──
function initPetMiniCanvas(env, stage) {
  const canvas = document.getElementById('petSceneCanvas');
  if (!canvas) return;

  // Cancel previous RAF if any
  if (_petCanvasRAF) { cancelAnimationFrame(_petCanvasRAF); _petCanvasRAF = null; }

  const ctx = canvas.getContext('2d');
  const card = canvas.parentElement;
  const resize = () => { canvas.width = card.offsetWidth || 360; canvas.height = card.offsetHeight || 240; };
  resize();

  const tints = ['#aaccff','#aaffbb','#88ddff','#ddaaff','#ffe8aa'];
  const tint  = tints[(stage||2)-1] || '#aaccff';
  const count = [80, 120, 180, 240][Math.min(env||0, 3)];

  const stars = Array.from({length: count}, () => ({
    x:     Math.random() * canvas.width,
    y:     Math.random() * canvas.height,
    r:     Math.random() * 1.6 + 0.2,
    base:  Math.random() * 0.55 + 0.18,
    speed: Math.random() * 3 + 1,
    phase: Math.random() * Math.PI * 2,
    tinted: Math.random() < 0.22,
  }));

  // Shooting stars
  const shoots = [];
  let nextShoot = 3 + Math.random() * 8;
  let t0 = null;

  function draw(ts) {
    if (!t0) t0 = ts;
    const t = (ts - t0) / 1000;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    stars.forEach(s => {
      const a = s.base * (0.4 + 0.6 * Math.sin(t / s.speed + s.phase));
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      if (s.tinted) {
        // Parse hex tint to rgba
        const hx = tint.replace('#','');
        const r  = parseInt(hx.slice(0,2),16);
        const g  = parseInt(hx.slice(2,4),16);
        const b  = parseInt(hx.slice(4,6),16);
        ctx.fillStyle = `rgba(${r},${g},${b},${a})`;
      } else {
        ctx.fillStyle = `rgba(255,255,255,${a})`;
      }
      ctx.fill();
    });

    // Shooting stars
    if (t > nextShoot) {
      shoots.push({ x: Math.random()*canvas.width*.7+canvas.width*.1, y: Math.random()*canvas.height*.4,
                    vx: 200+Math.random()*180, vy: 60+Math.random()*80, life:0, maxLife:.6+Math.random()*.4 });
      nextShoot = t + 4 + Math.random()*9;
    }
    for (let i = shoots.length - 1; i >= 0; i--) {
      const s = shoots[i];
      s.x += s.vx / 60; s.y += s.vy / 60; s.life += 1/60;
      if (s.life >= s.maxLife) { shoots.splice(i,1); continue; }
      const p = s.life / s.maxLife;
      const fade = p < .15 ? p/.15 : p > .7 ? 1-(p-.7)/.3 : 1;
      const dx = -s.vx/60 * (50/60) * 60 * fade * .6;
      const dy = -s.vy/60 * (50/60) * 60 * fade * .6;
      const g  = ctx.createLinearGradient(s.x+dx, s.y+dy, s.x, s.y);
      g.addColorStop(0,'transparent');
      g.addColorStop(1,`rgba(255,255,255,${.85*fade})`);
      ctx.beginPath(); ctx.moveTo(s.x+dx,s.y+dy); ctx.lineTo(s.x,s.y);
      ctx.strokeStyle = g; ctx.lineWidth = 1.4*fade; ctx.stroke();
      ctx.beginPath(); ctx.arc(s.x,s.y,1.8*fade,0,Math.PI*2);
      ctx.fillStyle = `rgba(255,255,255,${fade})`; ctx.fill();
    }

    _petCanvasRAF = requestAnimationFrame(draw);
  }
  _petCanvasRAF = requestAnimationFrame(draw);
}

// ── Play animation state ──
function playPetMiniAnimation(anim) {
  const wrap  = document.getElementById('petMiniWrap');
  const zzz   = document.getElementById('petMiniZzz');
  const parts = document.getElementById('petMiniParticles');
  const mood  = document.getElementById('petMiniMood');
  if (!wrap) return;

  // Clear all states
  wrap.classList.remove('pw-eating','pw-celebrating','pw-sleeping','pw-levelup','pw-tap');
  wrap.dataset.anim = anim;
  zzz?.classList.remove('visible');
  if (parts) parts.innerHTML = '';
  mood?.classList.remove('pop');

  switch (anim) {
    case 'eating':
      wrap.classList.add('pw-eating');
      spawnPetCoins(parts);
      showPetMood('😋');
      break;
    case 'celebrating':
      wrap.classList.add('pw-celebrating');
      spawnPetConfetti(parts);
      spawnPetSparks(parts, 22);
      showPetMood('🎉');
      break;
    case 'sleeping':
      wrap.classList.add('pw-sleeping');
      zzz?.classList.add('visible');
      showPetMood('💤', 3000);
      break;
    case 'levelup':
      wrap.classList.add('pw-levelup');
      spawnPetSparks(parts, 36);
      [0,250,500].forEach(d => setTimeout(() => spawnPetRing(parts), d));
      showPetMood('⬆️');
      setTimeout(() => wrap.classList.remove('pw-levelup'), 1200);
      break;
    default: break; // idle — float animation plays automatically via CSS
  }
}

// ── Mood emoji popup ──
function showPetMood(emoji, dur=1600) {
  const el = document.getElementById('petMiniMood');
  if (!el) return;
  void el.offsetWidth;
  el.textContent = emoji;
  el.classList.add('pop');
  setTimeout(() => el.classList.remove('pop'), dur);
}

// ── Idle variety ──
function schedulePetIdleCharm() {
  _petIdleTimer = setTimeout(() => {
    const wrap = document.getElementById('petMiniWrap');
    if (wrap && !['pw-eating','pw-celebrating','pw-sleeping','pw-levelup']
                  .some(c => wrap.classList.contains(c))) {
      if (Math.random() < .5) {
        wrap.classList.add('pw-tap');
        spawnPetHearts(document.getElementById('petMiniParticles'), 3);
        setTimeout(() => wrap.classList.remove('pw-tap'), 520);
      } else {
        showPetMood(['✨','🌟','💫','❤️'][Math.floor(Math.random()*4)], 1400);
      }
    }
    schedulePetIdleCharm();
  }, 8000 + Math.random() * 14000);
}

// ── Particle helpers ──
function spawnPetCoins(container) {
  if (!container) return;
  const colors = ['#ffe566','#ffd000','#c6ff5e','#40d8ff','#ff9f40'];
  for (let i = 0; i < 12; i++) {
    const el = document.createElement('div');
    el.className = 'pw-coin';
    const a = Math.random()*Math.PI*2, d = 50+Math.random()*65;
    const c = colors[i%colors.length];
    const sz = 10+Math.random()*5;
    el.style.cssText = `left:50%;top:40%;width:${sz}px;height:${sz}px;
      background:radial-gradient(circle,${c},#b07000);--c:${c};
      --sx:${Math.cos(a)*d}px;--sy:${Math.sin(a)*d}px;
      --dur:${.5+Math.random()*.5}s;animation-delay:${i*.07}s;`;
    container.appendChild(el);
  }
}

function spawnPetSparks(container, count=20) {
  if (!container) return;
  const colors = ['#ff6b6b','#ffd93d','#6bcb77','#4d96ff','#ff6fe8','#fff','#ffe566'];
  for (let i = 0; i < count; i++) {
    const el = document.createElement('div');
    el.className = 'pw-spark';
    const a = Math.random()*Math.PI*2, d = 55+Math.random()*105;
    const c = colors[Math.floor(Math.random()*colors.length)];
    const sz = 4+Math.random()*6;
    el.style.cssText = `left:50%;top:45%;width:${sz}px;height:${sz}px;--c:${c};
      --dx:${Math.cos(a)*d}px;--dy:${Math.sin(a)*d}px;
      --dur:${.45+Math.random()*.7}s;animation-delay:${i*.03}s;`;
    container.appendChild(el);
  }
}

function spawnPetHearts(container, count=5) {
  if (!container) return;
  const emojis = ['❤️','💚','💙','💜','💛','🩷','✨'];
  for (let i = 0; i < count; i++) {
    const el = document.createElement('div');
    el.className = 'pw-heart';
    const ox = (Math.random()-.5)*80;
    el.textContent = emojis[Math.floor(Math.random()*emojis.length)];
    el.style.cssText = `left:calc(50% + ${ox}px);top:30%;
      --sx:0px;--sy:0px;--tx:${(Math.random()-.5)*50}px;
      --rot:${(Math.random()-.5)*30}deg;--rot2:${(Math.random()-.5)*30}deg;
      --sz:${16+Math.random()*10}px;--dur:${1+Math.random()*.4}s;
      animation-delay:${i*.08}s;`;
    container.appendChild(el);
  }
}

function spawnPetConfetti(container, count=28) {
  if (!container) return;
  const colors = ['#ff6b6b','#ffd93d','#6bcb77','#4d96ff','#ff6fe8','#fff','#ffa040','#aa44ff'];
  for (let i = 0; i < count; i++) {
    const el = document.createElement('div');
    el.className = 'pw-confetti';
    const c = colors[Math.floor(Math.random()*colors.length)];
    const w = 5+Math.random()*8, h = 3+Math.random()*6;
    el.style.cssText = `left:50%;top:40%;width:${w}px;height:${h}px;--c:${c};
      --dx:${(Math.random()-.5)*210}px;--dy:${-40-Math.random()*130}px;
      --spin:${(Math.random()>.5?1:-1)*(180+Math.random()*360)}deg;
      --dur:${.9+Math.random()*.8}s;animation-delay:${i*.04}s;
      border-radius:${Math.random()>.5?'2px':'50%'};`;
    container.appendChild(el);
  }
}

function spawnPetRing(container) {
  if (!container) return;
  const r = document.createElement('div');
  r.className = 'pw-ring';
  container.appendChild(r);
  setTimeout(() => r.remove(), 1000);
}

// ── Page navigation — called from reminders.js on 'pet' tab ──
