/* ── Theme ─────────────────────────────────────────── */
function initTheme() {
  const saved = localStorage.getItem('ss-theme') || 'dark';
  applyTheme(saved);
}
function applyTheme(mode) {
  document.body.classList.toggle('light', mode === 'light');
  localStorage.setItem('ss-theme', mode);
  const icon = document.getElementById('themeIcon');
  if (icon) icon.textContent = mode === 'light' ? '🌙' : '☀️';
}
function toggleTheme() {
  applyTheme(document.body.classList.contains('light') ? 'dark' : 'light');
}

/* ── Char Counter ───────────────────────────────────── */
function updateCounter() {
  const ta = document.getElementById('emailInput');
  const el = document.getElementById('charCount');
  if (!ta || !el) return;
  const words = ta.value.trim() ? ta.value.trim().split(/\s+/).length : 0;
  el.textContent = `${ta.value.length} chars · ${words} words`;
}

/* ── Sample Fill ────────────────────────────────────── */
function fillSample(txt) {
  const ta = document.getElementById('emailInput');
  if (!ta) return;
  ta.value = txt;
  updateCounter();
  ta.focus();
  showToast('📋 Sample loaded');
}

/* ── Clear ──────────────────────────────────────────── */
function clearInput() {
  const ta = document.getElementById('emailInput');
  if (ta) { ta.value = ''; updateCounter(); ta.focus(); }
}

/* ── Submit Loader ──────────────────────────────────── */
function handleSubmit(btn) {
  const t = btn.querySelector('.btn-text');
  const s = btn.querySelector('.spin');
  if (t) t.textContent = 'Analysing…';
  if (s) s.style.display = 'inline-block';
  btn.disabled = true;
}

/* ── Copy Email ─────────────────────────────────────── */
function copyEmail() {
  const body = document.getElementById('epBody');
  if (!body) return;
  navigator.clipboard.writeText(body.textContent.trim())
    .then(() => showToast('📋 Email content copied!'));
}

/* ── Copy Result ────────────────────────────────────── */
function copyResult() {
  const lbl  = document.getElementById('resultLabel');
  const prob = document.querySelector('.prob-pct');
  if (!lbl) return;
  navigator.clipboard.writeText(
    `Verdict: ${lbl.textContent.trim()} | Confidence: ${prob ? prob.textContent : ''}`
  ).then(() => showToast('📋 Result copied!'));
}

/* ── Animate Probability Bar ────────────────────────── */
function animateProbBar() {
  const bar = document.getElementById('probBar');
  if (!bar) return;
  const target = parseFloat(bar.dataset.v || 0);
  setTimeout(() => { bar.style.width = target + '%'; }, 150);
}

/* ── Animate Metric Counters ────────────────────────── */
function animateCounters() {
  document.querySelectorAll('[data-v]').forEach(el => {
    if (el.id === 'probBar') return;
    const target = parseFloat(el.dataset.v);
    if (isNaN(target)) return;
    let cur = 0;
    const step = target / 40;
    const tid = setInterval(() => {
      cur = Math.min(cur + step, target);
      el.textContent = cur.toFixed(1) + '%';
      if (cur >= target) clearInterval(tid);
    }, 18);
  });
}

/* ── Chart.js Doughnut ──────────────────────────────── */
function drawPieChart(spam, ham) {
  const ctx = document.getElementById('pieChart');
  if (!ctx || typeof Chart === 'undefined') return;
  const isLight = document.body.classList.contains('light');
  const textColor = isLight ? '#334155' : '#8aa8c8';
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Spam', 'Legitimate'],
      datasets: [{
        data: [spam, ham],
        backgroundColor: ['rgba(220,38,38,0.85)', 'rgba(0,232,122,0.8)'],
        borderColor:     ['rgba(220,38,38,1)',    'rgba(0,232,122,1)'],
        borderWidth: 2, hoverOffset: 8,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, cutout: '65%',
      plugins: {
        legend: { position: 'bottom', labels: { color: textColor, font: { family: 'Rajdhani', size: 13, weight: '700' }, padding: 16, usePointStyle: true } },
        tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.parsed} (${Math.round(ctx.parsed/(spam+ham)*100)}%)` } }
      }
    }
  });
}

/* ── Admin Filter ───────────────────────────────────── */
function filterTable() {
  const q = (document.getElementById('searchInput')?.value || '').toLowerCase();
  const activeF = document.querySelector('.fbtn.active-f')?.dataset.filter || 'all';
  document.querySelectorAll('.htable tbody tr').forEach(row => {
    const matchQ = !q || row.textContent.toLowerCase().includes(q);
    const matchF = activeF === 'all' || row.dataset.result === activeF;
    row.style.display = (matchQ && matchF) ? '' : 'none';
  });
}
function setFilter(btn, filter) {
  document.querySelectorAll('.fbtn').forEach(b => { b.classList.remove('fa','fs','fh','active-f'); });
  btn.classList.add('active-f');
  if (filter==='all')  btn.classList.add('fa');
  if (filter==='spam') btn.classList.add('fs');
  if (filter==='ham')  btn.classList.add('fh');
  btn.dataset.filter = filter;
  filterTable();
}

/* ── Toast ──────────────────────────────────────────── */
function showToast(msg, ms = 2600) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.querySelector('.tmsg').textContent = msg;
  t.classList.add('show');
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.remove('show'), ms);
}

/* ── Init ───────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  updateCounter();
  animateCounters();
  animateProbBar();
  const firstF = document.querySelector('.fbtn');
  if (firstF && !firstF.classList.contains('active-f')) {
    firstF.classList.add('fa', 'active-f');
    firstF.dataset.filter = 'all';
  }
});

/* ── Spam Score Meter Needle ────────────────────────── */
function animateMeterNeedle() {
  const needle = document.getElementById('smNeedle');
  if (!needle) return;
  const val = parseFloat(needle.dataset.v || 0);
  // Map 0–100% value to left% position across the bar
  setTimeout(() => { needle.style.left = val + '%'; }, 200);
}

document.addEventListener('DOMContentLoaded', () => {
  animateMeterNeedle();
});