/* ============================================================
   Citizen Portal — JavaScript
   ============================================================ */

// ── State ──────────────────────────────────────────────────
const state = {
  selectedLat: null,
  selectedLng: null,
  page: 1,
  totalPages: 1,
  trackFilters: { search: '', status: '', sort: 'createdAt' },
};

// ── DOM Ready ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initComplaintForm();
  initImageUpload();
  initLocationControls();
  initTrackFilters();
  initMap();

  // Auto-switch to track if URL has ?tab=track
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('tab') === 'track') switchTab('track');
});


// ── Tab Switching ─────────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.id === `tab-${tab}`);
    btn.setAttribute('aria-selected', btn.id === `tab-${tab}` ? 'true' : 'false');
  });
  document.getElementById('panel-report').classList.toggle('hidden', tab !== 'report');
  document.getElementById('panel-track').classList.toggle('hidden', tab !== 'track');
  document.getElementById('success-banner').classList.add('hidden');

  if (tab === 'track') {
    state.page = 1;
    loadTrackComplaints();
  }
}

function initTabs() {
  // Nothing extra needed — tab-btn uses onclick
}


// ── Map Init ──────────────────────────────────────────────
function initMap() {
  MapsHelper.initMap('location-map', ({ lat, lng }) => {
    state.selectedLat = lat;
    state.selectedLng = lng;
    document.getElementById('latitude').value = lat.toFixed(7);
    document.getElementById('longitude').value = lng.toFixed(7);
    _clearFieldError('latitude');
  });
}


// ── Location Controls ─────────────────────────────────────
function initLocationControls() {
  const btn = document.getElementById('get-location-btn');
  if (!btn) return;

  btn.addEventListener('click', () => {
    if (!navigator.geolocation) {
      Toast.error('Geolocation is not supported by your browser.');
      return;
    }

    setLoading(btn, true);
    const status = document.getElementById('location-status');
    status.textContent = '📍 Getting your location...';
    status.classList.remove('hidden');

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        state.selectedLat = lat;
        state.selectedLng = lng;
        document.getElementById('latitude').value = lat.toFixed(7);
        document.getElementById('longitude').value = lng.toFixed(7);
        MapsHelper.setCenter(lat, lng);
        status.textContent = `✅ Location set: ${lat.toFixed(5)}, ${lng.toFixed(5)}`;
        setLoading(btn, false);
        _clearFieldError('latitude');
      },
      (err) => {
        status.textContent = `❌ Could not get location: ${err.message}`;
        setLoading(btn, false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  });
}


// ── Image Upload ──────────────────────────────────────────
function initImageUpload() {
  const dropZone = document.getElementById('image-drop-zone');
  const input = document.getElementById('image-upload');
  const preview = document.getElementById('image-preview');
  const placeholder = document.getElementById('upload-placeholder');
  const previewImg = document.getElementById('preview-img');
  const removeBtn = document.getElementById('remove-image-btn');

  if (!dropZone || !input) return;

  input.addEventListener('change', () => {
    const file = input.files[0];
    if (file) _showPreview(file);
  });

  // Drag and drop
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      _showPreview(file);
    }
  });

  removeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    input.value = '';
    previewImg.src = '';
    preview.classList.add('hidden');
    placeholder.classList.remove('hidden');
  });

  function _showPreview(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      previewImg.src = e.target.result;
      preview.classList.remove('hidden');
      placeholder.classList.add('hidden');
    };
    reader.readAsDataURL(file);
  }
}


// ── Form Submission ───────────────────────────────────────
function initComplaintForm() {
  const form = document.getElementById('complaint-form');
  if (!form) return;

  // Character counter
  const desc = document.getElementById('description');
  const counter = document.getElementById('char-count');
  if (desc && counter) {
    desc.addEventListener('input', () => {
      const len = desc.value.length;
      counter.textContent = len;
      if (len > 900) counter.style.color = 'var(--color-danger)';
      else counter.style.color = '';
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!_validateForm()) return;

    const submitBtn = document.getElementById('submit-btn');
    setLoading(submitBtn, true);

    const formData = new FormData(form);
    formData.set('latitude', state.selectedLat);
    formData.set('longitude', state.selectedLng);

    try {
      const res = await API.submitComplaint(formData);

      if (res.success) {
        document.getElementById('success-complaint-id').textContent = res.complaintId;
        document.getElementById('success-banner').classList.remove('hidden');
        document.getElementById('success-banner').scrollIntoView({ behavior: 'smooth' });
        Toast.success('Complaint submitted successfully!');
      } else {
        Toast.error(res.errors ? res.errors.join(', ') : 'Submission failed.');
      }
    } catch (err) {
      Toast.error(err.message);
    } finally {
      setLoading(submitBtn, false);
    }
  });
}

function _validateForm() {
  let valid = true;

  const name = document.getElementById('reporter-name').value.trim();
  const phone = document.getElementById('reporter-phone').value.trim();
  const description = document.getElementById('description').value.trim();

  if (!name) { _showFieldError('name', 'Name is required'); valid = false; }
  else _clearFieldError('name');

  if (!phone || phone.length < 7) { _showFieldError('phone', 'Valid phone number is required'); valid = false; }
  else _clearFieldError('phone');

  if (!description || description.length < 20) { _showFieldError('description', 'Description must be at least 20 characters'); valid = false; }
  else _clearFieldError('description');

  if (!state.selectedLat || !state.selectedLng) { _showFieldError('latitude', 'Please select your location on the map or use GPS'); valid = false; }
  else _clearFieldError('latitude');

  return valid;
}

function _showFieldError(field, msg) {
  const input = document.getElementById(`reporter-${field}`) || document.getElementById(field);
  const err = document.getElementById(`err-${field}`);
  if (input) input.classList.add('error');
  if (err) { err.textContent = msg; err.classList.remove('hidden'); }
}

function _clearFieldError(field) {
  const input = document.getElementById(`reporter-${field}`) || document.getElementById(field);
  const err = document.getElementById(`err-${field}`);
  if (input) input.classList.remove('error');
  if (err) err.classList.add('hidden');
}

function resetForm() {
  document.getElementById('complaint-form').reset();
  document.getElementById('char-count').textContent = '0';
  document.getElementById('success-banner').classList.add('hidden');
  state.selectedLat = null;
  state.selectedLng = null;
  const preview = document.getElementById('image-preview');
  const placeholder = document.getElementById('upload-placeholder');
  if (preview) preview.classList.add('hidden');
  if (placeholder) placeholder.classList.remove('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}


// ── Track Filters ─────────────────────────────────────────
function initTrackFilters() {
  const search = document.getElementById('track-search');
  const statusFilter = document.getElementById('track-status-filter');
  const sortFilter = document.getElementById('track-sort');

  if (search) {
    search.addEventListener('input', debounce(() => {
      state.trackFilters.search = search.value;
      state.page = 1;
      loadTrackComplaints();
    }, 400));
  }

  if (statusFilter) {
    statusFilter.addEventListener('change', () => {
      state.trackFilters.status = statusFilter.value;
      state.page = 1;
      loadTrackComplaints();
    });
  }

  if (sortFilter) {
    sortFilter.addEventListener('change', () => {
      state.trackFilters.sort = sortFilter.value;
      state.page = 1;
      loadTrackComplaints();
    });
  }
}


// ── Load Track Complaints ─────────────────────────────────
async function loadTrackComplaints() {
  const container = document.getElementById('track-complaints-list');
  if (!container) return;

  container.innerHTML = '<div class="loading-container"><div class="loading-spinner"></div><span>Loading...</span></div>';

  try {
    const params = {
      search: state.trackFilters.search,
      status: state.trackFilters.status,
      sort: state.trackFilters.sort,
      order: state.trackFilters.sort === 'priorityScore' ? 'desc' : 'desc',
      page: state.page,
      per_page: 10,
    };

    const res = await API.getComplaints(params);
    const complaints = res.data || [];
    const pagination = res.pagination || {};
    state.totalPages = pagination.total_pages || 1;

    if (!complaints.length) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📭</div>
          <div class="empty-state-title">No complaints found</div>
          <div class="empty-state-desc">Try adjusting your search or filters.</div>
        </div>`;
      renderPagination();
      return;
    }

    container.innerHTML = complaints.map(c => `
      <article class="complaint-card" onclick="window.location.href='complaint-details.html?id=${c.id}'" tabindex="0" role="button">
        <div class="complaint-card-header">
          <span class="complaint-card-category">
            ${getCategoryIcon(c.category)} ${c.category ? c.category.replace(/_/g, ' ') : 'PROCESSING...'}
          </span>
          <div style="display:flex;align-items:center;gap:8px">
            ${renderStatusBadge(c.status)}
            ${c.priorityScore > 0 ? renderPriorityBadge(c.priorityScore) : ''}
          </div>
        </div>
        <p class="complaint-card-description">${escapeHtml(c.summary || c.description)}</p>
        <div class="complaint-card-meta">
          <span>🆔 ${c.id.substring(0, 8).toUpperCase()}</span>
          <span>⏱ ${timeAgo(c.createdAt)}</span>
          <span>👤 ${escapeHtml(c.reporterName)}</span>
          ${c.department ? `<span>🏛 ${c.department}</span>` : ''}
        </div>
      </article>
    `).join('');

    renderPagination();
  } catch (err) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-title">Failed to load complaints</div>
        <div class="empty-state-desc">${err.message}</div>
      </div>`;
  }
}


// ── Pagination ────────────────────────────────────────────
function renderPagination() {
  const container = document.getElementById('track-pagination');
  if (!container) return;

  if (state.totalPages <= 1) { container.innerHTML = ''; return; }

  const pages = [];
  const start = Math.max(1, state.page - 2);
  const end = Math.min(state.totalPages, state.page + 2);

  pages.push(`<button class="page-btn" ${state.page === 1 ? 'disabled' : ''} onclick="goPage(${state.page - 1})">‹</button>`);
  for (let i = start; i <= end; i++) {
    pages.push(`<button class="page-btn ${i === state.page ? 'active' : ''}" onclick="goPage(${i})">${i}</button>`);
  }
  pages.push(`<button class="page-btn" ${state.page === state.totalPages ? 'disabled' : ''} onclick="goPage(${state.page + 1})">›</button>`);

  container.innerHTML = pages.join('');
}

function goPage(p) {
  state.page = p;
  loadTrackComplaints();
  document.getElementById('panel-track').scrollIntoView({ behavior: 'smooth' });
}


// ── Quick Lookup ──────────────────────────────────────────
async function lookupComplaint() {
  const id = document.getElementById('lookup-id').value.trim();
  if (!id) { Toast.warning('Please enter a complaint ID'); return; }
  window.location.href = `complaint-details.html?id=${encodeURIComponent(id)}`;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}
