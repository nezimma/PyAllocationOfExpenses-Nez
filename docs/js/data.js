// ─── CONFIG ──────────────────────────────────
// Замените на реальный адрес вашего сервера при деплое
const API_BASE = 'http://localhost:8080';

// ─── MOCK DATA ───────────────────────────────
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

// Заполняется из API; mock-данные используются как запасной вариант
let EXPENSES = [];

const MOCK_EXPENSES = [
  { id: 1,  name: 'Сходил в Евроопт',                         cat: 'restaurants',   amount: 22, date: '2025-03-23T09:15' },
  { id: 2,  name: 'Вызвал Яндекс.Такси до офиса',             cat: 'transport',     amount: 15,  date: '2025-03-23T10:42' },
  { id: 3,  name: 'Посидел в Тьерри, взял кофе и круассан',   cat: 'restaurants',   amount: 18,  date: '2025-03-23T11:05' },
  { id: 4,  name: 'Аренда квартиры',                          cat: 'housing',       amount: 900,date: '2025-03-22T08:00' },
  { id: 5,  name: 'Заказал чайник на OZON',                   cat: 'household',     amount: 80, date: '2025-03-22T13:30' },
  { id: 6,  name: 'Оплатил курсы по английскому',             cat: 'education',     amount: 460, date: '2025-03-22T15:00' },
  { id: 7,  name: 'Сходил в кино на "Аватар 3"',              cat: 'entertainment', amount: 21,  date: '2025-03-21T19:30' },
  { id: 8,  name: 'Купил умывалку',                           cat: 'health',        amount: 11,  date: '2025-03-21T11:20' },
  { id: 9,  name: 'Прикупил шмот в Mark Formelle',            cat: 'clothes',       amount: 220, date: '2025-03-20T16:00' },
  { id: 10, name: 'Купил микрофон',                           cat: 'electronics',   amount: 140, date: '2025-03-20T14:00' },
  { id: 11, name: 'Взял самокат',                             cat: 'transport',     amount: 8,  date: '2025-03-20T08:30' },
  { id: 12, name: 'Сходил в БК',                              cat: 'restaurants',   amount: 15,  date: '2025-03-19T13:00' },
  { id: 13, name: 'Оплатил Cloude',                           cat: 'education',     amount: 45,  date: '2025-03-19T20:00' },
  { id: 14, name: 'Заказал крем на Wildberries',              cat: 'health',        amount: 14,  date: '2025-03-18T17:30' },
  { id: 15, name: 'Обновил проездной',                        cat: 'transport',     amount: 53, date: '2025-03-18T09:00' },
  { id: 16, name: 'Купил игру Crimson Desert',                cat: 'entertainment', amount: 210,  date: '2025-03-17T21:00' },
  { id: 17, name: 'Зашел в перекресток взять pringles',       cat: 'restaurants',   amount: 9, date: '2025-03-17T18:00' },
  { id: 18, name: 'Заказал носочки',                          cat: 'clothes',       amount: 32, date: '2025-03-16T15:00' },
  { id: 19, name: 'Коммуналка',                               cat: 'housing',       amount: 250, date: '2025-03-16T10:00' },
  { id: 20, name: 'Купил губки',                              cat: 'household',     amount: 17,  date: '2025-03-15T12:00' },
  { id: 21, name: 'Сходил в барбершоп',                       cat: 'health',        amount: 50, date: '2025-03-15T14:00' },
  { id: 22, name: 'Оплатил Spotify',                          cat: 'entertainment', amount: 30,  date: '2025-03-14T00:00' },
  { id: 23, name: 'Приобрел перчатки для быта',               cat: 'household',     amount: 6, date: '2025-03-13T11:00' },
  { id: 24, name: 'Посидел в Beermania',                      cat: 'restaurants',   amount: 42, date: '2025-03-12T20:30' },
];

async function loadExpenses() {
  const tg = window.Telegram?.WebApp;
  const userId = tg?.initDataUnsafe?.user?.id;
  if (!userId) {
    // Запуск вне Telegram — показываем mock
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

// Chart aggregation helpers
function getBarData(expenses) {
  // Group by day of week
  const days = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];
  const sums = new Array(7).fill(0);
  expenses.forEach(e => {
    const d = new Date(e.date);
    const dow = (d.getDay() + 6) % 7;
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
    data: sorted.map(([, v]) => v)
  };
}

function getDoughnutData(expenses) {
  const byCat = {};
  expenses.forEach(e => {
    byCat[e.cat] = (byCat[e.cat] || 0) + e.amount;
  });
  const entries = Object.entries(byCat).sort((a, b) => b[1] - a[1]);
  return {
    labels: entries.map(([k]) => CATEGORIES[k]?.emoji + ' ' + CATEGORIES[k]?.label),
    data: entries.map(([, v]) => v),
    colors: entries.map(([k]) => CATEGORIES[k]?.color || '#888'),
    keys: entries.map(([k]) => k),
  };
}
