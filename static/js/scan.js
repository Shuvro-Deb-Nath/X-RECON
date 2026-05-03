// scan.js — New Scan page logic
let currentScanId = null;
let pollOffset    = 0;
let pollTimer     = null;
let logLineCount  = 0;

// ── Module toggle cards ────────────────────────────────────────
document.querySelectorAll('.module-toggle').forEach(el => {
  el.addEventListener('click', () => el.classList.toggle('active'));
});

// ── Thread slider ──────────────────────────────────────────────
const slider = document.getElementById('scan-threads');
const valEl  = document.getElementById('thread-val');
if (slider) slider.addEventListener('input', () => { if (valEl) valEl.textContent = slider.value; });

// ── Start scan ─────────────────────────────────────────────────
document.getElementById('start-scan-btn')?.addEventListener('click', async () => {
  const domain = document.getElementById('scan-domain').value.trim();
  if (!domain) { showToast('Domain is required', 'error'); return; }

  // Basic domain validation
  if (!/^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$/.test(domain)) {
    showToast('Please enter a valid domain (e.g. example.com)', 'warning'); return;
  }

  const modules = Array.from(document.querySelectorAll('.module-toggle.active'))
    .map(el => el.dataset.module);
  if (!modules.length) { showToast('Select at least one module', 'warning'); return; }

  const threads  = parseInt(document.getElementById('scan-threads')?.value || '20');
  const wordlist = document.getElementById('scan-wordlist')?.value.trim() || '';

  // Reset UI
  clearOutput();
  setStatus('running', 'Running…');
  setProgress('running', 5);
  document.getElementById('result-summary')?.classList.add('hidden');
  document.getElementById('terminal-placeholder')?.style.setProperty('display', 'none');

  const btn = document.getElementById('start-scan-btn');
  btn.disabled = true;
  btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin .8s linear infinite"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg> Scanning…`;

  showStopBtn(true);

  try {
    const res = await fetch('/api/scan/start', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ domain, modules, threads, wordlist }),
    });
    const data = await res.json();
    if (data.error) { showToast(data.error, 'error'); resetBtn(); showStopBtn(false); return; }

    currentScanId = data.scan_id;
    pollOffset    = 0;
    logLineCount  = 0;
    pollTimer     = setInterval(poll, 1000);
    showToast(`Scan started — ID: ${data.scan_id}`, 'success');
  } catch (e) {
    showToast('Network error: could not reach backend', 'error');
    setStatus('error', 'Failed');
    setProgress('error', 100);
    resetBtn();
    showStopBtn(false);
  }
});

// ── Stop scan ──────────────────────────────────────────────────
document.getElementById('stop-scan-btn')?.addEventListener('click', async () => {
  if (!currentScanId) return;
  const stopBtn = document.getElementById('stop-scan-btn');
  stopBtn.disabled = true;
  stopBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin .8s linear infinite" width="14" height="14"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg> Stopping…`;
  setStatus('running', 'Stopping…');
  try {
    await fetch(`/api/scan/${currentScanId}/stop`, { method: 'POST' });
    showToast('Stop signal sent — scan will halt shortly', 'warning');
  } catch (e) {
    showToast('Could not reach backend to stop scan', 'error');
    stopBtn.disabled = false;
  }
});

// ── Polling ────────────────────────────────────────────────────
async function poll() {
  if (!currentScanId) return;
  try {
    const r    = await fetch(`/api/scan/${currentScanId}/poll?since=${pollOffset}`);
    const data = await r.json();

    data.logs.forEach(appendLine);
    pollOffset   += data.logs.length;
    logLineCount += data.logs.length;

    // Rough progress estimate based on log lines
    if (data.status === 'running') {
      const pct = Math.min(5 + logLineCount * 1.5, 90);
      setProgress('running', pct);
    }

    if (data.status === 'done' || data.status === 'error' || data.status === 'stopped') {
      clearInterval(pollTimer);
      const ok      = data.status === 'done';
      const stopped = data.status === 'stopped';
      setStatus(data.status, ok ? 'Complete' : stopped ? 'Stopped' : 'Error');
      setProgress(data.status === 'stopped' ? 'stopped' : data.status, 100);
      resetBtn();
      showStopBtn(false);
      if (ok || stopped) showSummary(data.result, document.getElementById('scan-domain')?.value.trim(), stopped);
    }
  } catch (e) { /* network glitch — retry next tick */ }
}

// ── Helpers ────────────────────────────────────────────────────
function appendLine(text) {
  const container = document.getElementById('output-lines');
  if (!container) return;
  const div = document.createElement('div');
  div.className = 'output-line' +
    (text.includes('[FATAL]') || (text.includes('ERROR') && !text.includes('✗'))
        ? ' output-line--err'
      : text.includes('✓')
        ? ' output-line--ok'
      : text.includes('⚠') || text.includes('WARN')
        ? ' output-line--warn'
      : text.includes('[MODULE') || text.includes('══')
        ? ' output-line--system'
        : '');
  div.textContent = text;
  container.appendChild(div);
  const term = document.getElementById('terminal-output');
  if (term) term.scrollTop = term.scrollHeight;
}

function clearOutput() {
  const c = document.getElementById('output-lines');
  if (c) c.innerHTML = '';
}

function setStatus(state, label) {
  const pill = document.getElementById('scan-status-pill');
  const lbl  = document.getElementById('scan-status-label');
  if (pill) pill.className = `scan-status-pill ${state}`;
  if (lbl)  lbl.textContent = label;
}

function setProgress(state, pct) {
  const bar  = document.getElementById('scan-progress-bar');
  const fill = document.getElementById('scan-progress-fill');
  if (!bar || !fill) return;
  bar.style.display = 'block';
  bar.className = `scan-progress-bar ${state}`;
  fill.style.width = `${Math.round(pct)}%`;
}

function showStopBtn(visible) {
  const btn = document.getElementById('stop-scan-btn');
  if (!btn) return;
  if (visible) {
    btn.classList.remove('hidden');
    btn.disabled = false;
    btn.innerHTML = `<svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14"><rect x="4" y="4" width="16" height="16" rx="2"/></svg> Stop Scan`;
  } else {
    btn.classList.add('hidden');
  }
}

function showSummary(result, domain, stopped = false) {
  const box = document.getElementById('result-summary');
  if (!box) return;
  box.classList.remove('hidden');
  const header = box.querySelector('.result-summary__header');
  if (header) header.textContent = stopped ? 'Scan Stopped' : 'Scan Complete';
  if (stopped && header) header.style.color = 'var(--orange)';
  const stats = document.getElementById('result-stats');
  if (stats) {
    const subs  = (result.subdomains  || []).length;
    const dirs  = (result.directories || []).length;
    const vulns = (result.vulnerabilities || []).length;
    stats.innerHTML = `
      <span class="badge badge--cyan">${subs} subdomain${subs !== 1 ? 's' : ''}</span>
      <span class="badge badge--blue">${dirs} director${dirs !== 1 ? 'ies' : 'y'}</span>
      <span class="badge badge--${vulns > 0 ? 'red' : 'grey'}">${vulns} payload hint${vulns !== 1 ? 's' : ''}</span>
    `;
  }
  const viewBtn = document.getElementById('view-detail-btn');
  if (viewBtn && domain) viewBtn.href = `/results/${encodeURIComponent(domain)}`;
}

function resetBtn() {
  const btn = document.getElementById('start-scan-btn');
  if (!btn) return;
  btn.disabled = false;
  btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5,3 19,12 5,21"/></svg> Launch Scan`;
}
