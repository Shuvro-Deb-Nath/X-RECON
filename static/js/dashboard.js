// dashboard.js
// Animated counters
document.querySelectorAll('.counter').forEach(el => {
  const target = parseInt(el.dataset.target, 10) || 0;
  if (target === 0) { el.textContent = '0'; return; }
  let current = 0;
  const step = Math.ceil(target / 40);
  const timer = setInterval(() => {
    current = Math.min(current + step, target);
    el.textContent = current;
    if (current >= target) clearInterval(timer);
  }, 30);
});

// Quick scan form on dashboard
const quickBtn = document.getElementById('quick-scan-btn');
if (quickBtn) {
  quickBtn.addEventListener('click', async () => {
    const domain = document.getElementById('quick-domain').value.trim();
    if (!domain) { showToast('Please enter a domain', 'error'); return; }
    const modules = ['mod-a','mod-b','mod-c']
      .filter(id => document.getElementById(id)?.checked)
      .map(id => id.replace('mod-', '').toUpperCase());
    quickBtn.disabled = true;
    quickBtn.textContent = 'Launching…';
    try {
      const r = await fetch('/api/scan/start', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({domain, modules, threads: 20})
      });
      const data = await r.json();
      if (data.scan_id) {
        showToast(`Scan started! ID: ${data.scan_id}`, 'success');
        setTimeout(() => window.location.href = '/scan', 1000);
      } else {
        showToast(data.error || 'Failed to start scan', 'error');
      }
    } catch(e) {
      showToast('Network error', 'error');
    } finally {
      quickBtn.disabled = false;
      quickBtn.textContent = 'Launch Scan';
    }
  });
}
