/**
 * OmniShield AI — Datasets Page
 */
OmniShield.registerPage('datasets', async (container) => {
  container.innerHTML = `
    <div class="grid-2" style="align-items:start">
      <!-- Upload -->
      <div>
        <div class="card mb-20">
          <div class="card-header"><span class="card-title"><span class="card-title-icon">📁</span> Upload Dataset</span></div>
          <div class="card-body">
            <div class="upload-zone" id="uploadZone" onclick="document.getElementById('fileInput').click()">
              <div class="upload-icon">📊</div>
              <div class="upload-label">Drop CSV file here or click to browse</div>
              <div class="upload-sub">Max 50MB · CSV format only</div>
              <button class="btn btn-secondary mt-8" type="button" onclick="event.stopPropagation(); document.getElementById('fileInput').click()">Browse Files</button>
            </div>
            <input type="file" id="fileInput" accept=".csv" style="display:none" onchange="handleFileSelect(event)">
            <div id="uploadStatus" class="mt-16"></div>
          </div>
        </div>

        <!-- Dataset inspection + training form -->
        <div id="datasetInspect" class="hidden"></div>
      </div>

      <!-- Dataset list -->
      <div class="card">
        <div class="card-header"><span class="card-title"><span class="card-title-icon">🗄️</span> Uploaded Datasets</span></div>
        <div id="datasetList"><div style="padding:40px;text-align:center"><div class="spinner"></div></div></div>
      </div>
    </div>
  `;

  setupUploadZone();
  loadDatasets();
});

function setupUploadZone() {
  const zone = document.getElementById('uploadZone');
  if (!zone) return;
  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  });
}

function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) uploadFile(file);
}

async function uploadFile(file) {
  const status = document.getElementById('uploadStatus');
  status.innerHTML = `<div class="d-flex gap-12" style="padding:12px;background:var(--bg-glass);border-radius:var(--radius-md)">
    <div class="spinner" style="width:20px;height:20px;border-width:2px;flex-shrink:0"></div>
    <span class="text-secondary">Uploading ${file.name}…</span>
  </div>`;

  const fd = new FormData();
  fd.append('file', file);
  const res = await OmniShield.api.upload('/dataset/upload', fd);

  if (!res.ok) {
    status.innerHTML = OmniShield.errorState(res.data?.error?.message || 'Upload failed');
    return;
  }

  const d = res.data.data;
  status.innerHTML = `<div class="toast success" style="position:static;animation:none">✅ Uploaded: ${d.filename} (${d.row_count.toLocaleString()} rows, ${d.column_count} columns)</div>`;
  renderDatasetInspect(d);
  loadDatasets();
}

function renderDatasetInspect(d) {
  const el = document.getElementById('datasetInspect');
  el.classList.remove('hidden');
  el.innerHTML = `
    <div class="card">
      <div class="card-header"><span class="card-title"><span class="card-title-icon">🔬</span> Dataset Inspection</span></div>
      <div class="card-body">
        <div class="grid-2 mb-16">
          <div class="result-metric"><div class="result-metric-label">Rows</div><div class="fw-700">${d.row_count.toLocaleString()}</div></div>
          <div class="result-metric"><div class="result-metric-label">Columns</div><div class="fw-700">${d.column_count}</div></div>
        </div>
        <div class="mb-16">
          <div class="form-label">Columns</div>
          <div>${d.columns.map(c => `<span class="tag mono">${c}</span>`).join('')}</div>
        </div>
        <div class="form-group">
          <label class="form-label" for="targetColSelect">Select Target Column *</label>
          <select class="form-control" id="targetColSelect">
            <option value="">— Select target column —</option>
            ${d.columns.map(c => `<option value="${c}" ${c.toLowerCase().includes('label') || c.toLowerCase().includes('class') || c.toLowerCase().includes('attack') ? 'selected' : ''}>${c}</option>`).join('')}
          </select>
        </div>
        <button class="btn btn-primary" onclick="startTraining(${d.dataset_id})" id="trainBtn">
          🤖 Start Training
        </button>
        <div id="trainStatus" class="mt-16"></div>
      </div>
    </div>
  `;
}

async function startTraining(datasetId) {
  const target = document.getElementById('targetColSelect')?.value?.trim();
  if (!target) { OmniShield.toast('Please select a target column', 'warning'); return; }

  const btn = document.getElementById('trainBtn');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner" style="width:16px;height:16px;border-width:2px"></div> Training…';

  const res = await OmniShield.api.post('/dataset/train', { dataset_id: datasetId, target_column: target });

  if (!res.ok) {
    btn.disabled = false;
    btn.innerHTML = '🤖 Start Training';
    OmniShield.toast(res.data?.error?.message || 'Training failed to start', 'error');
    document.getElementById('trainStatus').innerHTML = OmniShield.errorState(res.data?.error?.message || 'Failed to start training');
    return;
  }

  const d = res.data.data;
  document.getElementById('trainStatus').innerHTML = `
    <div class="card" style="border-color:rgba(0,212,255,0.3)">
      <div class="card-body" style="padding:14px 16px">
        <div class="fw-600 text-accent mb-8">🔄 Training in progress…</div>
        <div class="text-secondary" style="font-size:13px">Model Run ID: #${d.model_run_id} &nbsp;|&nbsp; Version: ${d.version}</div>
        <div class="text-secondary" style="font-size:13px;margin-top:4px">Check the ML Models page for progress and results.</div>
        <div class="mt-12">
          <button class="btn btn-secondary btn-sm" onclick="pollTrainingStatus(${d.model_run_id})">🔄 Check Status</button>
          <button class="btn btn-secondary btn-sm" style="margin-left:8px" onclick="OmniShield.navigate('models')">📊 View Models</button>
        </div>
      </div>
    </div>`;

  OmniShield.toast('Training started', 'success');
  pollTrainingStatus(d.model_run_id);
  loadDatasets();
}

async function pollTrainingStatus(runId) {
  const res = await OmniShield.api.get('/model/status/' + runId);
  if (!res.ok) return;
  const run = res.data.data;
  if (run.status === 'COMPLETED') {
    OmniShield.toast('Model training complete! 🎉', 'success');
    OmniShield.refreshModelStatus();
    loadDatasets();
    document.getElementById('trainBtn').disabled = false;
    document.getElementById('trainBtn').innerHTML = '🤖 Start Training';
    const statusEl = document.getElementById('trainStatus');
    if (statusEl) statusEl.innerHTML += `<div class="toast success" style="position:static;animation:none;margin-top:8px">✅ Training completed. Accuracy: ${(run.accuracy*100).toFixed(1)}% | F1: ${(run.f1_score*100).toFixed(1)}%</div>`;
  } else if (run.status === 'FAILED') {
    OmniShield.toast('Training failed: ' + (run.error_message || 'Unknown error'), 'error');
    document.getElementById('trainBtn').disabled = false;
    document.getElementById('trainBtn').innerHTML = '🤖 Start Training';
  } else {
    // Still training, poll again
    setTimeout(() => pollTrainingStatus(runId), 3000);
  }
}

async function loadDatasets() {
  const list = document.getElementById('datasetList');
  if (!list) return;
  const res = await OmniShield.api.get('/datasets');
  if (!res.ok) { list.innerHTML = OmniShield.errorState('Failed to load datasets'); return; }

  const datasets = res.data.data.datasets;
  if (datasets.length === 0) {
    list.innerHTML = OmniShield.emptyState('🗄️', 'No datasets uploaded', 'Upload a CSV dataset to get started.');
    return;
  }

  const statusColors = {
    UPLOADED:'var(--accent-cyan)', VALIDATED:'var(--color-normal)', INVALID:'var(--color-attack)'
  };
  const trainColors = {
    PENDING:'var(--text-muted)', TRAINING:'var(--accent-cyan)', COMPLETED:'var(--color-normal)', FAILED:'var(--color-attack)'
  };

  list.innerHTML = `<div class="table-responsive"><table class="data-table">
    <thead>
      <tr>
        <th style="width: 50px;">ID</th>
        <th>Dataset Filename</th>
        <th style="text-align: right;">Rows</th>
        <th style="text-align: right;">Cols</th>
        <th>Target Field</th>
        <th>Status</th>
        <th>Training</th>
      </tr>
    </thead>
    <tbody>
      ${datasets.map(d => `
        <tr>
          <td class="mono text-muted">#${d.id}</td>
          <td class="fw-600 cell-truncate" title="${d.filename}">${d.filename}</td>
          <td style="text-align: right;" class="mono">${d.row_count?.toLocaleString() ?? '—'}</td>
          <td style="text-align: right;" class="mono">${d.column_count ?? '—'}</td>
          <td class="mono cell-truncate" style="color:var(--accent-cyan);">${d.target_column || '—'}</td>
          <td><span class="badge" style="background:rgba(0,240,255,0.08); color:${statusColors[d.status]||'#fff'}; border:1px solid rgba(0,240,255,0.2);">${d.status}</span></td>
          <td><span class="badge" style="background:rgba(255,255,255,0.04); color:${trainColors[d.training_status]||'#fff'}; border:1px solid rgba(255,255,255,0.1);">${d.training_status || '—'}</span></td>
        </tr>`).join('')}
    </tbody></table></div>`;
}
