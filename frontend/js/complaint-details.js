/* ============================================================
   Complaint Details — JavaScript
   ============================================================ */

document.addEventListener('DOMContentLoaded', async () => {
  const params = new URLSearchParams(window.location.search);
  const id = params.get('id');

  if (!id) {
    renderError('No complaint ID provided.');
    return;
  }

  await loadComplaint(id);
});

async function loadComplaint(id) {
  const container = document.getElementById('details-container');

  try {
    const res = await API.getComplaint(id);
    if (!res.success) throw new Error(res.error || 'Complaint not found');
    renderComplaint(res.data);
  } catch (err) {
    renderError(err.message);
  }
}

function renderComplaint(c) {
  const container = document.getElementById('details-container');
  document.title = `Complaint #${c.id.substring(0, 8).toUpperCase()} — CivicIQ`;

  const priority = c.priorityScore || 0;
  const priorityColor = priority >= 70 ? '#dc2626' : priority >= 40 ? '#d97706' : '#16a34a';
  const priorityLabel = priority >= 70 ? 'HIGH' : priority >= 40 ? 'MEDIUM' : 'LOW';

  container.innerHTML = `
    <div class="details-layout">
      <!-- ── Main Column ── -->
      <div>
        <!-- Header -->
        <div class="details-header">
          <div>
            <div class="details-id">🆔 ${c.id}</div>
            <h1 class="details-title">${getCategoryIcon(c.category)} ${c.category ? c.category.replace(/_/g,' ') : 'Civic Complaint'}</h1>
          </div>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px">
            ${renderStatusBadge(c.status)}
            ${priority > 0 ? renderPriorityBadge(priority) : ''}
          </div>
        </div>

        <!-- AI Summary -->
        ${c.summary ? `
          <div class="ai-summary-card">
            <div class="ai-summary-header">🤖 AI Analysis Summary</div>
            <p class="ai-summary-text">${escapeHtml(c.summary)}</p>
          </div>
        ` : ''}

        <!-- Image -->
        <div class="complaint-image-section">
          ${c.imageUrl
            ? `<img src="${c.imageUrl}" alt="Complaint image for ${c.category || 'civic issue'}" loading="lazy" />`
            : `<div class="no-image-placeholder">📷 No image submitted</div>`
          }
        </div>

        <!-- Description -->
        <div class="card mb-8">
          <div class="card-header"><span class="card-title">📝 Complaint Description</span></div>
          <div class="card-body">
            <p style="font-size:var(--font-size-sm);color:var(--color-gray-700);line-height:var(--line-height-relaxed)">${escapeHtml(c.description)}</p>
          </div>
        </div>

        <!-- Info Grid -->
        <div class="card mb-8">
          <div class="card-header"><span class="card-title">📋 Complaint Information</span></div>
          <div class="card-body">
            <div class="info-grid">
              <div class="info-item">
                <span class="info-item-label">Department</span>
                <span class="info-item-value">${c.department || '—'}</span>
              </div>
              <div class="info-item">
                <span class="info-item-label">Category</span>
                <span class="info-item-value">${getCategoryIcon(c.category)} ${c.category ? c.category.replace(/_/g,' ') : '—'}</span>
              </div>
              <div class="info-item">
                <span class="info-item-label">Est. Cost</span>
                <span class="info-item-value">${formatCurrency(c.estimatedCost)}</span>
              </div>
              <div class="info-item">
                <span class="info-item-label">Est. Duration</span>
                <span class="info-item-value">${c.estimatedDuration || '—'}</span>
              </div>
              <div class="info-item">
                <span class="info-item-label">Submitted</span>
                <span class="info-item-value">${formatDate(c.createdAt)}</span>
              </div>
              <div class="info-item">
                <span class="info-item-label">Last Updated</span>
                <span class="info-item-value">${formatDate(c.updatedAt)}</span>
              </div>
              <div class="info-item">
                <span class="info-item-label">Reporter</span>
                <span class="info-item-value">${escapeHtml(c.reporterName)}</span>
              </div>
              <div class="info-item">
                <span class="info-item-label">Duplicate Report</span>
                <span class="info-item-value">${c.isDuplicate ? '⚠️ Yes' : '✅ No'}</span>
              </div>
              ${c.reporterCount ? `
              <div class="info-item">
                <span class="info-item-label">Total Reporters</span>
                <span class="info-item-value">👥 ${c.reporterCount} citizens</span>
              </div>` : ''}
              <div class="info-item">
                <span class="info-item-label">Coordinates</span>
                <span class="info-item-value" style="font-family:monospace;font-size:11px">${c.latitude?.toFixed(5)}, ${c.longitude?.toFixed(5)}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Location Map -->
        <div class="card">
          <div class="card-header"><span class="card-title">📍 Location</span>
            <a href="https://maps.google.com/?q=${c.latitude},${c.longitude}" target="_blank" rel="noopener" class="btn btn-ghost btn-sm">Open in Maps ↗</a>
          </div>
          <div class="card-body" style="padding:0">
            <div class="detail-map" id="detail-map-container">
              <div class="map-placeholder" id="map-placeholder">
                <div class="map-placeholder-content">
                  🗺️ Map requires Google Maps API key<br>
                  <a href="https://maps.google.com/?q=${c.latitude},${c.longitude}" target="_blank" style="color:var(--color-primary)">View on Google Maps ↗</a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Sidebar ── -->
      <div class="sidebar-section">

        <!-- Priority Score Card -->
        <div class="card mb-4">
          <div class="card-header"><span class="card-title">⚡ Priority Score</span></div>
          <div class="card-body priority-gauge-card">
            <div class="gauge-circle" style="background:${priorityColor}22;border:4px solid ${priorityColor}">
              <span class="gauge-value" style="color:${priorityColor}">${priority.toFixed(1)}</span>
              <span class="gauge-label" style="color:${priorityColor}">${priorityLabel}</span>
            </div>
            <div class="scores-grid">
              <div class="score-item">
                <div class="score-value">${(c.severityScore * 100).toFixed(0)}%</div>
                <div class="score-label">Severity</div>
              </div>
              <div class="score-item">
                <div class="score-value">${(c.communityValidation * 100).toFixed(0)}%</div>
                <div class="score-label">Validation</div>
              </div>
              <div class="score-item">
                <div class="score-value">${(c.reporterCredibility * 100).toFixed(0)}%</div>
                <div class="score-label">Credibility</div>
              </div>
              <div class="score-item">
                <div class="score-value">${c.reporterCount || 1}</div>
                <div class="score-label">Reports</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Quick Actions Card -->
        <div class="card mb-4">
          <div class="card-header"><span class="card-title">🔧 Quick Actions</span></div>
          <div class="card-body">
            <div class="detail-action-row">
              <button class="btn btn-primary" onclick="copyToClipboard('${c.id}')">📋 Copy Complaint ID</button>
              <a href="https://maps.google.com/?q=${c.latitude},${c.longitude}" target="_blank" class="btn btn-outline">📍 Open Location</a>
              ${c.status === 'VALID' ? `<button class="btn btn-success" onclick="quickAssign('${c.id}')">👷 Assign Worker</button>` : ''}
            </div>
          </div>
        </div>

        <!-- Status History -->
        <div class="card">
          <div class="card-header"><span class="card-title">📜 Current Status</span></div>
          <div class="card-body">
            <div style="text-align:center;padding:var(--space-4)">
              <div style="font-size:3rem;margin-bottom:var(--space-2)">${getStatusEmoji(c.status)}</div>
              ${renderStatusBadge(c.status)}
              <p class="text-sm text-muted" style="margin-top:var(--space-3)">${getStatusDescription(c.status)}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  // Init map if coordinates available
  if (c.latitude && c.longitude) {
    const placeholder = document.getElementById('map-placeholder');
    if (window.CIVIC_CONFIG && window.CIVIC_CONFIG.GOOGLE_MAPS_API_KEY) {
      if (placeholder) placeholder.style.display = 'none';
      MapsHelper.initMap('detail-map-container', null, { lat: c.latitude, lng: c.longitude });
      setTimeout(() => MapsHelper.setCenter(c.latitude, c.longitude, 15), 500);
    }
  }
}

function quickAssign(id) {
  window.location.href = `officer.html`;
}

function getStatusEmoji(status) {
  const map = { PROCESSING: '⏳', VALID: '✅', IN_PROGRESS: '🔧', RESOLVED: '✔️', REJECTED: '❌' };
  return map[status] || '•';
}

function getStatusDescription(status) {
  const map = {
    PROCESSING: 'AI is currently analyzing this complaint.',
    VALID: 'Complaint verified and ready for assignment.',
    IN_PROGRESS: 'A worker has been assigned and work is underway.',
    RESOLVED: 'This issue has been successfully resolved.',
    REJECTED: 'Complaint was reviewed and rejected.',
  };
  return map[status] || 'Status unknown.';
}

function renderError(msg) {
  const container = document.getElementById('details-container');
  container.innerHTML = `
    <div class="empty-state" style="padding-top:var(--space-16)">
      <div class="empty-state-icon">⚠️</div>
      <div class="empty-state-title">Could not load complaint</div>
      <div class="empty-state-desc">${escapeHtml(msg)}</div>
      <a href="citizen.html?tab=track" class="btn btn-primary" style="margin-top:var(--space-6)">← Back to Complaints</a>
    </div>`;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}
