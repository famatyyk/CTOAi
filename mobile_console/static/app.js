const tokenInput = document.getElementById('token');
const statusOut = document.getElementById('statusOut');
const cmdOut = document.getElementById('cmdOut');
const presetSelect = document.getElementById('presetSelect');

function getToken() {
  return localStorage.getItem('ctoa_mobile_token') || '';
}

function setToken(token) {
  localStorage.setItem('ctoa_mobile_token', token);
}

async function api(path, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    'X-CTOA-Token': token,
    ...(options.headers || {}),
  };
  const res = await fetch(path, { ...options, headers });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

document.getElementById('saveToken').onclick = () => {
  setToken(tokenInput.value.trim());
  alert('Token zapisany');
};

document.getElementById('refreshStatus').onclick = async () => {
  try {
    const data = await api('/api/status');
    statusOut.textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    statusOut.textContent = String(e);
  }
};

document.getElementById('runnerLog').onclick = async () => {
  try {
    const data = await api('/api/logs?target=runner&lines=120');
    statusOut.textContent = (data.stdout || '') + (data.stderr || '');
  } catch (e) {
    statusOut.textContent = String(e);
  }
};

document.getElementById('healthLog').onclick = async () => {
  try {
    const data = await api('/api/logs?target=health&lines=120');
    statusOut.textContent = (data.stdout || '') + (data.stderr || '');
  } catch (e) {
    statusOut.textContent = String(e);
  }
};

document.getElementById('mythibiaApiLog').onclick = async () => {
  try {
    const data = await api('/api/logs?target=mythibia_api&lines=120');
    statusOut.textContent = (data.stdout || '') + (data.stderr || '');
  } catch (e) {
    statusOut.textContent = String(e);
  }
};

document.getElementById('mythibiaWatcherLog').onclick = async () => {
  try {
    const data = await api('/api/logs?target=mythibia_watcher&lines=120');
    statusOut.textContent = (data.stdout || '') + (data.stderr || '');
  } catch (e) {
    statusOut.textContent = String(e);
  }
};

document.getElementById('loadPresets').onclick = async () => {
  try {
    const data = await api('/api/presets');
    presetSelect.innerHTML = '';
    data.commands.forEach((cmd) => {
      const opt = document.createElement('option');
      opt.textContent = cmd;
      opt.value = cmd;
      presetSelect.appendChild(opt);
    });
  } catch (e) {
    cmdOut.textContent = String(e);
  }
};

document.getElementById('runPreset').onclick = async () => {
  const cmd = presetSelect.value;
  if (!cmd) return;
  try {
    const data = await api('/api/command', {
      method: 'POST',
      body: JSON.stringify({ command: cmd, timeout: 30 }),
    });
    cmdOut.textContent = (data.stdout || '') + (data.stderr || '');
  } catch (e) {
    cmdOut.textContent = String(e);
  }
};

document.getElementById('runCmd').onclick = async () => {
  const cmd = document.getElementById('cmd').value.trim();
  if (!cmd) return;
  try {
    const data = await api('/api/command', {
      method: 'POST',
      body: JSON.stringify({ command: cmd, timeout: 60 }),
    });
    cmdOut.textContent = (data.stdout || '') + (data.stderr || '');
  } catch (e) {
    cmdOut.textContent = String(e);
  }
};

// ── Tab navigation ────────────────────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach((p) => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.add('active');
  });
});

// ── Server registration ───────────────────────────────────────────────────────
document.getElementById('registerServer').onclick = async () => {
  const url = document.getElementById('serverUrl').value.trim();
  const fb  = document.getElementById('serverFeedback');
  if (!url) { fb.className = 'error'; fb.textContent = 'Podaj URL serwera'; return; }
  try {
    const data = await api('/api/server/register', {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
    fb.className = 'ok';
    fb.textContent = '✓ Serwer zarejestrowany. Agenci startują… ' + JSON.stringify(data.db || '');
  } catch (e) {
    fb.className = 'error';
    fb.textContent = '✗ ' + String(e);
  }
};

// ── Dashboard ─────────────────────────────────────────────────────────────────
function badgeStatus(s) {
  const map = { VALIDATED:'ok', GENERATED:'ok', READY:'ok', INGESTED:'waiting', SCOUTING:'waiting',
                FAILED:'error', ERROR:'error', QUEUED:'queued', RELEASED:'ok', NEW:'queued' };
  const cls = map[s] || 'queued';
  return `<span class="badge badge-${cls}">${s}</span>`;
}

document.getElementById('refreshDash').onclick = async () => {
  try {
    const d = await api('/api/dashboard');

    // stats row: [dt, modules_generated, programs_generated, avg_quality, launcher_day]
    if (d.stats && d.stats.length > 0) {
      const row = d.stats[0];
      const mods = parseInt(row[1]) || 0;
      const progs = parseInt(row[2]) || 0;
      const qual = parseFloat(row[3]) || 0;
      const launched = (row[4] || '').trim() === 't';

      document.getElementById('dashModules').textContent = mods;
      document.getElementById('dashPrograms').textContent = progs;
      document.getElementById('dashQuality').textContent = qual.toFixed(1);
      document.getElementById('dashLauncher').textContent = launched ? '🚀 RELEASED' : '⏳ pending';
      document.getElementById('dashModuleBar').style.width = Math.min(100, mods * 2) + '%';
      document.getElementById('dashProgramBar').style.width = Math.min(100, progs * 20) + '%';
    }

    // servers table: [id, url, status, created_at]
    const srvBody = document.querySelector('#dashServers tbody');
    if (d.servers && d.servers.length > 0) {
      srvBody.innerHTML = d.servers.map(r =>
        `<tr><td>${r[0]||''}</td><td style="max-width:160px;overflow:hidden;text-overflow:ellipsis">${r[1]||''}</td><td>${badgeStatus((r[2]||'').trim())}</td></tr>`
      ).join('');
    }

    // top modules: [task_id, output_file, quality_score, status]
    const topBody = document.querySelector('#dashTop tbody');
    if (d.top && d.top.length > 0) {
      topBody.innerHTML = d.top.map(r =>
        `<tr><td>${r[0]||''}</td><td>${r[1]||''}</td><td><b>${r[2]||'?'}%</b></td><td>${badgeStatus((r[3]||'').trim())}</td></tr>`
      ).join('');
    }
  } catch (e) {
    document.getElementById('agentStatusOut').textContent = 'Dashboard error: ' + String(e);
  }
};

document.getElementById('refreshAgentStatus').onclick = async () => {
  const out = document.getElementById('agentStatusOut');
  try {
    const d = await api('/api/agents/status');
    out.textContent = JSON.stringify(d, null, 2);
  } catch (e) {
    out.textContent = String(e);
  }
};

// ── Agent logs ────────────────────────────────────────────────────────────────
const agentLogOut = document.getElementById('agentLogOut');
async function fetchAgentLog(target) {
  try {
    const d = await api(`/api/logs?target=${target}&lines=150`);
    agentLogOut.textContent = (d.stdout || '') + (d.stderr || '');
  } catch (e) {
    agentLogOut.textContent = String(e);
  }
}

['orchestrator','scout','brain','generator','validator','publisher'].forEach((name) => {
  const btn = document.getElementById('log' + name.charAt(0).toUpperCase() + name.slice(1));
  if (btn) btn.onclick = () => fetchAgentLog('agent_' + name);
});

tokenInput.value = getToken();
