/**
 * OmniShield AI — Core App
 * Router, API client, global state, shared utilities.
 */

const OmniShield = (() => {
  'use strict';

  // ── State ────────────────────────────────────────────────────────────────
  const state = {
    currentPage: 'dashboard',
    modelLoaded: false,
    modelVersion: null,
    alertCount: 0,
    chartInstances: {},
    refreshTimer: null,
  };

  // ── API Client ───────────────────────────────────────────────────────────
  const api = {
    async request(method, path, body = null) {
      const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
      };
      if (body !== null) opts.body = JSON.stringify(body);
      try {
        const res = await fetch('/api' + path, opts);
        const json = await res.json();
        return { ok: res.ok, status: res.status, data: json };
      } catch (err) {
        return { ok: false, status: 0, data: { error: { message: 'Network error: ' + err.message } } };
      }
    },
    get: (path) => api.request('GET', path),
    post: (path, body) => api.request('POST', path, body),
    patch: (path, body) => api.request('PATCH', path, body),

    async upload(path, formData) {
      try {
        const res = await fetch('/api' + path, { method: 'POST', body: formData });
        const json = await res.json();
        return { ok: res.ok, status: res.status, data: json };
      } catch (err) {
        return { ok: false, status: 0, data: { error: { message: 'Upload failed: ' + err.message } } };
      }
    },
  };

  // ── Toast ────────────────────────────────────────────────────────────────
  function toast(message, type = 'info', duration = 4000) {
    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    const container = document.getElementById('toast-container');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${message}</span>`;
    container.appendChild(el);
    setTimeout(() => el.remove(), duration);
  }

  // ── Modal ────────────────────────────────────────────────────────────────
  function showModal(titleText, bodyHTML) {
    const container = document.getElementById('modal-container');
    container.innerHTML = `
      <div class="modal-overlay" id="activeModal">
        <div class="modal">
          <div class="modal-header">
            <span class="modal-title">${titleText}</span>
            <button class="modal-close" onclick="OmniShield.closeModal()">✕</button>
          </div>
          <div class="modal-body">${bodyHTML}</div>
        </div>
      </div>`;
    document.getElementById('activeModal').addEventListener('click', (e) => {
      if (e.target.id === 'activeModal') closeModal();
    });
  }

  function closeModal() {
    document.getElementById('modal-container').innerHTML = '';
  }

  // ── Chart helpers ────────────────────────────────────────────────────────
  function destroyChart(id) {
    if (state.chartInstances[id]) {
      state.chartInstances[id].destroy();
      delete state.chartInstances[id];
    }
  }

  function registerChart(id, instance) {
    destroyChart(id);
    state.chartInstances[id] = instance;
  }

  const CHART_DEFAULTS = {
    color: '#8892a4',
    borderColor: 'rgba(255,255,255,0.06)',
    gridColor: 'rgba(255,255,255,0.05)',
    fontFamily: 'Inter, system-ui, sans-serif',
  };

  Chart.defaults.color = CHART_DEFAULTS.color;
  Chart.defaults.borderColor = CHART_DEFAULTS.gridColor;
  Chart.defaults.font.family = CHART_DEFAULTS.fontFamily;

  function makeLineChart(ctx, labels, datasets, id) {
    const instance = new Chart(ctx, {
      type: 'line',
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            labels: {
              color: '#aab4c4',
              font: { size: 12 },
              usePointStyle: true,
              pointStyleWidth: 10,
              padding: 20,
            },
          },
          tooltip: {
            backgroundColor: '#0f1a2e',
            borderColor: 'rgba(0,212,255,0.3)',
            borderWidth: 1,
            titleColor: '#00d4ff',
            bodyColor: '#ccd6e0',
            padding: 12,
            callbacks: {
              label: (ctx) => ` ${ctx.dataset.label}: ${ctx.parsed.y}`,
            },
          },
          datalabels: {
            display: (ctx) => ctx.dataset.data[ctx.dataIndex] > 0,
            color: '#ffffff',
            backgroundColor: (ctx) => ctx.dataset.borderColor,
            borderRadius: 4,
            font: { size: 10, weight: '600' },
            padding: { top: 3, bottom: 3, left: 6, right: 6 },
            anchor: 'end',
            align: 'top',
            offset: 4,
            formatter: (val) => val,
          },
        },
        scales: {
          x: {
            grid: { color: CHART_DEFAULTS.gridColor },
            ticks: { color: '#5a6a7e', font: { size: 11 }, maxRotation: 0 },
          },
          y: {
            grid: { color: CHART_DEFAULTS.gridColor },
            ticks: {
              color: '#5a6a7e',
              precision: 0,
              font: { size: 11 },
              callback: (val) => val,
            },
            beginAtZero: true,
          },
        },
      },
    });
    if (id) registerChart(id, instance);
    return instance;
  }

  function makeDoughnutChart(ctx, labels, data, colors, id) {
    const total = data.reduce((a, b) => a + b, 0);
    const instance = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data,
          backgroundColor: colors,
          borderColor: '#0d1b2e',
          borderWidth: 3,
          hoverOffset: 8,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '65%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              usePointStyle: true,
              color: '#aab4c4',
              font: { size: 12 },
              padding: 16,
              generateLabels: (chart) => {
                const meta = chart.getDatasetMeta(0);
                return chart.data.labels.map((label, i) => {
                  const val = chart.data.datasets[0].data[i];
                  const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                  return {
                    text: `${label}  ${val} (${pct}%)`,
                    fillStyle: chart.data.datasets[0].backgroundColor[i],
                    strokeStyle: 'transparent',
                    pointStyle: 'circle',
                    index: i,
                    hidden: meta.data[i].hidden,
                  };
                });
              },
            },
          },
          tooltip: {
            backgroundColor: '#0f1a2e',
            borderColor: 'rgba(0,212,255,0.3)',
            borderWidth: 1,
            titleColor: '#00d4ff',
            bodyColor: '#ccd6e0',
            padding: 12,
            callbacks: {
              label: (ctx) => {
                const val = ctx.parsed;
                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                return ` ${ctx.label}: ${val} (${pct}%)`;
              },
            },
          },
          datalabels: {
            display: (ctx) => {
              const val = ctx.dataset.data[ctx.dataIndex];
              return total > 0 && (val / total) > 0.05;
            },
            color: '#fff',
            font: { size: 11, weight: '700' },
            formatter: (val) => {
              const pct = total > 0 ? ((val / total) * 100).toFixed(0) : 0;
              return pct + '%';
            },
          },
        },
      },
    });
    if (id) registerChart(id, instance);
    return instance;
  }

  function makeBarChart(ctx, labels, data, label, color, id) {
    const isArray = Array.isArray(color);
    const maxVal = Math.max(...data, 1);
    const instance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label,
          data,
          backgroundColor: isArray ? color : color,
          borderRadius: 6,
          borderSkipped: false,
          maxBarThickness: 48,
          minBarLength: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#0f1a2e',
            borderColor: 'rgba(0,212,255,0.3)',
            borderWidth: 1,
            titleColor: '#00d4ff',
            bodyColor: '#ccd6e0',
            padding: 12,
            callbacks: {
              label: (ctx) => ` Count: ${ctx.parsed.y}`,
            },
          },
          datalabels: {
            anchor: 'end',
            align: 'top',
            color: '#ccd6e0',
            font: { size: 12, weight: '700' },
            formatter: (val) => val,
            offset: 2,
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: '#5a6a7e', font: { size: 11 } },
          },
          y: {
            grid: { color: CHART_DEFAULTS.gridColor },
            ticks: {
              color: '#5a6a7e',
              precision: 0,
              font: { size: 11 },
            },
            beginAtZero: true,
            suggestedMax: maxVal + Math.ceil(maxVal * 0.2) + 1,
          },
        },
      },
    });
    if (id) registerChart(id, instance);
    return instance;
  }

  // ── Utilities ────────────────────────────────────────────────────────────
  function formatDate(isoStr) {
    if (!isoStr) return '—';
    const d = new Date(isoStr);
    return d.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
  }

  function formatRelTime(isoStr) {
    if (!isoStr) return '—';
    const diff = Date.now() - new Date(isoStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return Math.floor(hrs / 24) + 'd ago';
  }

  function badge(type) {
    const cls = type.toLowerCase().replace(/\s+/g, '-');
    const icons = {
      normal: '✅', attack: '🚨', suspicious: '⚠️',
      critical: '🔴', high: '🟠', medium: '🟡', low: '🟢', info: '🔵',
      new: '🔔', acknowledged: '👁️', resolved: '✔️',
    };
    return `<span class="badge badge-${cls}">${icons[cls] || ''} ${type}</span>`;
  }

  function riskColor(score) {
    if (score >= 80) return '#dc2626';
    if (score >= 60) return '#f97316';
    if (score >= 35) return '#f59e0b';
    if (score >= 10) return '#10b981';
    return '#3b82f6';
  }

  function severityToClass(sev) {
    const map = { CRITICAL: 'critical', HIGH: 'high', MEDIUM: 'medium', LOW: 'low', INFO: 'info' };
    return map[(sev || '').toUpperCase()] || 'info';
  }

  function skeleton(lines = 3) {
    return Array.from({ length: lines }, (_, i) =>
      `<div class="skeleton skeleton-text ${i % 3 === 2 ? 'short' : ''}" style="margin-bottom:10px"></div>`
    ).join('');
  }

  function emptyState(icon, title, sub, action = '') {
    return `<div class="empty-state">
      <div class="empty-icon">${icon}</div>
      <div class="empty-title">${title}</div>
      <div class="empty-sub">${sub}</div>
      ${action}
    </div>`;
  }

  function errorState(msg) {
    return `<div class="error-state">
      <div class="error-icon">⚠️</div>
      <div class="error-msg">${msg}</div>
    </div>`;
  }

  // ── Security Score Ring ──────────────────────────────────────────────────
  function drawScoreRing(canvasId, score, color) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const size = canvas.width;
    const cx = size / 2, cy = size / 2, r = size / 2 - 12;
    ctx.clearRect(0, 0, size, size);
    // Track
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = 10;
    ctx.stroke();
    // Fill
    const angle = (score / 100) * Math.PI * 2 - Math.PI / 2;
    ctx.beginPath();
    ctx.arc(cx, cy, r, -Math.PI / 2, angle);
    ctx.strokeStyle = color;
    ctx.lineWidth = 10;
    ctx.lineCap = 'round';
    ctx.stroke();
  }

  // ── Model status update ──────────────────────────────────────────────────
  async function refreshModelStatus() {
    const res = await api.get('/model/info');
    if (res.ok && res.data.data) {
      const info = res.data.data;
      state.modelLoaded = info.loaded;
      state.modelVersion = info.version || null;

      const dot = document.getElementById('modelStatusDot');
      const text = document.getElementById('modelStatusText');
      const ver = document.getElementById('modelVersionText');
      if (dot) dot.classList.toggle('active', info.loaded);
      if (text) text.textContent = info.loaded ? (info.model_name || 'RF Model') : 'No model loaded';
      if (ver) ver.textContent = info.loaded ? ('v' + info.version) : '—';
    }
  }

  // ── Alert count ──────────────────────────────────────────────────────────
  async function refreshAlertCount() {
    const res = await api.get('/alerts?per_page=1');
    if (res.ok && res.data.data) {
      const count = res.data.data.unread_count || 0;
      state.alertCount = count;
      const badgeEl = document.getElementById('alert-count-badge');
      const dot = document.getElementById('headerAlertDot');
      if (badgeEl) { badgeEl.textContent = count; badgeEl.classList.toggle('hidden', count === 0); }
      if (dot) dot.classList.toggle('visible', count > 0);
    }
  }

  // ── Live clock in header ─────────────────────────────────────────────────
  function startLiveClock() {
    const el = document.getElementById('liveClock');
    if (!el) return;
    function tick() {
      el.textContent = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
    tick();
    setInterval(tick, 1000);
  }

  // ── Router ───────────────────────────────────────────────────────────────
  const pages = {};

  function registerPage(name, renderer) {
    pages[name] = renderer;
  }

  function navigate(page) {
    if (!pages[page]) { toast('Page not found: ' + page, 'error'); return; }
    state.currentPage = page;

    // Cancel any existing refresh timer
    if (state.refreshTimer) { clearInterval(state.refreshTimer); state.refreshTimer = null; }

    // Update nav active state
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    const navEl = document.getElementById('nav-' + page);
    if (navEl) navEl.classList.add('active');

    // Update header title
    const titles = {
      dashboard: 'Dashboard', analyze: 'Analyze Activity', history: 'Activity History',
      alerts: 'Alerts', analytics: 'Analytics', datasets: 'Datasets',
      models: 'ML Models', reports: 'Reports',
    };
    const titleEl = document.getElementById('pageTitle');
    if (titleEl) titleEl.textContent = titles[page] || page;

    // Close mobile sidebar
    closeSidebar();

    // Destroy all charts
    Object.values(state.chartInstances).forEach(c => { try { c.destroy(); } catch {} });
    state.chartInstances = {};

    // Render page
    const content = document.getElementById('pageContent');
    content.innerHTML = `<div style="padding:60px;text-align:center"><div class="spinner"></div></div>`;
    pages[page](content);
  }

  // ── Mobile sidebar ───────────────────────────────────────────────────────
  function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    sidebar.classList.toggle('open');
    overlay.classList.toggle('visible');
  }
  function closeSidebar() {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('sidebarOverlay').classList.remove('visible');
  }

  // ── Init ─────────────────────────────────────────────────────────────────
  function init() {
    // Sidebar nav
    document.querySelectorAll('.nav-item[data-page]').forEach(el => {
      el.addEventListener('click', () => navigate(el.dataset.page));
    });

    // Hamburger
    document.getElementById('hamburgerBtn').addEventListener('click', toggleSidebar);
    document.getElementById('sidebarOverlay').addEventListener('click', closeSidebar);

    // Header alert btn
    document.getElementById('headerAlertBtn').addEventListener('click', () => navigate('alerts'));

    // Initial load
    refreshModelStatus();
    refreshAlertCount();
    startLiveClock();
    setInterval(refreshAlertCount, 30000);
    setInterval(refreshModelStatus, 60000);

    // Navigate to dashboard
    navigate('dashboard');
  }

  document.addEventListener('DOMContentLoaded', init);

  // Public API
  return {
    api,
    toast,
    showModal,
    closeModal,
    registerPage,
    navigate,
    state,
    badge,
    riskColor,
    formatDate,
    formatRelTime,
    skeleton,
    emptyState,
    errorState,
    makeLineChart,
    makeDoughnutChart,
    makeBarChart,
    drawScoreRing,
    registerChart,
    destroyChart,
    severityToClass,
    refreshModelStatus,
    refreshAlertCount,
  };
})();


