/* ============================================================
   Officer Portal — JavaScript
   ============================================================ */

const officerState = {
  page: 1,
  totalPages: 1,
  filters: {
    search: '',
    status: '',
    department: '',
    category: '',
    sort: 'priorityScore',
  },
};

document.addEventListener('DOMContentLoaded', async () => {
  initOfficerFilters();
  await Promise.all([
    loadOfficerStats(),
    loadComplaints(),
    loadDeptChart(),
    loadCatChart(),
  ]);
});


// ── Stats ─────────────────────────────────────────────────
async function loadOfficerStats() {
  try {
    const res = await API.getStats();
    const d = res.data;
    _setStatValue('s-total', d.total);
    _setStatValue('s-pending', d.pending);
    _setStatValue('s-resolved', d.resolved);
    _setStatValue('s-high-priority', d.highPriority);
    _setStatValue('s-avg-priority', d.averagePriority.toFixed(1));
  } catch {
    ['s-total','s-pending','s-resolved','s-high-priority','s-avg-priority'].forEach(id => _setStatValue(id, '—'));
  }
}

function _setStatValue(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}


// ── Department Chart ──────────────────────────────────────
async function loadDeptChart() {
  const container = document.getElementById('dept-chart-container');
  if (!container) return;

  try {
    const res = await API.getDepartmentStats();
    const data = res.data || [];
    if (!data.length) { container.innerHTML = '<div class="text-muted text-center">No data</div>'; return; }

    const max = Math.max(...data.map(d => d.count));
    const colors = ['#1a3c6e','#2a5298','#e8792b','#16a34a','#dc2626','#d97706','#7c3aed','#0284c7'];

    container.innerHTML = `<div class="bar-chart">
      ${data.sort((a, b) => b.count - a.count).map((d, i) => `
        <div class="bar-item">
          <div class="bar-label" title="${d.department}">${d.department}</div>
          <div class="bar-track">
            <div class="bar-fill" style="width:${(d.count/max*100).toFixed(1)}%;background:${colors[i % colors.length]}"></div>
          </div>
          <div class="bar-value">${d.count}</div>
        </div>`).join('')}
    </div>`;
  } catch {
    container.innerHTML = '<div class="text-muted text-center">Failed to load</div>';
  }
}


// ── Category Chart ────────────────────────────────────────
async function loadCatChart() {
  const container = document.getElementById('cat-chart-container');
  if (!container) return;

  try {
    const res = await API.getCategoryStats();
    const data = res.data || [];
    if (!data.length) { container.innerHTML = '<div class="text-muted text-center">No data</div>'; return; }

    const max = Math.max(...data.map(d => d.count));
    const colors = ['#e8792b','#1a3c6e','#16a34a','#dc2626','#d97706','#7c3aed','#0284c7','#475569'];

    container.innerHTML = `<div class="bar-chart">
      ${data.sort((a, b) => b.count - a.count).map((d, i) => `
        <div class="bar-item">
          <div class="bar-label" title="${d.category}">${getCategoryIcon(d.category)} ${d.category.replace(/_/g,' ')}</div>
          <div class="bar-track">
            <div class="bar-fill" style="width:${(d.count/max*100).toFixed(1)}%;background:${colors[i % colors.length]}"></div>
          </div>
          <div class="bar-value">${d.count}</div>
        </div>`).join('')}
    </div>`;
  } catch {
    container.innerHTML = '<div class="text-muted text-center">Failed to load</div>';
  }
}


// ── Filters Init ──────────────────────────────────────────
function initOfficerFilters() {
  const bindings = [
    ['search-input', 'search', true],
    ['filter-status', 'status', false],
    ['filter-department', 'department', false],
    ['filter-category', 'category', false],
    ['sort-by', 'sort', false],
  ];

  bindings.forEach(([id, key, debounced]) => {
    const el = document.getElementById(id);
    if (!el) return;
    const handler = () => {
      officerState.filters[key] = el.value;
      officerState.page = 1;
      loadComplaints();
    };
    el.addEventListener(debounced ? 'input' : 'change', debounced ? debounce(handler, 400) : handler);
  });
}


// ── Load Complaints ───────────────────────────────────────
async function loadComplaints() {
  const tbody = document.getElementById('complaints-tbody');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="9" class="text-center" style="padding:3rem">
    <div class="loading-spinner" style="margin:0 auto"></div>
  </td></tr>`;

  try {
    const f = officerState.filters;
    const res = await API.getComplaints({
      search: f.search,
      status: f.status,
      department: f.department,
      category: f.category,
      sort: f.sort,
      order: 'desc',
      page: officerState.page,
      per_page: 15,
    });

    const complaints = res.data || [];
    const pagination = res.pagination || {};
    officerState.totalPages = pagination.total_pages || 1;

    const countText = document.getElementById('total-count-text');
    if (countText) countText.textContent = `${pagination.total || 0} complaints`;

    if (!complaints.length) {
      tbody.innerHTML = `<tr><td colspan="9">
        <div class="empty-state">
          <div class="empty-state-icon">📭</div>
          <div class="empty-state-title">No complaints found</div>
          <div class="empty-state-desc">Adjust your filters or wait for new submissions.</div>
        </div>
      </td></tr>`;
      renderOfficerPagination();
      return;
    }

    tbody.innerHTML = complaints.map(c => {
      const priority = c.priorityScore || 0;
      const priorityColor = priority >= 70 ? '#dc2626' : priority >= 40 ? '#d97706' : '#16a34a';

      return `
        <tr>
          <td>
            <span class="font-bold text-xs" style="font-family:monospace;color:var(--color-primary)">${c.id.substring(0, 8).toUpperCase()}</span>
          </td>
          <td>
            <div style="display:flex;align-items:center;gap:5px;white-space:nowrap">
              ${getCategoryIcon(c.category)}
              <span class="text-xs font-semibold">${c.category ? c.category.replace(/_/g,' ') : 'Processing...'}</span>
            </div>
          </td>
          <td>
            <div class="truncate-2 text-sm">${escapeHtml(c.summary || c.description)}</div>
          </td>
          <td><span class="text-xs text-muted">${c.department || '—'}</span></td>
          <td>
            <div class="priority-bar">
              ${renderPriorityBadge(priority)}
              <div class="priority-track">
                <div class="priority-fill" style="width:${priority}%;background:${priorityColor}"></div>
              </div>
            </div>
          </td>
          <td>${renderStatusBadge(c.status)}</td>
          <td>
            <div class="text-xs">
              <div class="font-semibold">${escapeHtml(c.reporterName)}</div>
              <div class="text-muted">${timeAgo(c.createdAt)}</div>
            </div>
          </td>
          <td class="text-xs text-muted" style="white-space:nowrap">${formatDate(c.createdAt)}</td>
          <td>
            <div class="action-btn-group">
              <a href="complaint-details.html?id=${c.id}" class="table-action-btn view" title="View details">👁 View</a>
              <button class="table-action-btn status" onclick="openStatusModal('${c.id}')" title="Update status">🔄</button>
              ${c.status === 'VALID' ? `<button class="table-action-btn assign" onclick="openAssignModal('${c.id}')" title="Assign worker">👷</button>` : ''}
            </div>
          </td>
        </tr>`;
    }).join('');

    renderOfficerPagination();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9">
      <div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-title">Failed to load complaints</div>
        <div class="empty-state-desc">${err.message}</div>
      </div>
    </td></tr>`;
  }
}


// ── Pagination ────────────────────────────────────────────
function renderOfficerPagination() {
  const container = document.getElementById('officer-pagination');
  if (!container) return;

  if (officerState.totalPages <= 1) { container.innerHTML = ''; return; }

  const pages = [];
  const start = Math.max(1, officerState.page - 2);
  const end = Math.min(officerState.totalPages, officerState.page + 2);

  pages.push(`<button class="page-btn" ${officerState.page === 1 ? 'disabled' : ''} onclick="officerGoPage(${officerState.page - 1})">‹</button>`);
  for (let i = start; i <= end; i++) {
    pages.push(`<button class="page-btn ${i === officerState.page ? 'active' : ''}" onclick="officerGoPage(${i})">${i}</button>`);
  }
  pages.push(`<button class="page-btn" ${officerState.page === officerState.totalPages ? 'disabled' : ''} onclick="officerGoPage(${officerState.page + 1})">›</button>`);

  container.innerHTML = pages.join('');
}

function officerGoPage(p) {
  officerState.page = p;
  loadComplaints();
}


// ── Status Modal ──────────────────────────────────────────
function openStatusModal(complaintId) {
  document.getElementById('status-complaint-id').value = complaintId;
  document.getElementById('status-modal').classList.remove('hidden');
}

function closeStatusModal() {
  document.getElementById('status-modal').classList.add('hidden');
}

async function submitStatusUpdate() {
  const id = document.getElementById('status-complaint-id').value;
  const status = document.getElementById('new-status').value;
  const btn = document.getElementById('status-submit-btn');

  setLoading(btn, true);
  try {
    await API.updateStatus(id, status);
    Toast.success(`Status updated to ${status}`);
    closeStatusModal();
    await Promise.all([loadComplaints(), loadOfficerStats()]);
  } catch (err) {
    Toast.error(err.message);
  } finally {
    setLoading(btn, false);
  }
}


// ── Assign Modal ──────────────────────────────────────────
function openAssignModal(complaintId) {
  document.getElementById('assign-complaint-id').value = complaintId;
  document.getElementById('worker-name').value = '';
  document.getElementById('worker-phone').value = '';
  document.getElementById('assign-modal').classList.remove('hidden');
}

function closeAssignModal() {
  document.getElementById('assign-modal').classList.add('hidden');
}

async function submitAssignment() {
  const id = document.getElementById('assign-complaint-id').value;
  const name = document.getElementById('worker-name').value.trim();
  const phone = document.getElementById('worker-phone').value.trim();
  const btn = document.getElementById('assign-submit-btn');

  if (!name || !phone) { Toast.warning('Please fill in both worker name and phone.'); return; }

  setLoading(btn, true);
  try {
    const res = await API.assignWorker(id, name, phone);
    if (res.smsSent) {
      Toast.success(`Worker assigned & SMS sent to ${name}!`);
    } else {
      Toast.info(`Worker assigned. SMS could not be sent (check Twilio config).`);
    }
    closeAssignModal();
    loadComplaints();
  } catch (err) {
    Toast.error(err.message);
  } finally {
    setLoading(btn, false);
  }
}


// Close modals on overlay click
document.getElementById('assign-modal').addEventListener('click', function(e) {
  if (e.target === this) closeAssignModal();
});
document.getElementById('status-modal').addEventListener('click', function(e) {
  if (e.target === this) closeStatusModal();
});


function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}
