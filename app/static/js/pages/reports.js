/**
 * OmniShield AI — Reports Page
 */
OmniShield.registerPage('reports', async (container) => {
  container.innerHTML = `
    <div class="grid-2" style="align-items:start">
      <!-- Generate panel -->
      <div class="card">
        <div class="card-header"><span class="card-title"><span class="card-title-icon">📄</span> Generate Report</span></div>
        <div class="card-body">
          <div class="form-group">
            <label class="form-label">Report Type</label>
            <select class="form-control" id="reportType">
              <option value="summary">Summary Report</option>
              <option value="detailed">Detailed Report</option>
            </select>
          </div>
          <div style="font-size:13px;color:var(--text-secondary);margin-bottom:20px;line-height:1.5">
            Reports are generated from actual database and model data.<br>
            <strong>Summary:</strong> Aggregated statistics and key metrics.<br>
            <strong>Detailed:</strong> Includes recent activities and alerts.
          </div>
          <button class="btn btn-primary" id="generateReportBtn" onclick="generateReport()">
            ⚡ Generate Report
          </button>
        </div>
      </div>

      <!-- Report output -->
      <div id="reportOutput">
        <div class="card">
          <div class="card-body">
            ${OmniShield.emptyState('📄', 'No report yet', 'Select a report type and click Generate Report.')}
          </div>
        </div>
      </div>
    </div>
  `;
});

async function generateReport() {
  const btn = document.getElementById('generateReportBtn');
  const type = document.getElementById('reportType').value;
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner" style="width:16px;height:16px;border-width:2px"></div> Generating…';

  const res = await OmniShield.api.post('/report/generate', { type });
  btn.disabled = false;
  btn.innerHTML = '⚡ Generate Report';

  if (!res.ok) {
    OmniShield.toast(res.data?.error?.message || 'Failed to generate report', 'error');
    return;
  }

  const r = res.data.data;
  renderReport(r);
  OmniShield.toast('Report generated', 'success');
}

function renderReport(r) {
  const output = document.getElementById('reportOutput');

  const summaryHTML = `
    <div class="stats-grid mb-20">
      <div class="stat-card"><div class="stat-label">Total Activities</div><div class="stat-value default">${r.summary.total_activities.toLocaleString()}</div></div>
      <div class="stat-card"><div class="stat-label">Normal</div><div class="stat-value normal">${r.summary.normal.toLocaleString()}</div></div>
      <div class="stat-card"><div class="stat-label">Suspicious</div><div class="stat-value suspicious">${r.summary.suspicious.toLocaleString()}</div></div>
      <div class="stat-card"><div class="stat-label">Attacks</div><div class="stat-value attack">${r.summary.attacks.toLocaleString()}</div></div>
    </div>`;

  const attackBreakdown = Object.entries(r.attack_breakdown || {}).length > 0
    ? `<div class="mb-16">
        <div class="fw-600 mb-8" style="font-size:13px">🥊 Attack Breakdown</div>
        ${Object.entries(r.attack_breakdown).map(([type,count]) =>
          `<div class="d-flex mb-8">
            <span class="tag">${type.toUpperCase()}</span>
            <span class="text-secondary" style="margin-left:8px;font-size:13px">${count} event${count>1?'s':''}</span>
          </div>`
        ).join('')}
      </div>`
    : '';

  const modelSection = r.model ? `
    <div class="card mb-16" style="border-color:rgba(0,212,255,0.2)">
      <div class="card-body">
        <div class="fw-600 mb-8">🤖 Active Model</div>
        <div class="grid-2">
          <div><span class="text-muted">Name:</span> <strong>${r.model.model_name}</strong></div>
          <div><span class="text-muted">Version:</span> <strong class="mono">${r.model.version}</strong></div>
          <div><span class="text-muted">Accuracy:</span> <strong>${r.model.accuracy ? (r.model.accuracy*100).toFixed(1)+'%' : 'N/A'}</strong></div>
          <div><span class="text-muted">F1 Score:</span> <strong>${r.model.f1_score ? (r.model.f1_score*100).toFixed(1)+'%' : 'N/A'}</strong></div>
        </div>
      </div>
    </div>` : '';

  output.innerHTML = `
    <div class="card">
      <div class="card-header">
        <span class="card-title"><span class="card-title-icon">📄</span> ${r.report_type === 'detailed' ? 'Detailed' : 'Summary'} Report</span>
        <span class="text-muted" style="font-size:12px">${OmniShield.formatDate(r.generated_at)}</span>
      </div>
      <div class="card-body">
        ${summaryHTML}

        <div class="grid-2 mb-16">
          <div class="result-metric">
            <div class="result-metric-label">Attack Rate</div>
            <div class="result-metric-value" style="color:var(--color-attack)">${r.summary.attack_percentage}%</div>
          </div>
          <div class="result-metric">
            <div class="result-metric-label">Avg Risk Score</div>
            <div class="result-metric-value" style="color:${OmniShield.riskColor(r.risk.average||0)}">${r.risk.average ?? 'N/A'}</div>
          </div>
          <div class="result-metric">
            <div class="result-metric-label">Open Alerts</div>
            <div class="result-metric-value attack">${r.alerts.open}</div>
          </div>
          <div class="result-metric">
            <div class="result-metric-label">Resolved Alerts</div>
            <div class="result-metric-value normal">${r.alerts.resolved}</div>
          </div>
        </div>

        ${attackBreakdown}
        ${modelSection}

        ${r.report_type === 'detailed' && r.recent_activities?.length ? `
          <div class="divider"></div>
          <div class="fw-600 mb-8">📋 Recent Activities (last 50)</div>
          <div class="table-wrap">
            <table class="data-table">
              <thead><tr><th>Time</th><th>Prediction</th><th>Attack Type</th><th>Risk</th><th>Severity</th></tr></thead>
              <tbody>
                ${r.recent_activities.slice(0,20).map(a => `
                  <tr>
                    <td class="text-muted">${OmniShield.formatDate(a.created_at)}</td>
                    <td>${OmniShield.badge(a.prediction)}</td>
                    <td>${a.attack_type?.toUpperCase() || '—'}</td>
                    <td style="color:${OmniShield.riskColor(a.risk_score)};font-weight:600">${a.risk_score}</td>
                    <td>${OmniShield.badge(a.severity)}</td>
                  </tr>`).join('')}
              </tbody>
            </table>
          </div>` : ''}

        <div class="mt-20">
          <button class="btn btn-secondary btn-sm" onclick="downloadReportJSON(${JSON.stringify(JSON.stringify(r))})">⬇️ Download JSON</button>
        </div>
      </div>
    </div>`;
}

function downloadReportJSON(jsonStr) {
  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `omnishield_report_${new Date().toISOString().slice(0,10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
  OmniShield.toast('Report downloaded', 'success');
}
