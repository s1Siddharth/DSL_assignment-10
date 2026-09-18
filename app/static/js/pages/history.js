/**
 * OmniShield AI — Activity History Page
 */
let _historyState = { page: 1, per_page: 20, total: 0, pages: 0 };
let _historyFilters = {};

OmniShield.registerPage('history', (container) => {
  container.innerHTML = `
    <!-- Filters -->
    <div class="card mb-16">
      <div class="card-body" style="padding:16px 24px">
        <div class="form-grid" style="grid-template-columns:1fr 1fr 1fr 1fr auto">
          <div>
            <label class="form-label">Search</label>
            <input type="text" class="form-control" id="histSearch" placeholder="IP, attack type…" oninput="historyApplyFilters()">
          </div>
          <div>
            <label class="form-label">Prediction</label>
            <select class="form-control" id="histPred" onchange="historyApplyFilters()">
              <option value="">All</option>
              <option>normal</option><option>suspicious</option><option>attack</option>
            </select>
          </div>
          <div>
            <label class="form-label">Severity</label>
            <select class="form-control" id="histSev" onchange="historyApplyFilters()">
              <option value="">All</option>
              <option>CRITICAL</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option><option>INFO</option>
            </select>
          </div>
          <div>
            <label class="form-label">Attack Type</label>
            <input type="text" class="form-control" id="histAttack" placeholder="dos, probe…" oninput="historyApplyFilters()">
          </div>
          <div style="display:flex;align-items:flex-end">
            <button class="btn btn-secondary" onclick="historyClearFilters()">Clear</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Table -->
    <div class="card">
      <div class="card-header">
        <span class="card-title"><span class="card-title-icon">📋</span> Activity History</span>
        <span class="text-muted" style="font-size:13px" id="histTotal">Loading…</span>
      </div>
      <div id="histTable"></div>
      <div id="histPager"></div>
    </div>
  `;

  _historyState.page = 1;
  _historyFilters = {};
  loadHistory();
});

function historyApplyFilters() {
  _historyFilters = {
    search: document.getElementById('histSearch')?.value?.trim() || '',
    prediction: document.getElementById('histPred')?.value || '',
    severity: document.getElementById('histSev')?.value || '',
    attack_type: document.getElementById('histAttack')?.value?.trim() || '',
  };
  _historyState.page = 1;
  loadHistory();
}

function historyClearFilters() {
  document.getElementById('histSearch').value = '';
  document.getElementById('histPred').value = '';
  document.getElementById('histSev').value = '';
  document.getElementById('histAttack').value = '';
  _historyFilters = {};
  _historyState.page = 1;
  loadHistory();
}

async function loadHistory() {
  const table = document.getElementById('histTable');
  table.innerHTML = `<div style="padding:40px;text-align:center"><div class="spinner"></div></div>`;

  const params = new URLSearchParams({
    page: _historyState.page,
    per_page: _historyState.per_page,
    sort_by: 'created_at',
    sort_order: 'desc',
    ...Object.fromEntries(Object.entries(_historyFilters).filter(([,v]) => v)),
  });

  const res = await OmniShield.api.get('/activities?' + params);
  if (!res.ok) {
    table.innerHTML = OmniShield.errorState('Failed to load activities');
    return;
  }

  const d = res.data.data;
  _historyState.total = d.total;
  _historyState.pages = d.pages;

  document.getElementById('histTotal').textContent = `${d.total.toLocaleString()} records`;

  if (d.activities.length === 0) {
    table.innerHTML = OmniShield.emptyState('📋', 'No activities found', 'Try adjusting filters or analyze some network activity.');
    document.getElementById('histPager').innerHTML = '';
    return;
  }

  table.innerHTML = `<div class="table-wrap"><table class="data-table">
    <thead><tr>
      <th>#</th><th>Time</th><th>Source</th><th>Destination</th>
      <th>Protocol</th><th>Prediction</th><th>Attack Type</th>
      <th>Confidence</th><th>Risk</th><th>Severity</th>
    </tr></thead>
    <tbody>
      ${d.activities.map(a => `
        <tr onclick="showActivityDetail(${a.id})" title="Click for details">
          <td class="mono text-muted">#${a.id}</td>
          <td class="text-muted">${OmniShield.formatRelTime(a.created_at)}</td>
          <td class="mono">${a.source || '—'}</td>
          <td class="mono">${a.destination || '—'}</td>
          <td>${a.protocol || '—'}</td>
          <td>${OmniShield.badge(a.prediction)}</td>
          <td>${a.attack_type ? `<span class="tag">${a.attack_type.toUpperCase()}</span>` : '—'}</td>
          <td>${a.confidence !== null ? (a.confidence*100).toFixed(1)+'%' : '<span class="text-muted">N/A</span>'}</td>
          <td><span style="color:${OmniShield.riskColor(a.risk_score)};font-weight:700">${a.risk_score}</span></td>
          <td>${OmniShield.badge(a.severity)}</td>
        </tr>`).join('')}
    </tbody></table></div>`;

  renderPager(d.total, d.pages, _historyState.page);
}

function renderPager(total, pages, current) {
  const pager = document.getElementById('histPager');
  if (pages <= 1) { pager.innerHTML = ''; return; }

  let html = `<div class="pagination">
    <button class="pagination-btn" onclick="historyGoPage(${current-1})" ${current<=1?'disabled':''}>← Prev</button>`;

  const start = Math.max(1, current - 2);
  const end = Math.min(pages, current + 2);
  if (start > 1) html += `<button class="pagination-btn" onclick="historyGoPage(1)">1</button>`;
  if (start > 2) html += `<span class="pagination-btn" style="cursor:default">…</span>`;
  for (let p = start; p <= end; p++) {
    html += `<button class="pagination-btn ${p===current?'active':''}" onclick="historyGoPage(${p})">${p}</button>`;
  }
  if (end < pages - 1) html += `<span class="pagination-btn" style="cursor:default">…</span>`;
  if (end < pages) html += `<button class="pagination-btn" onclick="historyGoPage(${pages})">${pages}</button>`;
  html += `<button class="pagination-btn" onclick="historyGoPage(${current+1})" ${current>=pages?'disabled':''}>Next →</button>
    <span class="pagination-info">Page ${current} of ${pages} &nbsp;(${total} total)</span></div>`;
  pager.innerHTML = html;
}

function historyGoPage(p) {
  _historyState.page = p;
  loadHistory();
}

async function showActivityDetail(id) {
  OmniShield.showModal('Activity Detail', `<div style="text-align:center;padding:40px"><div class="spinner"></div></div>`);
  const res = await OmniShield.api.get('/activities/' + id);
  if (!res.ok) {
    document.querySelector('.modal-body').innerHTML = OmniShield.errorState('Failed to load activity');
    return;
  }
  const a = res.data.data;
  const riskColor = OmniShield.riskColor(a.risk_score);
  const confStr = a.confidence !== null ? `${(a.confidence*100).toFixed(1)}%` : 'Unavailable';

  document.querySelector('.modal-body').innerHTML = `
    <div class="grid-2 mb-16">
      <div class="result-metric"><div class="result-metric-label">Prediction</div><div>${OmniShield.badge(a.prediction)}</div></div>
      <div class="result-metric"><div class="result-metric-label">Attack Type</div><div class="fw-600">${a.attack_type?.toUpperCase() || '—'}</div></div>
      <div class="result-metric"><div class="result-metric-label">Confidence</div><div class="fw-600" style="color:var(--accent-cyan)">${confStr}</div></div>
      <div class="result-metric"><div class="result-metric-label">Risk Score</div><div class="fw-600" style="color:${riskColor}">${a.risk_score}/100</div></div>
      <div class="result-metric"><div class="result-metric-label">Severity</div><div>${OmniShield.badge(a.severity)}</div></div>
      <div class="result-metric"><div class="result-metric-label">Anomaly Score</div><div class="fw-600">${a.anomaly_score?.toFixed(3) ?? 'N/A'}</div></div>
    </div>
    <div class="divider"></div>
    <div class="grid-2 mb-16">
      <div><span class="text-muted" style="font-size:12px">Source:</span> <strong class="mono">${a.source||'—'}</strong></div>
      <div><span class="text-muted" style="font-size:12px">Destination:</span> <strong class="mono">${a.destination||'—'}</strong></div>
      <div><span class="text-muted" style="font-size:12px">Protocol:</span> <strong>${a.protocol||'—'}</strong></div>
      <div><span class="text-muted" style="font-size:12px">Time:</span> <strong>${OmniShield.formatDate(a.created_at)}</strong></div>
    </div>
    ${a.explanation?.summary ? `
      <div class="divider"></div>
      <div class="fw-600 mb-8" style="font-size:13px">📝 Explanation</div>
      <div style="font-size:13px;color:var(--text-secondary);line-height:1.6;margin-bottom:12px">${a.explanation.summary}</div>
      ${(a.explanation.key_factors||[]).map(f=>
        `<div class="explanation-item"><div class="explanation-factor">${f.factor}</div><div class="explanation-detail">${f.detail}</div></div>`
      ).join('')}` : ''}
  `;
}
