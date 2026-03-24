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

const EXPENSES = [
  { id: 1,  name: 'Пятёрочка',          cat: 'restaurants',   amount: 1240, date: '2025-03-23T09:15' },
  { id: 2,  name: 'Яндекс.Такси',       cat: 'transport',     amount: 380,  date: '2025-03-23T10:42' },
  { id: 3,  name: 'Кофе и круассан',    cat: 'restaurants',   amount: 320,  date: '2025-03-23T11:05' },
  { id: 4,  name: 'Аренда квартиры',    cat: 'housing',       amount: 28000,date: '2025-03-22T08:00' },
  { id: 5,  name: 'OZON — чайник',      cat: 'household',     amount: 2890, date: '2025-03-22T13:30' },
  { id: 6,  name: 'Supabase PRO',       cat: 'education',     amount: 1500, date: '2025-03-22T15:00' },
  { id: 7,  name: 'Кино «Аквамен»',    cat: 'entertainment', amount: 490,  date: '2025-03-21T19:30' },
  { id: 8,  name: 'Аптека Rigla',       cat: 'health',        amount: 760,  date: '2025-03-21T11:20' },
  { id: 9,  name: 'H&M — джинсы',      cat: 'clothes',       amount: 3200, date: '2025-03-20T16:00' },
  { id: 10, name: 'Наушники Sony',      cat: 'electronics',   amount: 5990, date: '2025-03-20T14:00' },
  { id: 11, name: 'Самокат',            cat: 'transport',     amount: 650,  date: '2025-03-20T08:30' },
  { id: 12, name: 'Бургер Кинг',        cat: 'restaurants',   amount: 545,  date: '2025-03-19T13:00' },
  { id: 13, name: 'Udemy курс Python',  cat: 'education',     amount: 990,  date: '2025-03-19T20:00' },
  { id: 14, name: 'Wildberries — крем', cat: 'health',        amount: 420,  date: '2025-03-18T17:30' },
  { id: 15, name: 'Метро (проездной)', cat: 'transport',     amount: 1800, date: '2025-03-18T09:00' },
  { id: 16, name: 'Steam — игра',       cat: 'entertainment', amount: 890,  date: '2025-03-17T21:00' },
  { id: 17, name: 'Перекрёсток',        cat: 'restaurants',   amount: 2100, date: '2025-03-17T18:00' },
  { id: 18, name: 'Zara — куртка',      cat: 'clothes',       amount: 4500, date: '2025-03-16T15:00' },
  { id: 19, name: 'Коммуналка',         cat: 'housing',       amount: 4800, date: '2025-03-16T10:00' },
  { id: 20, name: 'Швабра + тряпки',    cat: 'household',     amount: 680,  date: '2025-03-15T12:00' },
  { id: 21, name: 'Маникюр',            cat: 'health',        amount: 1500, date: '2025-03-15T14:00' },
  { id: 22, name: 'Яндекс Музыка',      cat: 'entertainment', amount: 169,  date: '2025-03-14T00:00' },
  { id: 23, name: 'Кухонный комбайн',   cat: 'household',     amount: 7200, date: '2025-03-13T11:00' },
  { id: 24, name: 'Ресторан «Золото»',  cat: 'restaurants',   amount: 3400, date: '2025-03-12T20:30' },
];

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
