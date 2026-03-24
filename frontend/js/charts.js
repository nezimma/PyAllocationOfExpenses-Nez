// ─── CHARTS ──────────────────────────────────
let mainChart = null;
let currentChartType = 'bar';

function getChartColors() {
  const isDark = document.documentElement.dataset.theme === 'dark';
  return {
    grid:    isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)',
    text:    isDark ? 'rgba(240,239,248,0.45)' : 'rgba(24,22,46,0.5)',
    accent:  '#7C6FF7',
  };
}

function buildBarChart(expenses) {
  const { labels, data } = getBarData(expenses);
  const c = getChartColors();
  return {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: data.map((v, i) =>
          i === data.indexOf(Math.max(...data)) ? '#7C6FF7' : 'rgba(124,111,247,0.25)'
        ),
        borderRadius: 8,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { display: false }, tooltip: tooltipConfig() },
      scales: {
        x: { grid: { color: c.grid }, ticks: { color: c.text, font: { family: 'Manrope', size: 11 } } },
        y: { grid: { color: c.grid }, ticks: { color: c.text, font: { family: 'Manrope', size: 11 }, callback: v => formatK(v) }, border: { display: false } }
      }
    }
  };
}

function buildLineChart(expenses) {
  const { labels, data } = getLineData(expenses);
  const c = getChartColors();
  return {
    type: 'line',
    data: {
      labels,
      datasets: [{
        data,
        borderColor: '#7C6FF7',
        backgroundColor: 'rgba(124,111,247,0.10)',
        borderWidth: 2.5,
        fill: true,
        tension: 0.4,
        pointBackgroundColor: '#7C6FF7',
        pointRadius: 4,
        pointHoverRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { display: false }, tooltip: tooltipConfig() },
      scales: {
        x: { grid: { color: c.grid }, ticks: { color: c.text, font: { family: 'Manrope', size: 11 } } },
        y: { grid: { color: c.grid }, ticks: { color: c.text, font: { family: 'Manrope', size: 11 }, callback: v => formatK(v) }, border: { display: false } }
      }
    }
  };
}

function buildDoughnutChart(expenses) {
  const { labels, data, colors } = getDoughnutData(expenses);
  return {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors,
        borderWidth: 0,
        hoverOffset: 8,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: '68%',
      plugins: {
        legend: { display: false },
        tooltip: tooltipConfig(),
      }
    }
  };
}

function tooltipConfig() {
  const isDark = document.documentElement.dataset.theme === 'dark';
  return {
    backgroundColor: isDark ? '#1E1E2A' : '#fff',
    titleColor: isDark ? '#F0EFF8' : '#18162E',
    bodyColor: isDark ? 'rgba(240,239,248,0.7)' : 'rgba(24,22,46,0.6)',
    borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
    borderWidth: 1,
    padding: 10,
    cornerRadius: 10,
    titleFont: { family: 'Unbounded', size: 12 },
    bodyFont: { family: 'Manrope', size: 12 },
    callbacks: {
      label: ctx => ' ' + ctx.formattedValue.replace(/,/g, ' ') + ' ₽'
    }
  };
}

function formatK(v) {
  if (v >= 1000) return (v / 1000).toFixed(0) + 'к';
  return v;
}

function renderChart(type, expenses) {
  currentChartType = type;
  const canvas = document.getElementById('mainChart');
  const ctx = canvas.getContext('2d');
  if (mainChart) { mainChart.destroy(); mainChart = null; }

  let cfg;
  if (type === 'bar')      cfg = buildBarChart(expenses);
  else if (type === 'line') cfg = buildLineChart(expenses);
  else                      cfg = buildDoughnutChart(expenses);

  mainChart = new Chart(ctx, cfg);
  renderLegend(type, expenses);
}

function renderLegend(type, expenses) {
  const el = document.getElementById('chartLegend');
  if (type !== 'doughnut') { el.innerHTML = ''; return; }
  const { labels, colors, data } = getDoughnutData(expenses);
  const total = data.reduce((a, b) => a + b, 0);
  el.innerHTML = labels.map((lbl, i) => `
    <div class="legend-item">
      <span class="legend-dot" style="background:${colors[i]}"></span>
      <span>${lbl}</span>
      <span style="opacity:.5;font-size:10px">${Math.round(data[i] / total * 100)}%</span>
    </div>
  `).join('');
}
