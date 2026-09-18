/**
 * OmniShield AI — Dashboard Page (Real-time)
 */
let _dashboardRefreshInterval = null;

OmniShield.registerPage('dashboard', async (container) => {
  container.innerHTML = dashboardSkeleton();
  await loadDashboardData(container);

  // Real-time refresh every 15 seconds
  _dashboardRefreshInterval = setInterval(async () => {
    if (OmniShield.state.currentPage !== 'dashboard') {
      clearInterval(_dashboardRefreshInterval);
      return;
    }
    // Only refresh stats and table, not full re-render
    await softRefreshDashboard();
  }, 15000);
});

function dashboardSkeleton() {
  return `<div class="stats-grid mb-24">
    ${Array.from({length:5}, () => `<div class="stat-card"><div class="skeleton skeleton-text short mb-8"></div><div class="skeleton skeleton-value"></div></div>`).join('')}
  </div>
  <div class="grid-2 mb-24">
    <div class="card"><div class="card-body"><div class="skeleton skeleton-chart"></div></div></div>
    <div class="card"><div class="card-body"><div class="skeleton skeleton-chart"></div></div></div>
  </div>`;
}

async function loadDashboardData(container) {
  const res = await OmniShield.api.get('/dashboard');
  if (!res.ok) {
    container.innerHTML = OmniShield.errorState('Failed to load dashboard: ' + (res.data?.error?.message || 'Unknown error'));
    return;
  }

  const d = res.data.data;
  if (!d.has_data) {
    renderEmptyDashboard(container, d);
  } else {
    renderDashboard(container, d);
  }
}

async function softRefreshDashboard() {
  const res = await OmniShield.api.get('/dashboard');
  if (!res.ok) return;
  const d = res.data.data;
  if (!d.has_data) return;

  // Update stat cards
  const updates = {
    'live-total': d.total_activities.toLocaleString(),
    'live-normal': d.normal_count.toLocaleString(),
    'live-suspicious': d.suspicious_count.toLocaleString(),
    'live-attacks': d.attack_count.toLocaleString(),
    'live-attack-rate': d.attack_percentage + '%',
  };
  Object.entries(updates).forEach(([id, val]) => {
    const el = document.getElementById(id);
    if (el && el.textContent !== val) {
      el.textContent = val;
      el.classList.add('stat-flash');
      setTimeout(() => el.classList.remove('stat-flash'), 600);
    }
  });

  // Update last-refreshed indicator
  const ts = document.getElementById('dashRefreshTime');
  if (ts) ts.textContent = 'Updated ' + OmniShield.formatRelTime(new Date().toISOString());

  // Refresh activity table
  const actList = document.getElementById('recentActivityList');
  if (actList && d.recent_activities.length > 0) {
    actList.innerHTML = buildActivityTable(d.recent_activities);
  }
}

function renderEmptyDashboard(container, d) {
  container.innerHTML = `
    <div class="stats-grid mb-24">
      ${statCard('Total Activities', 0, 'default', '📊', 'live-total')}
      ${statCard('Normal', 0, 'normal', '✅', 'live-normal')}
      ${statCard('Suspicious', 0, 'suspicious', '⚠️', 'live-suspicious')}
      ${statCard('Attacks', 0, 'attack', '🚨', 'live-attacks')}
      ${statCard('Attack Rate', '0%', 'default', '⚡', 'live-attack-rate')}
    </div>
    ${OmniShield.emptyState('🛡️',
      'No network activity analyzed yet.',
      'Start by uploading a dataset and training a model, then analyze your first network activity.',
      `<button class="btn btn-primary mt-16" onclick="OmniShield.navigate('datasets')">🗄️ Upload Dataset</button>
       <button class="btn btn-secondary mt-16" style="margin-left:8px" onclick="OmniShield.navigate('analyze')">🔍 Analyze Activity</button>`
    )}`;

  if (d.current_model?.loaded) {
    container.insertAdjacentHTML('beforeend', modelInfoBanner(d.current_model));
  }
}

function renderDashboard(container, d) {
  const threatClass = {LOW:'low',MEDIUM:'medium',HIGH:'high',CRITICAL:'critical'}[d.threat_level] || 'low';
  const now = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  container.innerHTML = `
    <!-- Live refresh indicator -->
    <div style="display:flex; justify-content:flex-end; align-items:center; gap:10px; margin-bottom:12px;">
      <span class="live-dot-indicator"></span>
      <span class="text-muted" style="font-size:12px" id="dashRefreshTime">Live • ${now}</span>
    </div>

    <!-- Stats row -->
    <div class="stats-grid mb-24">
      ${statCard('Total Activities', d.total_activities, 'default', '📊', 'live-total')}
      ${statCard('Normal', d.normal_count, 'normal', '✅', 'live-normal')}
      ${statCard('Suspicious', d.suspicious_count, 'suspicious', '⚠️', 'live-suspicious')}
      ${statCard('Attacks', d.attack_count, 'attack', '🚨', 'live-attacks')}
      <div class="stat-card">
        <div class="stat-label">⚡ Attack Rate</div>
        <div class="stat-value default" id="live-attack-rate">${d.attack_percentage}%</div>
      </div>
    </div>

    <!-- Security score + Activity Distribution -->
    <div class="grid-2 mb-24">
      <div class="card">
        <div class="card-header"><span class="card-title"><span class="card-title-icon">🛡️</span> Security Score</span></div>
        <div class="card-body security-score-card">
          <div class="score-ring-wrap">
            <canvas id="scoreRingCanvas" width="130" height="130"></canvas>
            <div class="score-ring-center">
              <div class="score-ring-value" id="scoreValue">${d.security_score}</div>
              <div class="score-ring-label">/ 100</div>
            </div>
          </div>
          <div style="flex:1; min-width:0;">
            <div class="mb-12">
              <div class="text-muted" style="font-size:11px; text-transform:uppercase; letter-spacing:.06em; margin-bottom:6px">Threat Level</div>
              <span class="badge badge-${threatClass}" style="font-size:14px; padding:6px 16px">${d.threat_level}</span>
            </div>
            <div class="divider"></div>
            <div style="font-size:12px; color:var(--text-secondary); line-height:1.8">
              <div>📦 ${d.total_activities} activities analyzed</div>
              <div>🚨 ${d.attack_count} attack${d.attack_count!==1?'s':''} detected</div>
              <div>✅ ${d.normal_count} normal events</div>
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title"><span class="card-title-icon">🥧</span> Activity Distribution</span></div>
        <div class="card-body" style="padding-bottom:16px">
          <div class="chart-container" style="height:200px">
            <canvas id="actDistChart"></canvas>
          </div>
        </div>
      </div>
    </div>

    <!-- Attack Trend + Attack Types -->
    <div class="grid-2 mb-24">
      <div class="card">
        <div class="card-header"><span class="card-title"><span class="card-title-icon">📈</span> Attack Trend (7 Days)</span></div>
        <div class="card-body">
          <div class="chart-container" style="height:210px">
            <canvas id="trendChart"></canvas>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title"><span class="card-title-icon">🥊</span> Attack Types</span></div>
        <div class="card-body">
          <div class="chart-container" style="height:210px" id="attackDistWrap">
            <canvas id="attackDistChart"></canvas>
          </div>
        </div>
      </div>
    </div>

    <!-- Recent Alerts + Recent Activity -->
    <div class="grid-2">
      <div class="card">
        <div class="card-header">
          <span class="card-title"><span class="card-title-icon">🚨</span> Recent Alerts</span>
          <button class="btn btn-secondary btn-sm" onclick="OmniShield.navigate('alerts')">View All</button>
        </div>
        <div id="recentAlertsList"></div>
      </div>
      <div class="card">
        <div class="card-header">
          <span class="card-title"><span class="card-title-icon">📋</span> Recent Activity</span>
          <button class="btn btn-secondary btn-sm" onclick="OmniShield.navigate('history')">View All</button>
        </div>
        <div id="recentActivityList"></div>
      </div>
    </div>
  `;

  // Draw score ring
  const scoreColor = d.security_score >= 80 ? '#10b981' : d.security_score >= 60 ? '#f59e0b' : '#ef4444';
  OmniShield.drawScoreRing('scoreRingCanvas', d.security_score, scoreColor);

  // Activity distribution doughnut
  const actCtx = document.getElementById('actDistChart');
  if (actCtx) {
    const labels = ['Normal', 'Suspicious', 'Attack'];
    const data = [d.normal_count, d.suspicious_count, d.attack_count];
    const colors = ['#10b981', '#f59e0b', '#ef4444'];
    OmniShield.makeDoughnutChart(actCtx, labels, data, colors, 'actDistChart');
  }

  // Attack trend line
  const trendCtx = document.getElementById('trendChart');
  if (trendCtx && d.attack_trend.length) {
    OmniShield.makeLineChart(
      trendCtx,
      d.attack_trend.map(t => t.date),
      [{
        label: 'Attacks',
        data: d.attack_trend.map(t => t.attacks),
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239,68,68,0.08)',
        fill: true,
        tension: 0.4,
        pointBackgroundColor: '#ef4444',
        pointRadius: 4,
        pointHoverRadius: 6,
      }],
      'trendChart'
    );
  } else if (trendCtx) {
    trendCtx.parentElement.innerHTML = OmniShield.emptyState('📈', 'No trend data', 'Analyze traffic to see trends.');
  }

  // Attack distribution bar
  const attCtx = document.getElementById('attackDistChart');
  if (attCtx && d.attack_distribution.length) {
    OmniShield.makeBarChart(
      attCtx,
      d.attack_distribution.map(a => a.attack_type.toUpperCase()),
      d.attack_distribution.map(a => a.count),
      'Count', 'rgba(239,68,68,0.75)', 'attackDistChart'
    );
  } else if (attCtx) {
    attCtx.parentElement.innerHTML = OmniShield.emptyState('🕊️', 'No attacks recorded', 'No attack data available.');
  }

  // Recent alerts
  const alertsList = document.getElementById('recentAlertsList');
  if (d.recent_alerts.length === 0) {
    alertsList.innerHTML = OmniShield.emptyState('🔔', 'No open alerts', 'All clear!');
  } else {
    alertsList.innerHTML = d.recent_alerts.map(a => alertRow(a)).join('');
  }

  // Recent activity
  const actList = document.getElementById('recentActivityList');
  if (d.recent_activities.length === 0) {
    actList.innerHTML = OmniShield.emptyState('📋', 'No activities', 'No activity recorded yet.');
  } else {
    actList.innerHTML = buildActivityTable(d.recent_activities);
  }
}

function buildActivityTable(activities) {
  return `<div class="table-wrap"><table class="data-table">
    <thead><tr>
      <th>Time</th>
      <th>Src IP</th>
      <th>Prediction</th>
      <th>Risk</th>
      <th>Severity</th>
    </tr></thead>
    <tbody>
      ${activities.map(a => `
        <tr onclick="OmniShield.navigate('history')" title="View full history">
          <td class="text-muted mono" style="font-size:12px; white-space:nowrap">${OmniShield.formatRelTime(a.created_at)}</td>
          <td class="mono" style="font-size:12px; color:var(--text-secondary)">${a.source || '—'}</td>
          <td>${OmniShield.badge(a.prediction)}</td>
          <td>
            <div style="display:flex; align-items:center; gap:6px">
              <div style="width:40px; height:4px; border-radius:2px; background:rgba(255,255,255,0.08); overflow:hidden">
                <div style="height:100%; width:${a.risk_score}%; background:${OmniShield.riskColor(a.risk_score)}; border-radius:2px"></div>
              </div>
              <span style="color:${OmniShield.riskColor(a.risk_score)}; font-weight:700; font-size:13px">${a.risk_score}</span>
            </div>
          </td>
          <td>${OmniShield.badge(a.severity)}</td>
        </tr>`).join('')}
    </tbody></table></div>`;
}

function statCard(label, value, type, icon, id) {
  const display = typeof value === 'number' ? value.toLocaleString() : value;
  return `<div class="stat-card">
    <div class="stat-label">${icon} ${label}</div>
    <div class="stat-value ${type}" id="${id}">${display}</div>
  </div>`;
}

function alertRow(a) {
  const sev = (a.severity || 'info').toLowerCase();
  const icons = { critical: '🔴', high: '🟠', medium: '🟡', low: '🟢', info: 'ℹ️' };
  return `<div class="alert-item">
    <div class="alert-icon-wrap ${sev}">${icons[sev] || '⚠️'}</div>
    <div class="alert-meta">
      <div class="alert-title-row">
        <span class="alert-title">${a.title}</span>
        ${OmniShield.badge(a.severity)}
      </div>
      <div class="alert-message">${a.message}</div>
      <div class="alert-time">${OmniShield.formatRelTime(a.created_at)}</div>
    </div>
  </div>`;
}

function modelInfoBanner(model) {
  return `<div class="card mt-24">
    <div class="card-body d-flex gap-16">
      <span style="font-size:24px">🤖</span>
      <div>
        <div class="fw-600">${model.model_name || 'RandomForestClassifier'} — v${model.version}</div>
        <div class="text-secondary" style="font-size:13px">Accuracy: ${model.accuracy ? (model.accuracy*100).toFixed(1)+'%' : '—'} &nbsp;|&nbsp; Classes: ${(model.classes||[]).join(', ')} &nbsp;|&nbsp; Features: ${model.feature_count}</div>
      </div>
    </div>
  </div>`;
}
