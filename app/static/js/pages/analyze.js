/**
 * OmniShield AI — Analyze Activity Page
 */
let _analyzeFeatures = [];
let _analyzeTab = 'manual'; // 'manual' or 'batch'

OmniShield.registerPage('analyze', async (container) => {
  container.innerHTML = `<div style="padding:60px;text-align:center"><div class="spinner"></div><p class="text-muted mt-16">Loading model features…</p></div>`;

  const res = await OmniShield.api.get('/model/features');
  const featureInfo = res.ok ? res.data.data : { features: [], model_loaded: false };
  _analyzeFeatures = featureInfo.features || [];

  renderAnalyzePage(container, featureInfo);
});

function renderAnalyzePage(container, info) {
  const modelLoaded = info.model_loaded;

  container.innerHTML = `
    <div class="grid-2" style="align-items:start">
      <!-- Left: Input forms -->
      <div>
        ${!modelLoaded ? `
          <div class="card mb-16" style="border-color:rgba(245,158,11,0.3)">
            <div class="card-body d-flex gap-12" style="padding:16px">
              <span style="font-size:20px">⚠️</span>
              <div>
                <div class="fw-600 text-suspicious">No model loaded</div>
                <div class="text-secondary" style="font-size:13px;margin-top:4px">
                  Please <a href="#" onclick="OmniShield.navigate('datasets')">upload a dataset and train a model</a> first.
                </div>
              </div>
            </div>
          </div>` : ''}

        <div class="card">
          <div class="card-header" style="padding:0">
            <div style="display:flex;width:100%">
              <div class="tab-btn ${_analyzeTab === 'manual' ? 'active' : ''}" onclick="switchAnalyzeTab('manual')" style="flex:1;text-align:center;padding:16px;cursor:pointer;border-bottom: 2px solid ${_analyzeTab === 'manual' ? 'var(--accent-cyan)' : 'transparent'};color:${_analyzeTab === 'manual' ? 'var(--text-primary)' : 'var(--text-muted)'};font-weight:600">
                <span class="card-title-icon">🔍</span> Manual Input
              </div>
              <div class="tab-btn ${_analyzeTab === 'batch' ? 'active' : ''}" onclick="switchAnalyzeTab('batch')" style="flex:1;text-align:center;padding:16px;cursor:pointer;border-bottom: 2px solid ${_analyzeTab === 'batch' ? 'var(--accent-cyan)' : 'transparent'};color:${_analyzeTab === 'batch' ? 'var(--text-primary)' : 'var(--text-muted)'};font-weight:600">
                <span class="card-title-icon">📊</span> Batch Upload (CSV)
              </div>
            </div>
          </div>
          
          <div class="card-body">
            <!-- MANUAL TAB -->
            <div id="tab-manual" style="display:${_analyzeTab === 'manual' ? 'block' : 'none'}">
              <form id="analyzeForm" onsubmit="submitAnalysis(event)">
                <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.1em;font-weight:600;margin-bottom:12px">Network Metadata</div>
                <div class="form-grid mb-24">
                  <div class="form-group">
                    <label class="form-label">Source IP / Host</label>
                    <input type="text" class="form-control" name="source" placeholder="e.g. 192.168.1.100" />
                  </div>
                  <div class="form-group">
                    <label class="form-label">Destination IP / Host</label>
                    <input type="text" class="form-control" name="destination" placeholder="e.g. 10.0.0.1" />
                  </div>
                  <div class="form-group">
                    <label class="form-label">Protocol</label>
                    <select class="form-control" name="protocol">
                      <option value="">Select…</option>
                      <option>TCP</option><option>UDP</option><option>ICMP</option><option>HTTP</option><option>HTTPS</option><option>DNS</option>
                    </select>
                  </div>
                </div>

                <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.1em;font-weight:600;margin-bottom:12px">
                  Model Features
                  ${modelLoaded ? `<span style="font-weight:400;text-transform:none;color:var(--text-muted)">(${_analyzeFeatures.length} features)</span>` : ''}
                </div>
                <div id="featureFields">
                  ${renderFeatureFields(_analyzeFeatures, modelLoaded)}
                </div>

                <div class="mt-24 d-flex gap-16">
                  <button type="submit" class="btn btn-primary" id="analyzeBtn" ${!modelLoaded?'disabled':''}>
                    ⚡ Analyze Activity
                  </button>
                  <button type="button" class="btn btn-secondary" onclick="clearAnalyzeForm()">Clear</button>
                </div>
              </form>
            </div>
            
            <!-- BATCH TAB -->
            <div id="tab-batch" style="display:${_analyzeTab === 'batch' ? 'block' : 'none'}">
              <div class="upload-zone" id="batchUploadZone" onclick="document.getElementById('batchFileInput').click()" style="border: 2px dashed var(--border-accent); border-radius: var(--radius-lg); padding: 40px; text-align: center; cursor: pointer; transition: all 0.2s;">
                <div style="font-size: 40px; margin-bottom: 12px;">📁</div>
                <div class="fw-600 mb-8">Drop CSV file here or click to browse</div>
                <div class="text-muted" style="font-size: 13px;">Max 50MB · CSV format only</div>
                <button class="btn btn-secondary mt-8" type="button" onclick="event.stopPropagation(); document.getElementById('batchFileInput').click()">Browse Files</button>
              </div>
              <input type="file" id="batchFileInput" accept=".csv" style="display:none" onchange="handleBatchFileSelect(event)">
              <div id="batchUploadStatus" class="mt-16"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Result panel -->
      <div id="resultArea">
        <div class="card">
          <div class="card-body">
            ${OmniShield.emptyState('🔬', 'No analysis yet', 'Submit data to get a real ML prediction.')}
          </div>
        </div>
      </div>
    </div>
  `;
  
  if (_analyzeTab === 'batch') {
    setupBatchUploadZone();
  }
}

window.switchAnalyzeTab = function(tab) {
  _analyzeTab = tab;
  document.getElementById('tab-manual').style.display = tab === 'manual' ? 'block' : 'none';
  document.getElementById('tab-batch').style.display = tab === 'batch' ? 'block' : 'none';
  
  const btns = document.querySelectorAll('.tab-btn');
  btns[0].style.borderBottomColor = tab === 'manual' ? 'var(--accent-cyan)' : 'transparent';
  btns[0].style.color = tab === 'manual' ? 'var(--text-primary)' : 'var(--text-muted)';
  
  btns[1].style.borderBottomColor = tab === 'batch' ? 'var(--accent-cyan)' : 'transparent';
  btns[1].style.color = tab === 'batch' ? 'var(--text-primary)' : 'var(--text-muted)';
  
  if (tab === 'batch') {
    setupBatchUploadZone();
  }
}

function setupBatchUploadZone() {
  const zone = document.getElementById('batchUploadZone');
  if (!zone) return;
  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.style.borderColor = 'var(--text-primary)'; zone.style.background = 'var(--bg-glass)'; });
  zone.addEventListener('dragleave', () => { zone.style.borderColor = 'var(--border-accent)'; zone.style.background = 'transparent'; });
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.style.borderColor = 'var(--border-accent)';
    zone.style.background = 'transparent';
    const file = e.dataTransfer.files[0];
    if (file) uploadBatchFile(file);
  });
}

window.handleBatchFileSelect = function(e) {
  const file = e.target.files[0];
  if (file) uploadBatchFile(file);
}

async function uploadBatchFile(file) {
  const status = document.getElementById('batchUploadStatus');
  status.innerHTML = `<div class="d-flex gap-16" style="padding:16px;background:var(--bg-glass);border-radius:var(--radius-md)">
    <div class="spinner" style="width:24px;height:24px;border-width:2px;flex-shrink:0"></div>
    <div>
      <div class="fw-600 mb-8">Analyzing ${file.name}…</div>
      <div class="text-secondary" style="font-size:13px">This may take a moment for large datasets. Please wait.</div>
    </div>
  </div>`;

  const fd = new FormData();
  fd.append('file', file);
  const res = await OmniShield.api.upload('/analyze/batch', fd);

  if (!res.ok) {
    status.innerHTML = OmniShield.errorState(res.data?.error?.message || 'Batch analysis failed');
    return;
  }

  const d = res.data.data;
  status.innerHTML = `<div class="toast success" style="position:static;animation:none">✅ Successfully analyzed ${d.total_analyzed} activities.</div>`;
  
  OmniShield.refreshAlertCount();
  
  // Render batch summary result
  const alertsHtml = d.alerts_generated > 0 
    ? `<div class="text-attack fw-600 mt-16">🚨 ${d.alerts_generated} Alerts Generated</div>` 
    : `<div class="text-normal fw-600 mt-16">✅ No Alerts Generated</div>`;

  document.getElementById('resultArea').innerHTML = `
    <div class="card">
      <div class="card-header"><span class="card-title">📊 Batch Analysis Complete</span></div>
      <div class="card-body">
        <div class="grid-2 mb-24">
          <div class="result-metric"><div class="result-metric-label">Total Rows</div><div class="fw-700" style="font-size:24px">${d.total_analyzed}</div></div>
          <div class="result-metric"><div class="result-metric-label">Model Version</div><div class="fw-700 text-muted" style="font-size:24px">v${d.model_version || '?'}</div></div>
        </div>
        <div class="fw-600 mb-16" style="font-size:13px">Prediction Breakdown</div>
        <div class="d-flex gap-16 mb-24" style="flex-wrap:wrap">
          <div style="flex:1;background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);padding:16px;border-radius:8px;text-align:center">
            <div style="font-size:24px;color:var(--color-normal)" class="fw-700 mb-8">${d.prediction_counts?.normal || 0}</div>
            <div class="text-muted" style="font-size:12px;text-transform:uppercase">Normal</div>
          </div>
          <div style="flex:1;background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);padding:16px;border-radius:8px;text-align:center">
            <div style="font-size:24px;color:var(--color-suspicious)" class="fw-700 mb-8">${d.prediction_counts?.suspicious || 0}</div>
            <div class="text-muted" style="font-size:12px;text-transform:uppercase">Suspicious</div>
          </div>
          <div style="flex:1;background:rgba(244,63,94,0.1);border:1px solid rgba(244,63,94,0.3);padding:16px;border-radius:8px;text-align:center">
            <div style="font-size:24px;color:var(--color-attack)" class="fw-700 mb-8">${d.prediction_counts?.attack || 0}</div>
            <div class="text-muted" style="font-size:12px;text-transform:uppercase">Attacks</div>
          </div>
        </div>
        <div class="divider"></div>
        ${alertsHtml}
        <button class="btn btn-secondary mt-24" style="width:100%" onclick="OmniShield.navigate('history')">View Details in Activity History →</button>
      </div>
    </div>
  `;
}

function renderFeatureFields(features, modelLoaded) {
  if (!modelLoaded) {
    return `<div class="empty-state" style="padding:24px">
      <div class="empty-icon">🤖</div>
      <div class="empty-sub">Feature fields will appear once a model is trained.</div>
    </div>`;
  }
  if (features.length === 0) {
    return `<div class="empty-sub">No features returned by the model.</div>`;
  }
  const half = Math.ceil(features.length / 2);
  const cols = [features.slice(0, half), features.slice(half)];
  return `<div class="form-grid">${cols.flat().map(f =>
    `<div class="form-group">
       <label class="form-label mono" style="font-size:11px">${f}</label>
       <input type="number" step="any" class="form-control" name="feat_${f}" id="feat_${f}" placeholder="0" />
     </div>`
  ).join('')}</div>`;
}

window.submitAnalysis = async function(e) {
  e.preventDefault();
  const btn = document.getElementById('analyzeBtn');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner" style="width:16px;height:16px;border-width:2px"></div> Analyzing…';

  const form = e.target;
  const data = {};

  // Network metadata
  const source = form.elements['source']?.value?.trim();
  const dest = form.elements['destination']?.value?.trim();
  const protocol = form.elements['protocol']?.value?.trim();
  if (source) data.source = source;
  if (dest) data.destination = dest;
  if (protocol) data.protocol = protocol;

  // Feature values
  _analyzeFeatures.forEach(f => {
    const el = form.elements['feat_' + f];
    if (el && el.value !== '') data[f] = parseFloat(el.value) || el.value;
  });

  const res = await OmniShield.api.post('/analyze', data);
  btn.disabled = false;
  btn.innerHTML = '⚡ Analyze Activity';

  if (!res.ok) {
    OmniShield.toast(res.data?.error?.message || 'Analysis failed', 'error');
    document.getElementById('resultArea').innerHTML = OmniShield.errorState(res.data?.error?.message || 'Analysis failed');
    return;
  }

  const result = res.data.data;
  renderResult(result);
  OmniShield.refreshAlertCount();
  OmniShield.toast('Analysis complete', 'success');
}

function renderResult(r) {
  const pred = r.prediction;
  const icons = { normal: '✅', attack: '🚨', suspicious: '⚠️' };
  const titles = {
    normal: 'Normal Activity',
    attack: `Attack Detected: ${(r.attack_type || 'Unknown').toUpperCase()}`,
    suspicious: 'Suspicious Activity',
  };

  const riskColor = OmniShield.riskColor(r.risk_score);
  const confStr = r.confidence !== null ? `${(r.confidence * 100).toFixed(1)}%` : 'Unavailable';
  const anomalyStr = r.anomaly_score !== null ? r.anomaly_score.toFixed(3) : 'N/A';

  const html = `
    <div class="result-panel card" style="border:1px solid var(--border-subtle)">
      <div class="result-header ${pred}" style="padding:20px;border-bottom:1px solid var(--border-subtle);display:flex;align-items:center;gap:16px">
        <div class="result-icon" style="font-size:32px">${icons[pred] || '❓'}</div>
        <div>
          <div class="result-title fw-600" style="font-size:16px">${titles[pred]}</div>
          <div class="text-secondary" style="font-size:13px;margin-top:4px">${OmniShield.formatDate(r.timestamp)}</div>
        </div>
        <div style="margin-left:auto">${OmniShield.badge(r.severity)}</div>
      </div>

      <div class="result-body" style="padding:20px">
        <!-- Metrics -->
        <div class="form-grid mb-24" style="grid-template-columns:1fr 1fr">
          <div class="result-metric">
            <div class="result-metric-label">Prediction</div>
            <div class="result-metric-value small mt-8">${OmniShield.badge(r.prediction)}</div>
          </div>
          <div class="result-metric">
            <div class="result-metric-label">Confidence</div>
            <div class="result-metric-value fw-700 mt-8" style="font-size:20px;color:${r.confidence !== null ? '#00d4ff' : 'var(--text-muted)'}">${confStr}</div>
          </div>
          <div class="result-metric mt-16">
            <div class="result-metric-label">Risk Score</div>
            <div class="result-metric-value fw-700 mt-8" style="font-size:24px;color:${riskColor}">${r.risk_score}<span style="font-size:14px;color:var(--text-muted)">/100</span></div>
          </div>
          <div class="result-metric mt-16">
            <div class="result-metric-label">Anomaly Score</div>
            <div class="result-metric-value fw-700 mt-8" style="font-size:20px;color:var(--text-secondary)">${anomalyStr}</div>
          </div>
        </div>

        <div class="divider"></div>

        <!-- Explanation summary -->
        ${r.explanation?.summary ? `
          <div class="card mb-16" style="background:var(--bg-glass);border-color:var(--border-subtle)">
            <div class="card-body" style="padding:16px">
              <div class="fw-600 mb-8" style="font-size:13px">📝 Summary</div>
              <div style="font-size:13px;color:var(--text-secondary);line-height:1.6">${r.explanation.summary}</div>
            </div>
          </div>` : ''}

        <!-- Key factors -->
        ${r.explanation?.key_factors?.length ? `
          <div class="mb-16">
            <div class="fw-600 mb-12" style="font-size:13px">🔑 Key Factors</div>
            ${r.explanation.key_factors.map(f => `
              <div class="explanation-item">
                <div class="explanation-factor">${f.factor}</div>
                <div class="explanation-detail">${f.detail}</div>
              </div>`).join('')}
          </div>` : ''}

        <!-- Class probabilities -->
        ${r.explanation?.class_probabilities ? `
          <div class="mb-16">
            <div class="fw-600 mb-12" style="font-size:13px">🎯 Class Probabilities</div>
            <div class="form-grid" style="grid-template-columns:1fr 1fr">
              ${Object.entries(r.explanation.class_probabilities)
                .sort((a,b)=>b[1]-a[1])
                .map(([cls, prob]) => `
                  <div class="result-metric p-8" style="background:var(--bg-glass);border-radius:8px;padding:8px">
                    <div class="result-metric-label">${cls.toUpperCase()}</div>
                    <div class="result-metric-value mt-4 fw-600" style="font-size:16px">${(prob*100).toFixed(1)}%</div>
                  </div>`).join('')}
            </div>
          </div>` : ''}

        <!-- Alerts generated -->
        ${r.alerts_generated?.length ? `
          <div class="card" style="border-color:rgba(239,68,68,0.3);background:rgba(239,68,68,0.04)">
            <div class="card-body" style="padding:14px 16px">
              <div class="fw-600 text-attack mb-8" style="font-size:13px">🚨 ${r.alerts_generated.length} Alert${r.alerts_generated.length>1?'s':''} Generated</div>
              ${r.alerts_generated.map(a => `<div style="font-size:12px;color:var(--text-secondary);margin-bottom:4px">• ${a.title}</div>`).join('')}
            </div>
          </div>` : ''}

        <div class="mt-16 text-right" style="font-size:11px;color:var(--text-muted)">Activity ID: #${r.activity_id} &nbsp;|&nbsp; Model: v${r.model_version || '?'}</div>
      </div>
    </div>
  `;

  document.getElementById('resultArea').innerHTML = html;
}

window.clearAnalyzeForm = function() {
  document.getElementById('analyzeForm').reset();
  document.getElementById('resultArea').innerHTML = `<div class="card"><div class="card-body">${OmniShield.emptyState('🔬', 'No analysis yet', 'Fill in the form and click Analyze Activity.')}</div></div>`;
}
