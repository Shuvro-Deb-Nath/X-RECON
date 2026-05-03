// cli.js
const input = document.getElementById('cli-input');
const history_el = document.getElementById('cli-history');
const output_el = document.getElementById('cli-output');
const cmdHistory = [];
let histIdx = -1;

// Focus terminal on click
document.getElementById('cli-terminal')?.addEventListener('click', () => input?.focus());
input?.focus();

// Example chips
document.querySelectorAll('.example-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    if (input) { input.value = chip.dataset.cmd; input.focus(); }
  });
});

// Clear button
document.getElementById('cli-clear-btn')?.addEventListener('click', clearTerminal);

// Key handling
input?.addEventListener('keydown', async e => {
  if (e.key === 'Enter') {
    const cmd = input.value.trim();
    if (!cmd) return;
    cmdHistory.unshift(cmd);
    histIdx = -1;
    input.value = '';
    appendCmd(cmd);
    if (cmd === 'clear') { clearTerminal(); return; }
    const lines = await sendCommand(cmd);
    lines.forEach(l => appendOut(l));
    output_el.scrollTop = output_el.scrollHeight;
  }
  if (e.key === 'ArrowUp') {
    histIdx = Math.min(histIdx + 1, cmdHistory.length - 1);
    input.value = cmdHistory[histIdx] || '';
    e.preventDefault();
  }
  if (e.key === 'ArrowDown') {
    histIdx = Math.max(histIdx - 1, -1);
    input.value = histIdx >= 0 ? cmdHistory[histIdx] : '';
    e.preventDefault();
  }
});

async function sendCommand(cmd) {
  try {
    const r = await fetch('/api/cli', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({command: cmd})
    });
    const data = await r.json();
    if (data.clear) { clearTerminal(); return []; }
    return data.output || [];
  } catch(e) {
    return [`[ERROR] Network failure: ${e.message}`];
  }
}

function appendCmd(cmd) {
  const row = document.createElement('div');
  row.style.display = 'flex';
  row.style.gap = '6px';
  row.style.paddingBottom = '2px';
  row.innerHTML = `
    <span style="font-family:var(--mono);font-size:.82rem;color:var(--cyan);white-space:nowrap">root@recon-x:~#</span>
    <span class="cli-cmd" style="font-family:var(--mono);font-size:.82rem">${escHtml(cmd)}</span>
  `;
  history_el.appendChild(row);
}

function appendOut(line) {
  const div = document.createElement('div');
  div.className = 'cli-out-line';
  const lower = line.toLowerCase();
  div.style.color =
    lower.includes('error') || lower.includes('fatal') ? 'var(--red)' :
    lower.includes('✓') || lower.includes('connected') || lower.includes('done') ? 'var(--cyan)' :
    lower.includes('⚠') || lower.includes('warn') || lower.includes('offline') ? 'var(--orange)' :
    lower.includes('module') || lower.includes('╔') || lower.includes('║') ? 'var(--purple)' :
    'var(--text)';
  div.textContent = line;
  history_el.appendChild(div);
}

function clearTerminal() {
  if (history_el) history_el.innerHTML = '';
  appendOut('Terminal cleared. Type help for commands.');
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
