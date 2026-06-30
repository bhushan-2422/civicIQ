/* ============================================================
   Landing Page JavaScript
   ============================================================ */

document.addEventListener('DOMContentLoaded', async () => {
  await Promise.all([
    loadStats(),
    loadRecentComplaints(),
    loadHeroes(),
  ]);
});


// ── Load Stats Strip ───────────────────────────────────────
async function loadStats() {
  try {
    const res = await API.getStats();
    const d = res.data;

    const animate = (el, target) => {
      if (!el) return;
      let start = 0;
      const step = Math.ceil(target / 40);
      const timer = setInterval(() => {
        start = Math.min(start + step, target);
        el.textContent = start.toLocaleString('en-IN');
        if (start >= target) clearInterval(timer);
      }, 30);
    };

    animate(document.getElementById('stat-total'), d.total || 0);
    animate(document.getElementById('stat-resolved'), d.resolved || 0);
    animate(document.getElementById('stat-pending'), d.pending || 0);
    animate(document.getElementById('stat-high-priority'), d.highPriority || 0);
  } catch {
    ['stat-total', 'stat-resolved', 'stat-pending', 'stat-high-priority'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = '0';
    });
  }
}


// ── Load Recent Complaints ────────────────────────────────
async function loadRecentComplaints() {
  const container = document.getElementById('recent-complaints-list');
  if (!container) return;

  try {
    const res = await API.getComplaints({ per_page: 6, sort: 'createdAt', order: 'desc' });
    const complaints = res.data || [];

    if (!complaints.length) {
      container.innerHTML = `
        <div class="empty-state" style="grid-column:1/-1">
          <div class="empty-state-icon">📭</div>
          <div class="empty-state-title">No complaints yet</div>
          <div class="empty-state-desc">Be the first to report a civic issue in your area.</div>
        </div>`;
      return;
    }

    container.innerHTML = complaints.map(c => `
      <article class="complaint-card" onclick="window.location.href='complaint-details.html?id=${c.id}'" tabindex="0" role="button" aria-label="View complaint ${c.id}">
        <div class="complaint-card-header">
          <span class="complaint-card-category">
            ${getCategoryIcon(c.category)} ${c.category ? c.category.replace('_', ' ') : 'PROCESSING'}
          </span>
          ${renderStatusBadge(c.status)}
        </div>
        <p class="complaint-card-description">${c.summary || c.description}</p>
        <div class="complaint-card-meta">
          <span>⏱ ${timeAgo(c.createdAt)}</span>
          ${c.priorityScore > 0 ? `<span>${renderPriorityBadge(c.priorityScore)}</span>` : ''}
          <span>👤 ${c.reporterName}</span>
        </div>
      </article>
    `).join('');
  } catch (err) {
    container.innerHTML = `
      <div class="empty-state" style="grid-column:1/-1">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-title">Could not load complaints</div>
        <div class="empty-state-desc">${err.message}</div>
      </div>`;
  }
}


// ── Load Heroes ───────────────────────────────────────────
async function loadHeroes() {
  const container = document.getElementById('heroes-list');
  if (!container) return;

  try {
    const res = await API.getLeaderboard(8);
    const heroes = res.data || [];

    if (!heroes.length) {
      container.innerHTML = `
        <div class="empty-state" style="grid-column:1/-1;color:rgba(255,255,255,0.7)">
          <div class="empty-state-icon">🏆</div>
          <div class="empty-state-title" style="color:#fff">No heroes yet</div>
          <div class="empty-state-desc">Start reporting valid complaints to earn your place on the leaderboard.</div>
        </div>`;
      return;
    }

    container.innerHTML = heroes.map((h, i) => {
      const rankClass = i === 0 ? 'rank-1' : i === 1 ? 'rank-2' : i === 2 ? 'rank-3' : 'rank-other';
      const rankEmoji = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${h.rank}`;
      return `
        <div class="hero-card">
          <div class="hero-rank ${rankClass}">${rankEmoji}</div>
          <div class="hero-info">
            <div class="hero-name">${escapeHtml(h.name)}</div>
            <div class="hero-badge-text">${h.badge}</div>
          </div>
          <div class="hero-count">
            <div class="hero-count-value">${h.validatedCount}</div>
            <div class="hero-count-label">Validated</div>
          </div>
        </div>`;
    }).join('');
  } catch (err) {
    container.innerHTML = `<div style="color:rgba(255,255,255,0.6);text-align:center;padding:2rem;grid-column:1/-1">Could not load heroes: ${err.message}</div>`;
  }
}


function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}
