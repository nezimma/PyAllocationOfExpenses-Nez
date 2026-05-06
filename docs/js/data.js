// ─── CONFIG ──────────────────────────────────
const API_BASE = 'http://localhost:8080';

// ─── CATEGORIES ──────────────────────────────
const CATEGORIES = {
  restaurants:   { label: 'Рестораны и еда',      emoji: '🍽', color: '#FF6B6B' },
  transport:     { label: 'Транспорт',             emoji: '🚗', color: '#4ECDC4' },
  housing:       { label: 'Жильё',                 emoji: '🏠', color: '#45B7D1' },
  household:     { label: 'Бытовые товары',        emoji: '🧹', color: '#96CEB4' },
  clothes:       { label: 'Одежда и мода',         emoji: '👗', color: '#FFEAA7' },
  electronics:   { label: 'Техника и электроника', emoji: '💻', color: '#DDA0DD' },
  education:     { label: 'Образование',           emoji: '📚', color: '#98D8C8' },
  entertainment: { label: 'Развлечения',           emoji: '🎮', color: '#F7DC6F' },
  health:        { label: 'Красота и здоровье',    emoji: '💊', color: '#F1948A' },
};

// Fills from API; mock used as fallback
let EXPENSES = [];

// Generates an ISO datetime string N days ago at a given hour
function _daysAgo(days, hour = 12) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  d.setHours(hour, 0, 0, 0);
  return d.toISOString().slice(0, 16);
}

const MOCK_EXPENSES = [
  { id: 1,  name: 'Сходил в Евроопт',                         cat: 'restaurants',   amount: 22,  date: _daysAgo(0, 9)  },
  { id: 2,  name: 'Вызвал Яндекс.Такси до офиса',             cat: 'transport',     amount: 15,  date: _daysAgo(0, 10) },
  { id: 3,  name: 'Посидел в Тьерри, взял кофе и круассан',   cat: 'restaurants',   amount: 18,  date: _daysAgo(0, 11) },
  { id: 4,  name: 'Аренда квартиры',                          cat: 'housing',       amount: 900, date: _daysAgo(1, 8)  },
  { id: 5,  name: 'Заказал чайник на OZON',                   cat: 'household',     amount: 80,  date: _daysAgo(1, 13) },
  { id: 6,  name: 'Оплатил курсы по английскому',             cat: 'education',     amount: 460, date: _daysAgo(1, 15) },
  { id: 7,  name: 'Сходил в кино на "Аватар 3"',              cat: 'entertainment', amount: 21,  date: _daysAgo(2, 19) },
  { id: 8,  name: 'Купил умывалку',                           cat: 'health',        amount: 11,  date: _daysAgo(2, 11) },
  { id: 9,  name: 'Прикупил шмот в Mark Formelle',            cat: 'clothes',       amount: 220, date: _daysAgo(3, 16) },
  { id: 10, name: 'Купил микрофон',                           cat: 'electronics',   amount: 140, date: _daysAgo(3, 14) },
  { id: 11, name: 'Взял самокат',                             cat: 'transport',     amount: 8,   date: _daysAgo(4, 8)  },
  { id: 12, name: 'Сходил в БК',                              cat: 'restaurants',   amount: 15,  date: _daysAgo(5, 13) },
  { id: 13, name: 'Оплатил Claude',                           cat: 'education',     amount: 45,  date: _daysAgo(5, 20) },
  { id: 14, name: 'Заказал крем на Wildberries',              cat: 'health',        amount: 14,  date: _daysAgo(8, 17) },
  { id: 15, name: 'Обновил проездной',                        cat: 'transport',     amount: 53,  date: _daysAgo(8, 9)  },
  { id: 16, name: 'Купил игру Crimson Desert',                cat: 'entertainment', amount: 210, date: _daysAgo(10, 21)},
  { id: 17, name: 'Зашел в перекресток взять pringles',       cat: 'restaurants',   amount: 9,   date: _daysAgo(10, 18)},
  { id: 18, name: 'Заказал носочки',                          cat: 'clothes',       amount: 32,  date: _daysAgo(14, 15)},
  { id: 19, name: 'Коммуналка',                               cat: 'housing',       amount: 250, date: _daysAgo(14, 10)},
  { id: 20, name: 'Купил губки',                              cat: 'household',     amount: 17,  date: _daysAgo(17, 12)},
  { id: 21, name: 'Сходил в барбершоп',                       cat: 'health',        amount: 50,  date: _daysAgo(20, 14)},
  { id: 22, name: 'Оплатил Spotify',                          cat: 'entertainment', amount: 30,  date: _daysAgo(22, 0) },
  { id: 23, name: 'Приобрел перчатки для быта',               cat: 'household',     amount: 6,   date: _daysAgo(25, 11)},
  { id: 24, name: 'Посидел в Beermania',                      cat: 'restaurants',   amount: 42,  date: _daysAgo(29, 20)},
];

async function loadExpenses() {
  const tg = window.Telegram?.WebApp;
  const userId = tg?.initDataUnsafe?.user?.id;
  if (!userId) {
    EXPENSES = [...MOCK_EXPENSES];
    return;
  }
  try {
    const resp = await fetch(`${API_BASE}/api/expenses/${userId}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    EXPENSES = await resp.json();
  } catch (e) {
    console.warn('API недоступен, используем mock-данные:', e);
    EXPENSES = [...MOCK_EXPENSES];
  }
}

// ─── CHART AGGREGATION HELPERS ────────────────

function getBarData(expenses, period = 'week') {
  if (period === 'year') {
    const months = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'];
    const sums = new Array(12).fill(0);
    expenses.forEach(e => { sums[new Date(e.date).getMonth()] += e.amount; });
    return { labels: months, data: sums };
  }

  if (period === 'month') {
    const now = new Date();
    const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
    const sums = new Array(daysInMonth).fill(0);
    const labels = Array.from({ length: daysInMonth }, (_, i) => String(i + 1));
    expenses.forEach(e => {
      const day = new Date(e.date).getDate() - 1;
      if (day >= 0 && day < daysInMonth) sums[day] += e.amount;
    });
    return { labels, data: sums };
  }

  // week: group by day of week Mon–Sun
  const days = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];
  const sums = new Array(7).fill(0);
  expenses.forEach(e => {
    const dow = (new Date(e.date).getDay() + 6) % 7;
    sums[dow] += e.amount;
  });
  return { labels: days, data: sums };
}

function getLineData(expenses) {
  const byDate = {};
  expenses.forEach(e => {
    const key = e.date.slice(0, 10);
    byDate[key] = (byDate[key] || 0) + e.amount;
  });
  const sorted = Object.entries(byDate).sort((a, b) => a[0].localeCompare(b[0]));
  return {
    labels: sorted.map(([d]) => d.slice(5)),
    data: sorted.map(([, v]) => v),
  };
}

function getDoughnutData(expenses) {
  const byCat = {};
  expenses.forEach(e => { byCat[e.cat] = (byCat[e.cat] || 0) + e.amount; });
  const entries = Object.entries(byCat).sort((a, b) => b[1] - a[1]);
  return {
    labels: entries.map(([k]) => CATEGORIES[k]?.emoji + ' ' + CATEGORIES[k]?.label),
    data:   entries.map(([, v]) => v),
    colors: entries.map(([k]) => CATEGORIES[k]?.color || '#888'),
    keys:   entries.map(([k]) => k),
  };
}
