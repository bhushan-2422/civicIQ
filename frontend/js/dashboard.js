/* ============================================================
   Dashboard — JavaScript
   Handles hotspot map and predictive maintenance views.
   ============================================================ */

let currentMapMode = 'heatmap';
let hotspotData = [];

document.addEventListener('DOMContentLoaded', async () => {
  // Auto-switch to hotspots if URL has #hotspots
  if (window.location.hash === '#hotspots') {
    switchDashTab('hotspot');
  }

  await loadHotspots();
});


// ── Tab Switching ─────────────────────────────────────────
function switchDashTab(tab) {
  ['hotspot', 'predictive'].forEach(t => {
    document.getElementById(`tab-${t}`).classList.toggle('active', t === tab);
    document.getElementById(`tab-${t}`).setAttribute('aria-selected', t === tab);
    document.getElementById(`panel-${t}`).classList.toggle('hidden', t !== tab);
  });

  if (tab === 'predictive') loadPredictions();
}


// ── Hotspot Map ───────────────────────────────────────────
async function loadHotspots() {
  try {
    const res = await API.getHotspots();
    hotspotData = res.data || [];

    const countEl = document.getElementById('hotspot-count');
    if (countEl) countEl.textContent = `${hotspotData.length} complaints plotted`;

    renderHotspotSummary(hotspotData);
    initHotspotMap();
  } catch (err) {
    console.error('Failed to load hotspot data:', err);
  }
}

function initHotspotMap() {
  if (!hotspotData.length) return;
  if (currentMapMode === 'heatmap') {
    const points = hotspotData.map(h => ({
      lat: h.lat, lng: h.lng,
      weight: Math.max(0.1, (h.priority || 0) / 100),
      priority: h.priority,
      category: h.category,
      status: h.status,
    }));
    MapsHelper.initHeatmap('hotspot-map', points);
  } else {
    MapsHelper.initMarkersMap('hotspot-map', hotspotData);
  }

  const placeholder = document.getElementById('hotspot-map-placeholder');
  if (placeholder && window.CIVIC_CONFIG && window.CIVIC_CONFIG.GOOGLE_MAPS_API_KEY) {
    placeholder.style.display = 'none';
  }
}

function setMapMode(mode) {
  currentMapMode = mode;
  document.getElementById('btn-heatmap').className = `btn btn-sm ${mode === 'heatmap' ? 'btn-primary' : 'btn-ghost'}`;
  document.getElementById('btn-markers').className = `btn btn-sm ${mode === 'markers' ? 'btn-primary' : 'btn-ghost'}`;

  // Re-init map in new mode (clear existing map)
  const mapEl = document.getElementById('hotspot-map');
  mapEl.innerHTML = `<div class="map-placeholder" id="hotspot-map-placeholder">
    <div class="map-placeholder-content">🗺️ Loading map...</div>
  </div>`;
  initHotspotMap();
}

function renderHotspotSummary(data) {
  const container = document.getElementById('hotspot-summary-content');
  if (!container) return;

  if (!data.length) {
    container.innerHTML = '<div class="text-muted text-center text-sm">No hotspot data available</div>';
    return;
  }

  const high = data.filter(d => d.priority >= 70).length;
  const medium = data.filter(d => d.priority >= 40 && d.priority < 70).length;
  const low = data.filter(d => d.priority < 40).length;

  // Category counts
  const catCounts = {};
  data.forEach(d => {
    if (d.category) catCounts[d.category] = (catCounts[d.category] || 0) + 1;
  });
  const topCats = Object.entries(catCounts).sort((a, b) => b[1] - a[1]).slice(0, 4);

  container.innerHTML = `
    <div class="hotspot-summary-list">
      <div class="hotspot-summary-item">
        <span>🔴 High Priority (≥70)</span>
        <strong style="color:#dc2626">${high}</strong>
      </div>
      <div class="hotspot-summary-item">
        <span>🟡 Medium Priority (40–70)</span>
        <strong style="color:#d97706">${medium}</strong>
      </div>
      <div class="hotspot-summary-item">
        <span>🟢 Low Priority (&lt;40)</span>
        <strong style="color:#16a34a">${low}</strong>
      </div>
      ${topCats.map(([cat, count]) => `
        <div class="hotspot-summary-item">
          <span>${getCategoryIcon(cat)} ${cat.replace(/_/g,' ')}</span>
          <strong>${count}</strong>
        </div>`).join('')}
    </div>`;
}


// ── Predictive Maintenance ────────────────────────────────
async function loadPredictions() {
  const container = document.getElementById('predictions-grid');
  if (!container) return;

  container.innerHTML = `<div class="loading-container" style="grid-column:1/-1">
    <div class="loading-spinner"></div>
    <span>Analyzing complaint patterns...</span>
  </div>`;

  try {
    const res = await API.getPredictions();
    const predictions = res.data || [];

    if (!predictions.length) {
      container.innerHTML = `
        <div class="empty-state" style="grid-column:1/-1">
          <div class="empty-state-icon">🔮</div>
          <div class="empty-state-title">No Predictions Available</div>
          <div class="empty-state-desc">Submit more complaints to generate pattern-based predictions. At least 2 complaints per category are required.</div>
        </div>`;
      return;
    }

    container.innerHTML = predictions.map(p => {
      const headerBg = p.riskColor || '#1a3c6e';
      const probPct = Math.round(p.probability * 100);

      return `
        <div class="prediction-card" style="border-color:${headerBg}40">
          <div class="prediction-card-header" style="background:${headerBg}">
            <div class="prediction-category">
              ${getCategoryIcon(p.category)}
              ${p.category.replace(/_/g,' ')}
            </div>
            <span class="risk-badge">${p.riskLevel} RISK</span>
          </div>
          <div class="prediction-card-body">
            <div class="prediction-meta">
              <div class="prediction-meta-item">
                <span class="prediction-meta-value">${p.complaintCount}</span>
                <span class="prediction-meta-label">Complaints (90d)</span>
              </div>
              <div class="prediction-meta-item">
                <span class="prediction-meta-value">${p.averagePriority.toFixed(0)}/100</span>
                <span class="prediction-meta-label">Avg Priority</span>
              </div>
              <div class="prediction-meta-item">
                <span class="prediction-meta-value">${probPct}%</span>
                <span class="prediction-meta-label">Probability</span>
              </div>
            </div>
            <div class="probability-bar-wrapper">
              <div class="probability-label">
                <span>Failure Probability</span>
                <span style="color:${headerBg}">${probPct}%</span>
              </div>
              <div class="probability-track">
                <div class="probability-fill" style="width:${probPct}%;background:${headerBg}"></div>
              </div>
            </div>
            <div class="prediction-recommendation">
              💡 ${escapeHtml(p.recommendation)}
            </div>
            ${p.centerLat && p.centerLng ? `
              <div style="margin-top:var(--space-3)">
                <a href="https://maps.google.com/?q=${p.centerLat},${p.centerLng}" target="_blank" class="btn btn-ghost btn-sm btn-full">
                  📍 View Area on Map
                </a>
              </div>` : ''}
          </div>
        </div>`;
    }).join('');
  } catch (err) {
    container.innerHTML = `
      <div class="empty-state" style="grid-column:1/-1">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-title">Failed to load predictions</div>
        <div class="empty-state-desc">${err.message}</div>
      </div>`;
  }
}


function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}
