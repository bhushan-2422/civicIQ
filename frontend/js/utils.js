/* ============================================================
   UI Utilities — Shared across all pages
   ============================================================ */

// ── Toast Notifications ────────────────────────────────────
const Toast = (() => {
  let container = null;

  function _getContainer() {
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      container.setAttribute('aria-live', 'polite');
      document.body.appendChild(container);
    }
    return container;
  }

  function show(message, type = 'info', duration = 4000) {
    const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${message}</span>`;
    _getContainer().appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  return { show, success: (m) => show(m, 'success'), error: (m) => show(m, 'error'), info: (m) => show(m, 'info'), warning: (m) => show(m, 'warning') };
})();


// ── Status Badge ───────────────────────────────────────────
function renderStatusBadge(status) {
  const icons = {
    PROCESSING: '⏳',
    VALID: '✅',
    IN_PROGRESS: '🔧',
    RESOLVED: '✔️',
    REJECTED: '❌',
  };
  const icon = icons[status] || '•';
  return `<span class="status-badge ${status}">${icon} ${status.replace('_', ' ')}</span>`;
}


// ── Priority Badge ─────────────────────────────────────────
function renderPriorityBadge(score) {
  let cls, label;
  if (score >= 70) { cls = 'priority-high'; label = '🔴 HIGH'; }
  else if (score >= 40) { cls = 'priority-medium'; label = '🟡 MEDIUM'; }
  else { cls = 'priority-low'; label = '🟢 LOW'; }
  return `<span class="priority-badge ${cls}">${label} ${score.toFixed(1)}</span>`;
}


// ── Category Icon Map ──────────────────────────────────────
const CATEGORY_ICONS = {
  ROAD_DAMAGE: '🛣️',
  WATER_LEAKAGE: '💧',
  STREETLIGHT: '💡',
  TRAFFIC_SIGNAL: '🚦',
  SEWERAGE: '🕳️',
  GARBAGE: '🗑️',
  TREE_FALL: '🌳',
  OTHER: '📋',
};

function getCategoryIcon(cat) {
  return CATEGORY_ICONS[cat] || '📋';
}


// ── Relative Time ──────────────────────────────────────────
function timeAgo(dateStr) {
  if (!dateStr) return 'Unknown';
  const now = new Date();
  const date = new Date(dateStr);
  const diff = Math.floor((now - date) / 1000);

  if (diff < 60) return 'Just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}


// ── Format Date ────────────────────────────────────────────
function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}


// ── Format Currency ────────────────────────────────────────
function formatCurrency(amount) {
  if (!amount) return '₹0';
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
}


// ── Debounce ───────────────────────────────────────────────
function debounce(fn, delay = 400) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}


// ── Navbar Mobile Toggle ───────────────────────────────────
function initNavbar() {
  const hamburger = document.getElementById('navbar-hamburger');
  const nav = document.getElementById('navbar-nav');
  if (hamburger && nav) {
    hamburger.addEventListener('click', () => {
      nav.classList.toggle('open');
    });
  }
}

document.addEventListener('DOMContentLoaded', initNavbar);


// ── Loading State ──────────────────────────────────────────
function setLoading(el, isLoading, originalText = null) {
  if (isLoading) {
    el.dataset.originalText = el.innerHTML;
    el.classList.add('btn-loading');
    el.disabled = true;
  } else {
    el.classList.remove('btn-loading');
    el.disabled = false;
    if (originalText) el.innerHTML = originalText;
    else if (el.dataset.originalText) el.innerHTML = el.dataset.originalText;
  }
}


// ── Copy to Clipboard ──────────────────────────────────────
async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    Toast.success('Copied to clipboard!');
  } catch {
    Toast.error('Could not copy.');
  }
}
