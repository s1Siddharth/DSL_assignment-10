/**
 * OmniShield AI — ML Models Page
 */
OmniShield.registerPage('models', async (container) => {
  container.innerHTML = `<div style="padding:60px;text-align:center"><div class="spinner"></div></div>`;

  const [perfRes, listRes] = await Promise.all([
    OmniShield.api.get('/model/performance'),
    OmniShield.api.get('/models'),
  ]);

  if (!perfRes.ok) { container.innerHTML = OmniShield.errorState('Failed to load model data'); return; }

  const d = perfRes.data.data;
  const models = listRes.ok ? listRes.data.data.models : [];

  if (!d.has_model) {
    container.innerHTML = OmniShield.emptyState('🤖', 'No trained models yet',
      'Upload a dataset and train a model to see performance metrics here.',
      `<button class="btn btn-primary mt-16" onclick="OmniShield.navigate('datasets')">🗄️ Upload Dataset</button>`);
    return;
  }

  container.innerHTML = `
    <!-- Model info header -->
    <div class="card mb-20">
      <div class="card-body">
        <div style="display:flex; align-items:center; gap:20px; flex-wrap:wrap;">
          <span style="font-size:42px">🤖</span>
          <div style="flex:1">
            <div style="font-size:22px; font-weight:700; color:#fff;">${d.model_name} <span class="badge badge-new" style="background:rgba(0,240,255,0.15); color:var(--accent-cyan);">v${d.version}</span></div>
            <div class="text-secondary mt-8" style="font-size:13px; font-family:var(--font-mono);">
              Trained: ${OmniShield.formatDate(d.created_at)} &nbsp;|&nbsp;
              Features: ${(d.feature_names||[]).length} &nbsp;|&nbsp;
              Classes: ${(d.classes||[]).map(c=>c.toUpperCase()).join(', ')} &nbsp;|&nbsp;
              Train: ${d.training_samples?.toLocaleString()}, Test: ${d.testing_samples?.toLocaleString()}
            </div>
          </div>
          <div>${d.status === 'COMPLETED' ? '<span class="badge badge-low" style="font-size:14px; padding:6px 14px;">✅ Active Model</span>' : ''}</div>
        </div>
      </div>
    </div>

    <!-- Metrics row -->
    <div class="stats-grid mb-20">
      ${metricCard('Accuracy', d.accuracy, '#00f0ff')}
      ${metricCard('Precision', d.precision, '#8b5cf6')}
      ${metricCard('Recall', d.recall, '#10b981')}
      ${metricCard('F1 Score', d.f1_score, '#f59e0b')}
    </div>

    <!-- Charts row -->
    <div class="grid-2 mb-20">
      <!-- Feature Importance -->
      <div class="card">
        <div class="card-header"><span class="card-title"><span class="card-title-icon">📊</span> Feature Importance</span></div>
        <div class="card-body" id="featureImportanceSection">
          ${renderFeatureImportance(d.feature_importance)}
        </div>
      </div>

      <!-- Confusion Matrix -->
      <div class="card">
        <div class="card-header"><span class="card-title"><span class="card-title-icon">🎯</span> Confusion Matrix</span></div>
        <div class="card-body">
          ${renderConfusionMatrix(d.confusion_matrix, d.classes)}
        </div>
      </div>
    </div>

    <!-- Per-class metrics -->
    ${d.class_metrics ? `
      <div class="card mb-20">
        <div class="card-header"><span class="card-title"><span class="card-title-icon">📋</span> Per-Class Metrics Breakdown</span></div>
        <div class="table-responsive">
          <table class="data-table">
            <thead><tr><th>Target Class</th><th style="text-align:right;">Precision</th><th style="text-align:right;">Recall</th><th style="text-align:right;">F1 Score</th><th style="text-align:right;">Support</th></tr></thead>
            <tbody>
              ${Object.entries(d.class_metrics).map(([cls, m]) => `
                <tr>
                  <td class="fw-600 mono" style="color:var(--accent-cyan);">${cls.toUpperCase()}</td>
                  <td style="text-align:right;" class="mono">${(m.precision*100).toFixed(1)}%</td>
                  <td style="text-align:right;" class="mono">${(m.recall*100).toFixed(1)}%</td>
                  <td style="text-align:right;" class="mono">${(m.f1_score*100).toFixed(1)}%</td>
                  <td style="text-align:right;" class="mono">${m.support?.toLocaleString()}</td>
                </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>` : ''}

    <!-- All model runs -->
    ${models.length > 1 ? `
      <div class="card">
        <div class="card-header"><span class="card-title"><span class="card-title-icon">🗃️</span> Model Training History</span></div>
        <div class="table-responsive">
          <table class="data-table">
            <thead><tr><th>Version</th><th>Status</th><th>Accuracy</th><th>F1 Score</th><th>Samples</th><th>Training Date</th></tr></thead>
            <tbody>
              ${models.map(r => `
                <tr>
                  <td class="mono fw-600" style="color:var(--accent-cyan);">v${r.version}</td>
                  <td>${r.status === 'COMPLETED' ? '<span class="badge badge-low">✅ Active</span>' : r.status === 'FAILED' ? '<span class="badge badge-attack">❌ Failed</span>' : '<span class="badge badge-new">⏳ Training</span>'}</td>
                  <td class="mono">${r.accuracy !== null ? (r.accuracy*100).toFixed(1)+'%' : '—'}</td>
                  <td class="mono">${r.f1_score !== null ? (r.f1_score*100).toFixed(1)+'%' : '—'}</td>
                  <td class="mono">${r.training_samples?.toLocaleString() ?? '—'}</td>
                  <td class="text-muted mono">${OmniShield.formatDate(r.created_at)}</td>
                </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>` : ''}
  `;
});

function metricCard(label, value, color) {
  const pct = value !== null ? (value * 100).toFixed(2) + '%' : 'N/A';
  return `<div class="stat-card">
    <div class="stat-label">${label}</div>
    <div class="stat-value" style="color:${color}; font-size:26px;">${pct}</div>
  </div>`;
}

function renderFeatureImportance(featureImportance) {
  if (!featureImportance || featureImportance.length === 0) {
    return OmniShield.emptyState('📊', 'No feature importance data', 'Feature importance is available for tree-based models.');
  }
  const top = featureImportance.slice(0, 10);
  const max = top[0]?.importance || 1;

  return `<div class="feature-list">
    ${top.map(f => {
      const pct = ((f.importance / max) * 100).toFixed(1);
      const valPct = (f.importance * 100).toFixed(2);
      return `<div class="feature-row">
        <div class="feature-header">
          <span>${f.feature}</span>
          <span style="color:var(--accent-cyan); font-weight:600;">${valPct}%</span>
        </div>
        <div class="feature-bar-bg">
          <div class="feature-bar-fill" style="width:${pct}%"></div>
        </div>
      </div>`;
    }).join('')}
  </div>`;
}

function renderConfusionMatrix(matrix, classes) {
  if (!matrix || !classes || classes.length === 0) {
    return OmniShield.emptyState('🎯', 'No confusion matrix data', 'Matrix will appear after training.');
  }
  const flat = matrix.flat();
  const maxVal = Math.max(...flat, 1);
  const totalPredictions = flat.reduce((a, b) => a + b, 0);

  function cellBg(val, isDiag) {
    if (val === 0) return 'rgba(255,255,255,0.02)';
    const alpha = Math.max(0.08, (val / maxVal) * 0.6);
    if (isDiag) return `rgba(0, 240, 255, ${alpha})`;
    return `rgba(239, 68, 68, ${alpha * 0.7})`;
  }

  function cellColor(val, isDiag) {
    if (val === 0) return 'var(--text-muted)';
    if (isDiag) return '#00f0ff';
    return '#fca5a5';
  }

  return `
    <div style="font-size:11px; color:var(--text-secondary); margin-bottom:10px; text-align:center; text-transform:uppercase; letter-spacing:.06em">
      Actual (rows) vs Predicted (cols)  •  ${totalPredictions.toLocaleString()} samples
    </div>
    <div class="cm-container">
      <table class="cm-table">
        <thead>
          <tr>
            <th style="background:rgba(0,240,255,0.1); color:var(--accent-cyan);">↓ Actual \ Pred →</th>
            ${classes.map(c => `<th style="color:var(--accent-cyan);">${c.toUpperCase()}</th>`).join('')}
          </tr>
        </thead>
        <tbody>
          ${matrix.map((row, i) => {
            const rowTotal = row.reduce((a, b) => a + b, 0);
            return `
              <tr>
                <th style="text-align:right; color:var(--accent-purple); font-weight:700;">${classes[i].toUpperCase()}</th>
                ${row.map((val, j) => {
                  const pct = rowTotal > 0 ? ((val / rowTotal) * 100).toFixed(0) : 0;
                  const isDiag = i === j;
                  return `<td style="background:${cellBg(val, isDiag)}; color:${cellColor(val, isDiag)}; font-weight:${isDiag?'700':'400'};" title="${val} / ${rowTotal} (${pct}%)">
                    ${val.toLocaleString()}
                    ${val > 0 ? `<div style="font-size:9px; opacity:0.7; margin-top:2px">${pct}%</div>` : ''}
                  </td>`;
                }).join('')}
              </tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>`;
}
