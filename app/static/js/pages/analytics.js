/**
 * OmniShield AI — Analytics Page (Improved charts + real-time)
 */
OmniShield.registerPage('analytics', async (container) => {
  container.innerHTML = `
    <div class="card mb-16">
      <div class="card-body d-flex gap-16" style="padding:14px 24px; align-items:center; flex-wrap:wrap;">
        <span class="fw-600" style="font-size:13px; color:var(--text-secondary)">📅 Time period:</span>
        ${[7,14,30,90].map(d=>`<button class="btn btn-secondary btn-sm" id="period-${d}" onclick="loadAnalytics(${d})">${d}d</button>`).join('')}
        <span style="flex:1"></span>
        <span class="live-dot-indicator"></span>
        <span class="text-muted" style="font-size:12px" id="analyticsRefreshTime">Live data</span>
      </div>
    </div>
    <div id="analyticsContent"><div style="padding:60px;text-align:center"><div class="spinner"></div></div></div>
  `;
  loadAnalytics(14);
});

async function loadAnalytics(days) {
  [7,14,30,90].forEach(d => {
    const btn = document.getElementById('period-' + d);
    if (btn) btn.classList.toggle('btn-primary', d === days);
    if (btn) btn.classList.toggle('btn-secondary', d !== days);
  });

  const ts = document.getElementById('analyticsRefreshTime');
  if (ts) ts.textContent = 'Loading…';

  const res = await OmniShield.api.get('/analytics?days=' + days);
  const content = document.getElementById('analyticsContent');
  if (!content) return;

  if (!res.ok) { content.innerHTML = OmniShield.errorState('Failed to load analytics'); return; }

  const d = res.data.data;
  if (ts) ts.textContent = 'Updated ' + new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  if (!d.has_data) {
    content.innerHTML = OmniShield.emptyState('📈', 'No analytics data', `No activity in the last ${days} days. Analyze some network traffic first.`,
      `<button class="btn btn-primary mt-16" onclick="OmniShield.navigate('analyze')">🔍 Analyze Activity</button>`);
    return;
  }

  // Destroy old charts before re-render
  ['analyticsActDist','analyticsAttackDist','analyticsTrend','analyticsSevDist','analyticsRiskDist']
    .forEach(id => OmniShield.destroyChart(id));

  // Compute summary numbers
  const totalAct = d.activity_distribution.reduce((s, r) => s + r.count, 0);
  const totalAtk = d.attack_distribution.reduce((s, r) => s + r.count, 0);
  const normalCount = (d.activity_distribution.find(r => r.label === 'normal') || {}).count || 0;
  const attackPct = totalAct > 0 ? ((totalAct - normalCount) / totalAct * 100).toFixed(1) : 0;

  content.innerHTML = `
    <!-- Summary mini-cards -->
    <div class="stats-grid mb-20" style="grid-template-columns:repeat(auto-fit,minmax(140px,1fr))">
      <div class="stat-card">
        <div class="stat-label">📦 Total Events</div>
        <div class="stat-value default">${totalAct.toLocaleString()}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">✅ Normal</div>
        <div class="stat-value normal">${normalCount.toLocaleString()}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">🚨 Attacks</div>
        <div class="stat-value attack">${totalAtk.toLocaleString()}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">⚡ Attack Rate</div>
        <div class="stat-value default">${attackPct}%</div>
      </div>
    </div>

    <!-- Doughnut charts row -->
    <div class="grid-2 mb-20">
      <div class="card">
        <div class="card-header">
          <span class="card-title"><span class="card-title-icon">🥧</span> Activity Distribution</span>
          <span class="text-muted" style="font-size:12px">${totalAct} total</span>
        </div>
        <div class="card-body" style="padding-bottom:16px">
          <div class="chart-container" style="height:220px"><canvas id="analyticsActDist"></canvas></div>
        </div>
      </div>
      <div class="card">
        <div class="card-header">
          <span class="card-title"><span class="card-title-icon">⚡</span> Severity Distribution</span>
        </div>
        <div class="card-body" style="padding-bottom:16px">
          <div class="chart-container" style="height:220px"><canvas id="analyticsSevDist"></canvas></div>
        </div>
      </div>
    </div>

    <!-- Trend chart -->
    <div class="card mb-20">
      <div class="card-header">
        <span class="card-title"><span class="card-title-icon">📈</span> Daily Activity Trend (Last ${days} Days)</span>
      </div>
      <div class="card-body">
        <div class="chart-container" style="height:240px"><canvas id="analyticsTrend"></canvas></div>
      </div>
    </div>

    <!-- Attack type + Risk distribution row -->
    <div class="grid-2">
      <div class="card">
        <div class="card-header">
          <span class="card-title"><span class="card-title-icon">🥊</span> Attack Type Breakdown</span>
          ${totalAtk > 0 ? `<span class="text-muted" style="font-size:12px">${totalAtk} attacks</span>` : ''}
        </div>
        <div class="card-body">
          <div id="analyticsAttackDistWrap" class="chart-container" style="height:220px"><canvas id="analyticsAttackDist"></canvas></div>
        </div>
      </div>
      <div class="card">
        <div class="card-header">
          <span class="card-title"><span class="card-title-icon">🎯</span> Risk Score Distribution</span>
        </div>
        <div class="card-body">
          <div class="chart-container" style="height:220px"><canvas id="analyticsRiskDist"></canvas></div>
        </div>
      </div>
    </div>
  `;

  // Activity distribution doughnut
  const actDistCtx = document.getElementById('analyticsActDist');
  if (actDistCtx && d.activity_distribution.length) {
    const colorMap = { normal:'#10b981', suspicious:'#f59e0b', attack:'#ef4444' };
    OmniShield.makeDoughnutChart(
      actDistCtx,
      d.activity_distribution.map(r => r.label.charAt(0).toUpperCase() + r.label.slice(1)),
      d.activity_distribution.map(r => r.count),
      d.activity_distribution.map(r => colorMap[r.label] || '#3b82f6'),
      'analyticsActDist'
    );
  }

  // Severity distribution doughnut
  const sevCtx = document.getElementById('analyticsSevDist');
  if (sevCtx && d.severity_distribution.length) {
    const sevColors = { CRITICAL:'#dc2626', HIGH:'#f97316', MEDIUM:'#f59e0b', LOW:'#10b981', INFO:'#3b82f6' };
    OmniShield.makeDoughnutChart(
      sevCtx,
      d.severity_distribution.map(r => r.severity),
      d.severity_distribution.map(r => r.count),
      d.severity_distribution.map(r => sevColors[r.severity] || '#8892a4'),
      'analyticsSevDist'
    );
  }

  // Trend line
  const trendCtx = document.getElementById('analyticsTrend');
  if (trendCtx && d.attack_trend.length) {
    OmniShield.makeLineChart(
      trendCtx,
      d.attack_trend.map(r => r.date),
      [
        {
          label: 'Attacks',
          data: d.attack_trend.map(r => r.attacks),
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239,68,68,0.08)',
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#ef4444',
          pointRadius: 4,
          pointHoverRadius: 6,
        },
        {
          label: 'Normal',
          data: d.attack_trend.map(r => r.normal),
          borderColor: '#10b981',
          backgroundColor: 'rgba(16,185,129,0.05)',
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#10b981',
          pointRadius: 4,
          pointHoverRadius: 6,
        },
      ],
      'analyticsTrend'
    );
  } else if (trendCtx) {
    trendCtx.parentElement.innerHTML = OmniShield.emptyState('📈', 'No trend data', 'No trend available for this period.');
  }

  // Attack type distribution bar
  const atkCtx = document.getElementById('analyticsAttackDist');
  if (atkCtx) {
    if (d.attack_distribution.length > 0) {
      const atkColors = ['#ef4444','#f97316','#f59e0b','#dc2626','#b91c1c'];
      OmniShield.makeBarChart(
        atkCtx,
        d.attack_distribution.map(r => r.attack_type.toUpperCase()),
        d.attack_distribution.map(r => r.count),
        'Attacks',
        d.attack_distribution.map((_, i) => atkColors[i % atkColors.length]),
        'analyticsAttackDist'
      );
    } else {
      document.getElementById('analyticsAttackDistWrap').innerHTML =
        OmniShield.emptyState('🕊️', 'No attacks', 'No attack events in this period.');
    }
  }

  // Risk distribution bar
  const riskCtx = document.getElementById('analyticsRiskDist');
  if (riskCtx && d.risk_distribution.length) {
    const riskColors = ['#3b82f6','#10b981','#10b981','#f59e0b','#f97316','#ef4444'];
    OmniShield.makeBarChart(
      riskCtx,
      d.risk_distribution.map(r => r.range),
      d.risk_distribution.map(r => r.count),
      'Count',
      d.risk_distribution.map((_, i) => riskColors[i % riskColors.length]),
      'analyticsRiskDist'
    );
  }
}
