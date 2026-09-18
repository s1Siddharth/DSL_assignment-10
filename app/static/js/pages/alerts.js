/**
 * OmniShield AI — Alerts Page
 */
let _alertsState = { page: 1, per_page: 20 };

OmniShield.registerPage('alerts', (container) => {
  container.innerHTML = `
    <!-- Filters -->
    <div class="card mb-16">
      <div class="card-body" style="padding:18px 24px">
        <div class="filter-row" style="display:flex; align-items:flex-end; gap:20px; flex-wrap:wrap;">
          <div class="filter-group">
            <div>
              <label class="form-label" style="margin-bottom:6px;">ALERT STATUS</label>
              <select class="form-select" id="alertStatusFilter" onchange="loadAlerts()" style="min-width:160px;">
                <option value="">All Statuses</option>
                <option value="NEW">New</option>
                <option value="ACKNOWLEDGED">Acknowledged</option>
                <option value="RESOLVED">Resolved</option>
              </select>
            </div>
          </div>
          <div class="filter-group">
            <div>
              <label class="form-label" style="margin-bottom:6px;">SEVERITY LEVEL</label>
              <select class="form-select" id="alertSevFilter" onchange="loadAlerts()" style="min-width:160px;">
                <option value="">All Severities</option>
                <option>CRITICAL</option>
                <option>HIGH</option>
                <option>MEDIUM</option>
                <option>LOW</option>
              </select>
            </div>
          </div>
          <div style="margin-left:auto; font-family:var(--font-mono); font-size:13px; color:var(--text-secondary);" id="alertsTotal"></div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <span class="card-title"><span class="card-title-icon">🚨</span> Security Alerts</span>
        <span class="badge badge-new" id="alertsUnreadBadge" style="display:none"></span>
      </div>
      <div id="alertsList"></div>
      <div id="alertsPager"></div>
    </div>
  `;

  _alertsState.page = 1;
  loadAlerts();
});

async function loadAlerts() {
  const list = document.getElementById('alertsList');
  list.innerHTML = `<div style="padding:40px;text-align:center"><div class="spinner"></div></div>`;

  const status = document.getElementById('alertStatusFilter')?.value || '';
  const severity = document.getElementById('alertSevFilter')?.value || '';

  const params = new URLSearchParams({
    page: _alertsState.page,
    per_page: _alertsState.per_page,
    ...(status && { status }),
    ...(severity && { severity }),
  });

  const res = await OmniShield.api.get('/alerts?' + params);
  if (!res.ok) {
    list.innerHTML = OmniShield.errorState('Failed to load alerts');
    return;
  }

  const d = res.data.data;
  document.getElementById('alertsTotal').textContent = `${d.total} alert${d.total !== 1 ? 's' : ''}`;

  const unreadBadge = document.getElementById('alertsUnreadBadge');
  if (unreadBadge && d.unread_count > 0) {
    unreadBadge.textContent = `${d.unread_count} new`;
    unreadBadge.style.display = '';
  }

  if (d.alerts.length === 0) {
    list.innerHTML = OmniShield.emptyState('🔔', 'No alerts', 'No alerts match the current filters. All clear!');
    document.getElementById('alertsPager').innerHTML = '';
    return;
  }

  const icons = { CRITICAL: '🔴', HIGH: '🟠', MEDIUM: '🟡', LOW: '🟢', INFO: 'ℹ️' };

  list.innerHTML = d.alerts.map(a => {
    const sev = (a.severity || 'INFO').toUpperCase();
    return `
      <div class="alert-item" id="alert-item-${a.id}">
        <div class="alert-icon-wrap ${sev.toLowerCase()}">${icons[sev] || '⚠️'}</div>
        <div class="alert-meta">
          <div class="alert-title-row">
            <span class="alert-title">${a.title}</span>
            ${OmniShield.badge(a.severity)}
            ${OmniShield.badge(a.status)}
          </div>
          <div class="alert-message">${a.message}</div>
          <div class="alert-time">${OmniShield.formatDate(a.created_at)}
            ${a.risk_score !== null ? ` &nbsp;|&nbsp; Risk: <strong style="color:${OmniShield.riskColor(a.risk_score)}">${a.risk_score}</strong>` : ''}
            ${a.activity_id ? ` &nbsp;|&nbsp; Activity #${a.activity_id}` : ''}
          </div>
        </div>
        <div class="alert-actions">
          ${a.status === 'NEW' ? `<button class="btn btn-secondary btn-sm" onclick="updateAlertStatus(${a.id},'ACKNOWLEDGED')">Acknowledge</button>` : ''}
          ${a.status !== 'RESOLVED' ? `<button class="btn btn-sm" style="background:rgba(16,185,129,0.1);color:var(--color-normal);border:1px solid rgba(16,185,129,0.3)" onclick="updateAlertStatus(${a.id},'RESOLVED')">Resolve</button>` : ''}
        </div>
      </div>`;
  }).join('');

  // Pagination
  const pager = document.getElementById('alertsPager');
  if (d.pages > 1) {
    pager.innerHTML = `<div class="pagination">
      <button class="pagination-btn" onclick="alertsGoPage(${_alertsState.page-1})" ${_alertsState.page<=1?'disabled':''}>← Prev</button>
      <span class="pagination-info">Page ${_alertsState.page} of ${d.pages}</span>
      <button class="pagination-btn" onclick="alertsGoPage(${_alertsState.page+1})" ${_alertsState.page>=d.pages?'disabled':''}>Next →</button>
    </div>`;
  } else {
    pager.innerHTML = '';
  }
}

function alertsGoPage(p) {
  _alertsState.page = p;
  loadAlerts();
}

async function updateAlertStatus(id, status) {
  const res = await OmniShield.api.patch('/alerts/' + id, { status });
  if (res.ok) {
    OmniShield.toast(`Alert ${status.toLowerCase()}`, 'success');
    OmniShield.refreshAlertCount();
    loadAlerts();
  } else {
    OmniShield.toast(res.data?.error?.message || 'Failed to update alert', 'error');
  }
}
