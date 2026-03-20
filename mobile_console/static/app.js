const tokenInput = document.getElementById('token');
const statusOut = document.getElementById('statusOut');
const cmdOut = document.getElementById('cmdOut');
const presetSelect = document.getElementById('presetSelect');
const authState = document.getElementById('authState');
const ownerLiveDashboardBtn = document.getElementById('ownerLiveDashboardBtn');
const roleBadge = document.getElementById('roleBadge');

function getToken() {
  return localStorage.getItem('ctoa_mobile_token') || '';
}

function getSessionToken() {
  return sessionStorage.getItem('ctoa_live_token') || '';
}

function setToken(token) {
  localStorage.setItem('ctoa_mobile_token', token);
}

async function api(path, options = {}) {
  const token = getToken();
  const sessionToken = getSessionToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  if (token) {
    headers['X-CTOA-Token'] = token;
  } else if (sessionToken) {
    headers.Authorization = `Bearer ${sessionToken}`;
  }
  const res = await fetch(path, { ...options, headers });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

async function refreshOwnerUi() {
  if (!ownerLiveDashboardBtn) return;
  ownerLiveDashboardBtn.style.display = 'none';
  try {
    const me = await api('/api/auth/me');
    const role = String(me.role || '').toLowerCase();
    setRoleBadge(role || 'guest');
    if (role === 'owner') {
      ownerLiveDashboardBtn.style.display = 'inline-block';
    }
  } catch (_e) {
    setRoleBadge('guest');
    ownerLiveDashboardBtn.style.display = 'none';
  }
}

function setRoleBadge(role) {
  if (!roleBadge) return;
  const normalized = String(role || 'guest').toLowerCase();
  const knownRole = normalized === 'owner' || normalized === 'operator' ? normalized : 'guest';
  roleBadge.textContent = knownRole;
  roleBadge.className = `role-badge role-${knownRole}`;
}

document.getElementById('saveToken').onclick = () => {
  setToken(tokenInput.value.trim());
  alert('Token zapisany');
  void checkAuthAuto();
};

tokenInput.addEventListener('keydown', (ev) => {
  if (ev.key === 'Enter') {
    ev.preventDefault();
    document.getElementById('saveToken').click();
  }
});

async function checkAuthAuto() {
  try {
    const data = await api('/api/auth/auto-check');
    if (data.token_valid) {
      const authMode = getToken() ? 'legacy-token' : (getSessionToken() ? 'session' : 'unknown');
      authState.textContent = `Auth OK (${authMode}) | full_access=${data.full_access} | orchestrator_timer=${data.orchestrator_timer || 'unknown'}`;
      authState.style.color = '#7fff7f';
      await refreshOwnerUi();
    } else {
      authState.textContent = 'Token NIEPOPRAWNY: zapisz aktualny CTOA_MOBILE_TOKEN';
      authState.style.color = '#ff9999';
      setRoleBadge('guest');
      if (ownerLiveDashboardBtn) ownerLiveDashboardBtn.style.display = 'none';
    }
  } catch (e) {
    authState.textContent = 'Auto-check blad: ' + String(e);
    authState.style.color = '#ff9999';
    setRoleBadge('guest');
    if (ownerLiveDashboardBtn) ownerLiveDashboardBtn.style.display = 'none';
  }
}

document.getElementById('autoCheckToken').onclick = async () => {
  await checkAuthAuto();
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

document.getElementById('launchIntel').onclick = async () => {
  const raw = document.getElementById('intelUrls').value || '';
  const urls = raw
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean);
  const out = document.getElementById('agentStatusOut');
  try {
    const data = await api('/api/agents/intel/launch', {
      method: 'POST',
      body: JSON.stringify({ urls, force_rescout: true, trigger_now: true }),
    });
    out.textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    out.textContent = 'Intel launch error: ' + String(e);
  }
};

document.getElementById('mythibiaOneClick').onclick = async () => {
  const out = document.getElementById('agentStatusOut');
  try {
    const data = await api('/api/agents/mythibia/run', {
      method: 'POST',
      body: JSON.stringify({}),
    });
    const names = (data.files || []).map((f) => f.name);
    out.textContent = JSON.stringify({
      ok: data.ok,
      url: data.url,
      generated_dir: data.generated_dir,
      files_count: data.files_count,
      server_state: data.server_state,
      client_sync: data.client_sync || {},
      files: names,
    }, null, 2);
  } catch (e) {
    out.textContent = 'Mythibia one-click error: ' + String(e);
  }
};

document.getElementById('intelReport').onclick = async () => {
  const out = document.getElementById('agentStatusOut');
  try {
    const data = await api('/api/agents/intel/report');
    out.textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    out.textContent = 'Intel report error: ' + String(e);
  }
};

document.getElementById('autoTrainerLatest').onclick = async () => {
  const out = document.getElementById('agentStatusOut');
  try {
    const data = await api('/api/agents/auto-trainer/latest');
    if (!data.exists) {
      out.textContent = 'Brak raportu auto-trainera: ' + (data.detail || 'unknown');
      return;
    }
    const meta = {
      ok: data.ok,
      exists: data.exists,
      updated_at: data.updated_at,
      json_summary: data.json || {},
    };
    out.textContent = JSON.stringify(meta, null, 2) + '\n\n' + (data.markdown || '');
  } catch (e) {
    out.textContent = 'Auto-trainer latest error: ' + String(e);
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
setRoleBadge('guest');
void checkAuthAuto();
