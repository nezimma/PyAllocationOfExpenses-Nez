// ─── CONFIG ──────────────────────────────────
// Замените на реальный адрес вашего сервера при деплое
const API_BASE = 'https://pyallocationofexpenses-nez.onrender.com';

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
  // Fallback — никогда не должен появляться при корректном маппинге на бэкенде
  other:         { label: 'Прочее',                emoji: '💰', color: '#AAAAAA' },
};

// Заполняется из API; mock-данные используются как запасной вариант
let EXPENSES = [];

// Курсы валют — base BYN. Формат: { USD: 3.25, EUR: 3.52, RUB: 0.035, ... }
let RATES = {};
const CURRENCY_SYMBOLS = { BYN: 'Br', USD: '$', EUR: '€', RUB: '₽', PLN: 'zł', GBP: '£', CNY: '¥', UAH: '₴' };

async function loadRates() {
  try {
    const resp = await fetch(`${API_BASE}/api/rates`, {
      headers: { 'ngrok-skip-browser-warning': 'true' },
    });
    if (!resp.ok) return;
    const data = await resp.json();
    RATES = data.rates || {};
  } catch (e) {
    console.warn('Не удалось загрузить курсы валют:', e);
  }
}

/**
 * Конвертирует сумму из fromCur в toCur, используя BYN как промежуточную.
 * Если курс недоступен — возвращает исходную сумму без изменений.
 */
function convertAmount(amount, fromCur, toCur) {
  if (!amount || fromCur === toCur) return amount;
  if (fromCur === 'BYN') {
    const rate = RATES[toCur];
    return rate ? amount / rate : amount;
  }
  if (toCur === 'BYN') {
    const rate = RATES[fromCur];
    return rate ? amount * rate : amount;
  }
  const rateFrom = RATES[fromCur];
  const rateTo   = RATES[toCur];
  return (rateFrom && rateTo) ? amount * rateFrom / rateTo : amount;
}

/** Возвращает отображаемую сумму расхода в выбранной валюте. */
function displayAmount(expense) {
  const target = (typeof state !== 'undefined' && state.currency) ? state.currency : 'BYN';
  return convertAmount(expense.amount, expense.currency || 'BYN', target);
}

const MOCK_EXPENSES = [
  { id: 1,  name: 'Сходил в Евроопт',                         cat: 'restaurants',   amount: 22,  currency: 'BYN', date: '2025-03-23T09:15' },
  { id: 2,  name: 'Вызвал Яндекс.Такси до офиса',             cat: 'transport',     amount: 15,  currency: 'BYN', date: '2025-03-23T10:42' },
  { id: 3,  name: 'Посидел в Тьерри, взял кофе и круассан',   cat: 'restaurants',   amount: 18,  currency: 'BYN', date: '2025-03-23T11:05' },
  { id: 4,  name: 'Аренда квартиры',                          cat: 'housing',       amount: 900, currency: 'BYN', date: '2025-03-22T08:00' },
  { id: 5,  name: 'Заказал чайник на OZON',                   cat: 'household',     amount: 80,  currency: 'BYN', date: '2025-03-22T13:30' },
  { id: 6,  name: 'Оплатил курсы по английскому',             cat: 'education',     amount: 460, currency: 'BYN', date: '2025-03-22T15:00' },
  { id: 7,  name: 'Сходил в кино на "Аватар 3"',              cat: 'entertainment', amount: 21,  currency: 'BYN', date: '2025-03-21T19:30' },
  { id: 8,  name: 'Купил умывалку',                           cat: 'health',        amount: 11,  currency: 'BYN', date: '2025-03-21T11:20' },
  { id: 9,  name: 'Прикупил шмот в Mark Formelle',            cat: 'clothes',       amount: 220, currency: 'BYN', date: '2025-03-20T16:00' },
  { id: 10, name: 'Купил микрофон',                           cat: 'electronics',   amount: 140, currency: 'BYN', date: '2025-03-20T14:00' },
  { id: 11, name: 'Взял самокат',                             cat: 'transport',     amount: 8,   currency: 'BYN', date: '2025-03-20T08:30' },
  { id: 12, name: 'Сходил в БК',                              cat: 'restaurants',   amount: 15,  currency: 'BYN', date: '2025-03-19T13:00' },
  { id: 13, name: 'Оплатил Cloude',                           cat: 'education',     amount: 45,  currency: 'BYN', date: '2025-03-19T20:00' },
  { id: 14, name: 'Заказал крем на Wildberries',              cat: 'health',        amount: 14,  currency: 'BYN', date: '2025-03-18T17:30' },
  { id: 15, name: 'Обновил проездной',                        cat: 'transport',     amount: 53,  currency: 'BYN', date: '2025-03-18T09:00' },
  { id: 16, name: 'Купил игру Crimson Desert',                cat: 'entertainment', amount: 210, currency: 'BYN', date: '2025-03-17T21:00' },
  { id: 17, name: 'Зашел в перекресток взять pringles',       cat: 'restaurants',   amount: 9,   currency: 'BYN', date: '2025-03-17T18:00' },
  { id: 18, name: 'Заказал носочки',                          cat: 'clothes',       amount: 32,  currency: 'BYN', date: '2025-03-16T15:00' },
  { id: 19, name: 'Коммуналка',                               cat: 'housing',       amount: 250, currency: 'BYN', date: '2025-03-16T10:00' },
  { id: 20, name: 'Купил губки',                              cat: 'household',     amount: 17,  currency: 'BYN', date: '2025-03-15T12:00' },
  { id: 21, name: 'Сходил в барбершоп',                       cat: 'health',        amount: 50,  currency: 'BYN', date: '2025-03-15T14:00' },
  { id: 22, name: 'Оплатил Spotify',                          cat: 'entertainment', amount: 30,  currency: 'BYN', date: '2025-03-14T00:00' },
  { id: 23, name: 'Приобрел перчатки для быта',               cat: 'household',     amount: 6,   currency: 'BYN', date: '2025-03-13T11:00' },
  { id: 24, name: 'Посидел в Beermania',                      cat: 'restaurants',   amount: 42,  currency: 'BYN', date: '2025-03-12T20:30' },
];

// Регулярные платежи — заполняется из API
let RECURRING = [];

async function loadRecurring(userId) {
  try {
    const resp = await fetch(`${API_BASE}/api/recurring/${userId}`, {
      headers: { 'ngrok-skip-browser-warning': 'true' },
    });
    if (!resp.ok) return [];
    return await resp.json();
  } catch (e) {
    console.warn('Recurring API недоступен:', e);
    return [];
  }
}

// TODO: убрать после защиты — статичный демо-прогноз
let FORECAST = {
  enough_data:    true,
  total_spent:    1547.50,
  forecast_total: 2890,
  daily_avg:      61.40,
  days_elapsed:   10,
  days_in_month:  30,
  method:         "regression",
  r2:             0.88,
  by_category: {
    "Жилье":           900,
    "Рестораны и еда": 680,
    "Транспорт":        420,
    "Быт":             310,
    "Здоровье":        180,
  },
};

async function loadForecast(userId) {
  try {
    const now = new Date();
    const resp = await fetch(
      `${API_BASE}/api/forecast/${userId}?year=${now.getFullYear()}&month=${now.getMonth() + 1}`,
      { headers: { 'ngrok-skip-browser-warning': 'true' } },
    );
    if (!resp.ok) return null;
    return await resp.json();
  } catch (e) {
    console.warn('Forecast API недоступен:', e);
    return null;
  }
}

// Жильё и образование — разовые в месяц, не экстраполируем вперёд
const _FIXED_CATS = new Set(['housing', 'education']);

// Статические веса — fallback пока истории < 2 месяцев
const _BASE_WEIGHTS = {
  restaurants:   1.0,
  transport:     1.0,
  entertainment: 0.9,
  health:        0.9,
  household:     0.8,
  clothes:       0.6,
  electronics:   0.4,
  education:     0.0,
  housing:       0.0,
  other:         0.7,
};

/**
 * Считает динамические веса категорий из истории:
 * вес = (кол-во месяцев с тратой в категории) / (всего уникальных месяцев в истории)
 * Возвращает null если истории меньше 2 месяцев.
 */
function _calcDynamicWeights(excludeYear, excludeMonth) {
  // Берём только прошлые месяцы (не текущий)
  const history = EXPENSES.filter(e => {
    const d = new Date(e.date);
    return !(d.getFullYear() === excludeYear && d.getMonth() + 1 === excludeMonth);
  });
  if (!history.length) return null;

  // Уникальные месяцы в истории
  const monthKeys = new Set(history.map(e => {
    const d = new Date(e.date);
    return `${d.getFullYear()}-${d.getMonth()}`;
  }));
  const totalMonths = monthKeys.size;
  if (totalMonths < 2) return null; // мало истории — используем fallback

  // Для каждой категории — в скольких месяцах встречалась
  const catMonthKeys = {};
  history.forEach(e => {
    const d = new Date(e.date);
    const key = `${e.cat}|${d.getFullYear()}-${d.getMonth()}`;
    catMonthKeys[key] = true;
  });

  const catCounts = {};
  Object.keys(catMonthKeys).forEach(key => {
    const cat = key.split('|')[0];
    catCounts[cat] = (catCounts[cat] || 0) + 1;
  });

  const weights = {};
  Object.entries(catCounts).forEach(([cat, months]) => {
    weights[cat] = Math.min(1.0, months / totalMonths);
  });
  return weights;
}

function buildLocalForecast() {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth() + 1;
  const today = now.getDate();
  const daysInMonth = new Date(year, month, 0).getDate();

  const currentMonthExpenses = EXPENSES.filter(e => {
    const d = new Date(e.date);
    return d.getFullYear() === year && d.getMonth() + 1 === month;
  });
  if (currentMonthExpenses.length < 3) return null;

  const totalSpent = currentMonthExpenses.reduce((s, e) => s + displayAmount(e), 0);
  const remainingDays = Math.max(0, daysInMonth - today);

  // Пробуем динамические веса, иначе — статические
  const dynWeights = _calcDynamicWeights(year, month);
  const getWeight = cat => {
    if (_FIXED_CATS.has(cat)) return 0;
    if (dynWeights) return dynWeights[cat] ?? _BASE_WEIGHTS[cat] ?? 0.5;
    return _BASE_WEIGHTS[cat] ?? 0.5;
  };

  // Прогноз переменных расходов: по каждой категории отдельно с её весом
  const cats = [...new Set(currentMonthExpenses.map(e => e.cat))];
  let forecastVariable = 0;
  let totalVariableAvg = 0;

  cats.forEach(cat => {
    if (_FIXED_CATS.has(cat)) return;
    const catSum = currentMonthExpenses
      .filter(e => e.cat === cat)
      .reduce((s, e) => s + displayAmount(e), 0);
    const catDailyAvg = today > 0 ? catSum / today : 0;
    const weight = getWeight(cat);
    forecastVariable += catDailyAvg * weight * remainingDays;
    totalVariableAvg += catDailyAvg;
  });

  const forecastTotal = totalSpent + forecastVariable;

  return {
    total_spent:    totalSpent,
    forecast_total: forecastTotal,
    daily_avg:      totalVariableAvg,
    days_elapsed:   today,
    days_in_month:  daysInMonth,
    enough_data:    true,
    using_dynamic:  dynWeights !== null,  // для отладки
  };
}

async function loadExpenses() {
  const tg = window.Telegram?.WebApp;
  const userId = tg?.initDataUnsafe?.user?.id;
  if (!userId) {
    EXPENSES = [...MOCK_EXPENSES];
    return;
  }
  // Загружаем расходы, курсы и прогноз параллельно
  await Promise.all([
    (async () => {
      try {
        const resp = await fetch(`${API_BASE}/api/expenses/${userId}`, {
          headers: { 'ngrok-skip-browser-warning': 'true' },
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        EXPENSES = await resp.json();
      } catch (e) {
        console.warn('API недоступен, используем mock-данные:', e);
        EXPENSES = [...MOCK_EXPENSES];
      }
    })(),
    loadRates(),
    (async () => { FORECAST   = await loadForecast(userId); })(),
    (async () => { RECURRING  = await loadRecurring(userId); })(),
  ]);
}

// Chart aggregation helpers — используют displayAmount для конвертации

const _MONTH_LABELS = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'];

function getBarData(expenses, period = 'week') {
  if (period === 'week') {
    const labels = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];
    const sums = new Array(7).fill(0);
    expenses.forEach(e => {
      sums[(new Date(e.date).getDay() + 6) % 7] += displayAmount(e);
    });
    return { labels, data: sums };
  }

  if (period === 'month') {
    // Определяем нужный месяц из данных или из текущей даты
    const ref = expenses.length > 0 ? new Date(expenses[0].date) : new Date();
    const daysInMonth = new Date(ref.getFullYear(), ref.getMonth() + 1, 0).getDate();
    const sums = new Array(daysInMonth).fill(0);
    expenses.forEach(e => {
      sums[new Date(e.date).getDate() - 1] += displayAmount(e);
    });
    return {
      labels: Array.from({ length: daysInMonth }, (_, i) => String(i + 1)),
      data: sums,
    };
  }

  // year → группируем по месяцам
  const sums = new Array(12).fill(0);
  expenses.forEach(e => {
    sums[new Date(e.date).getMonth()] += displayAmount(e);
  });
  return { labels: _MONTH_LABELS, data: sums };
}

function getLineData(expenses, period = 'week') {
  if (period === 'year') {
    // Год → 12 точек по месяцам
    const sums = new Array(12).fill(0);
    expenses.forEach(e => { sums[new Date(e.date).getMonth()] += displayAmount(e); });
    return { labels: _MONTH_LABELS, data: sums };
  }
  // Неделя / месяц → группируем по дате
  const byDate = {};
  expenses.forEach(e => {
    const key = e.date.slice(0, 10);
    byDate[key] = (byDate[key] || 0) + displayAmount(e);
  });
  const sorted = Object.entries(byDate).sort((a, b) => a[0].localeCompare(b[0]));
  return {
    labels: sorted.map(([d]) => period === 'month' ? d.slice(8) : d.slice(5)),
    data: sorted.map(([, v]) => v),
  };
}

function getDoughnutData(expenses) {
  const byCat = {};
  expenses.forEach(e => {
    byCat[e.cat] = (byCat[e.cat] || 0) + displayAmount(e);
  });
  const entries = Object.entries(byCat).sort((a, b) => b[1] - a[1]);
  return {
    labels: entries.map(([k]) => CATEGORIES[k]?.emoji + ' ' + CATEGORIES[k]?.label),
    data: entries.map(([, v]) => v),
    colors: entries.map(([k]) => CATEGORIES[k]?.color || '#888'),
    keys: entries.map(([k]) => k),
  };
}
