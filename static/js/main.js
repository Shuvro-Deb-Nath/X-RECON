// main.js — shared utilities & global UI
// ─────────────────────────────────────────────────────────────

// ── Toast notifications ────────────────────────────────────────
function showToast(msg, type = 'info') {
  const c = document.getElementById('toast-container');
  if (!c) return;
  const t = document.createElement('div');
  t.className = `toast toast--${type}`;
  const icons = {
    success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="16" height="16"><polyline points="20 6 9 17 4 12"/></svg>',
    error:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="16" height="16"><path d="M18 6L6 18M6 6l12 12"/></svg>',
    info:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16v1"/></svg>',
    warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M12 2L2 19h20L12 2z"/><path d="M12 9v5M12 17v1"/></svg>',
  };
  t.innerHTML = `${icons[type] || icons.info}<span>${msg}</span>`;
  c.appendChild(t);
  // Animate out
  setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateY(8px)'; }, 2700);
  setTimeout(() => t.remove(), 3000);
}

// ── Live clock ─────────────────────────────────────────────────
function updateClock() {
  const el = document.getElementById('topbar-time');
  if (el) el.textContent = new Date().toUTCString().slice(17, 25) + ' UTC';
}
setInterval(updateClock, 1000);
updateClock();

// ── Sidebar toggle (mobile) ────────────────────────────────────
const toggleBtn = document.getElementById('sidebar-toggle');
const sidebar   = document.getElementById('sidebar');
const overlay   = document.getElementById('sidebar-overlay');

function openSidebar() {
  sidebar?.classList.add('open');
  overlay?.classList.add('visible');
  document.body.style.overflow = 'hidden'; // prevent bg scroll on mobile
}

function closeSidebar() {
  sidebar?.classList.remove('open');
  overlay?.classList.remove('visible');
  document.body.style.overflow = '';
}

if (toggleBtn && sidebar) {
  toggleBtn.addEventListener('click', () => {
    if (sidebar.classList.contains('open')) closeSidebar();
    else openSidebar();
  });
}

// Tap overlay to close
if (overlay) {
  overlay.addEventListener('click', closeSidebar);
}

// Swipe-left on sidebar to close (touch devices)
if (sidebar) {
  let touchStartX = 0;
  sidebar.addEventListener('touchstart', e => { touchStartX = e.touches[0].clientX; }, { passive: true });
  sidebar.addEventListener('touchend', e => {
    if (touchStartX - e.changedTouches[0].clientX > 60) closeSidebar();
  }, { passive: true });
}

// ── Close sidebar on nav click (mobile) ───────────────────────
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', () => {
    if (window.innerWidth < 768) closeSidebar();
  });
});

// Reopen scroll lock on resize back to desktop
window.addEventListener('resize', () => {
  if (window.innerWidth >= 768) {
    document.body.style.overflow = '';
    overlay?.classList.remove('visible');
  }
});

// ── Topbar session scan counter ────────────────────────────────
async function updateScanBadge() {
  try {
    const r = await fetch('/api/scans');
    const scans = await r.json();
    if (!Array.isArray(scans) || scans.length === 0) return;
    const badge = document.getElementById('topbar-scan-badge');
    const countEl = document.getElementById('topbar-scan-count');
    if (!badge || !countEl) return;
    const running = scans.filter(s => s.status === 'running').length;
    badge.style.display = 'flex';
    badge.style.borderColor = running > 0 ? 'rgba(0,245,212,.4)' : 'var(--border)';
    const dot = badge.querySelector('.scan-badge-dot');
    if (dot) dot.style.background = running > 0 ? 'var(--cyan)' : 'var(--text-muted)';
    countEl.textContent = `${scans.length} scan${scans.length !== 1 ? 's' : ''}`;
    // Recurse if there are running scans
    if (running > 0) setTimeout(updateScanBadge, 3000);
  } catch (_) {}
}
updateScanBadge();
