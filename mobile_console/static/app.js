const tokenInput = document.getElementById('token');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const statusOut = document.getElementById('statusOut');
const cmdOut = document.getElementById('cmdOut');
const presetSelect = document.getElementById('presetSelect');
const authState = document.getElementById('authState');
const ownerLiveDashboardBtn = document.getElementById('ownerLiveDashboardBtn');
const roleBadge = document.getElementById('roleBadge');

let legacyToken = '';
let csrfToken = '';

function getToken() {
  return legacyToken;
}

function getSessionToken() {
  return sessionStorage.getItem('ctoa_live_token') || sessionStorage.getItem('ctoa_admin_api_token_v1') || '';
}

function setToken(token) {
  legacyToken = token;
}

async function api(path, options = {}) {
  const token = getToken();
  const sessionToken = getSessionToken();
  const method = String(options.method || 'GET').toUpperCase();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  if (token) {
    headers['X-CTOA-Token'] = token;
  } else if (sessionToken) {
    headers.Authorization = `Bearer ${sessionToken}`;
  }
  if (csrfToken && !['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    headers['X-CSRF-Token'] = csrfToken;
  }
  const requestInit = { ...options, headers, credentials: 'include' };
  const res = await fetch(path, requestInit);
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

function applyRoleState(role) {
  const normalized = String(role || 'guest').toLowerCase();
  setRoleBadge(normalized);
  if (ownerLiveDashboardBtn) {
    ownerLiveDashboardBtn.style.display = normalized === 'owner' ? 'inline-block' : 'none';
  }
}

function setRoleBadge(role) {
  if (!roleBadge) return;
  const normalized = String(role || 'guest').toLowerCase();
  const knownRole = normalized === 'owner' || normalized === 'operator' ? normalized : 'guest';
  roleBadge.textContent = knownRole;
  roleBadge.className = `role-badge role-${knownRole}`;
}

document.getElementById('saveToken').onclick = async () => {
  const username = usernameInput ? usernameInput.value.trim() : '';
  const password = passwordInput ? passwordInput.value : '';
  const legacy = tokenInput.value.trim();

  if (username && password) {
    try {
      const data = await api('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });
      setToken('');
      csrfToken = data.csrf_token || '';
      tokenInput.value = '';
      if (passwordInput) passwordInput.value = '';
      authState.textContent = `Sesja OK (${data.role || 'unknown'})`;
      authState.style.color = '#7fff7f';
      applyRoleState(data.role || 'guest');
      await refreshOwnerUi();
      return;
    } catch (e) {
      authState.textContent = 'Logowanie nieudane: ' + String(e);
      authState.style.color = '#ff9999';
      applyRoleState('guest');
      return;
    }
  }

  setToken(legacy);
  authState.textContent = legacy
    ? 'Legacy token aktywny tylko w biezacej karcie przegladarki.'
    : 'Podaj login/haslo albo legacy token dla tej karty.';
  authState.style.color = legacy ? '#f2c66d' : '#ff9999';
  void checkAuthAuto();
};

const logoutBtn = document.getElementById('logout');
if (logoutBtn) {
  logoutBtn.onclick = async () => {
    try {
      await api('/api/auth/logout', { method: 'POST' });
    } catch (_e) {
      // Logout should still clear client-side transient auth hints.
    }
    setToken('');
    csrfToken = '';
    tokenInput.value = '';
    if (passwordInput) passwordInput.value = '';
    authState.textContent = 'Sesja zakonczona';
    authState.style.color = '#888';
    applyRoleState('guest');
  };
}

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
      csrfToken = data.csrf_token || csrfToken;
      const authMode = data.auth_mode || (getToken() ? 'legacy-token-memory' : (getSessionToken() ? 'session' : 'cookie'));
      authState.textContent = `Auth OK (${authMode}) | command_mode=${data.command_mode || 'presets'} | orchestrator_timer=${data.orchestrator_timer || 'unknown'}`;
      authState.style.color = '#7fff7f';
      applyRoleState(data.role || 'guest');
      await refreshOwnerUi();
    } else {
      csrfToken = '';
      authState.textContent = 'Sesja niepoprawna: zaloguj sie albo podaj legacy token dla tej karty.';
      authState.style.color = '#ff9999';
      applyRoleState('guest');
    }
  } catch (e) {
    csrfToken = '';
    authState.textContent = 'Auto-check blad: ' + String(e);
    authState.style.color = '#ff9999';
    applyRoleState('guest');
  }
}

document.getElementById('autoCheckToken').onclick = async () => {
  await checkAuthAuto();
};

document.getElementById('refreshStatus').onclick = async () => {
  try {
    const [statusData, dictionaryData] = await Promise.all([
      api('/api/status'),
      api('/api/commands/dictionary').catch(() => null),
    ]);

    const view = {
      ...statusData,
      command_dictionary: dictionaryData
        ? {
            version: dictionaryData.version,
            source: dictionaryData.source,
            count: dictionaryData.count,
          }
        : null,
    };

    statusOut.textContent = JSON.stringify(view, null, 2);
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

document.getElementById('intelApiLog').onclick = async () => {
  try {
    const data = await api('/api/logs?target=intel_api&lines=120');
    statusOut.textContent = (data.stdout || '') + (data.stderr || '');
  } catch (e) {
    statusOut.textContent = String(e);
  }
};

document.getElementById('intelWatcherLog').onclick = async () => {
  try {
    const data = await api('/api/logs?target=intel_watcher&lines=120');
    statusOut.textContent = (data.stdout || '') + (data.stderr || '');
  } catch (e) {
    statusOut.textContent = String(e);
  }
};

document.getElementById('loadPresets').onclick = async () => {
  try {
    const data = await api('/api/presets');
    clearElement(presetSelect);
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

const runCmd = document.getElementById('runCmd');
if (runCmd) {
  runCmd.onclick = () => {
    cmdOut.textContent = 'Dowolne komendy sa zablokowane. Wybierz preset z allowlisty.';
  };
}

// Tab navigation ------------------------------------------------------------
document.querySelectorAll('.tab-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach((p) => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.add('active');
  });
});

// Server registration -------------------------------------------------------
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
    fb.textContent = 'OK: Serwer zarejestrowany. Agenci startuja... ' + JSON.stringify(data.db || '');
  } catch (e) {
    fb.className = 'error';
    fb.textContent = 'ERROR: ' + String(e);
  }
};

document.getElementById('launchIntel').onclick = async () => {
  const raw = document.getElementById('intelUrls').value || '';
  const urls = raw
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean);
  const out = document.getElementById('agentStatusOut');
  const reason = window.prompt('Powod audytu dla misji zwiadowczej:', 'manual intel launch');
  if (!reason || !reason.trim()) {
    out.textContent = 'Intel launch cancelled: missing audit reason.';
    return;
  }
  const confirmed = window.confirm('Uruchomic misje zwiadowcza teraz?');
  if (!confirmed) {
    out.textContent = 'Intel launch cancelled.';
    return;
  }
  try {
    const data = await api('/api/agents/intel/launch', {
      method: 'POST',
      body: JSON.stringify({
        urls,
        force_rescout: true,
        trigger_now: true,
        confirm: true,
        reason: reason.trim(),
      }),
    });
    out.textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    out.textContent = 'Intel launch error: ' + String(e);
  }
};

document.getElementById('intelOneClick').onclick = async () => {
  const out = document.getElementById('agentStatusOut');
  const reason = window.prompt('Powod audytu dla one-click run:', 'manual one-click intel run');
  if (!reason || !reason.trim()) {
    out.textContent = 'Intel one-click cancelled: missing audit reason.';
    return;
  }
  const confirmed = window.confirm('Uruchomic one-click Intel Run teraz?');
  if (!confirmed) {
    out.textContent = 'Intel one-click cancelled.';
    return;
  }
  try {
    const data = await api('/api/agents/execution/run', {
      method: 'POST',
      body: JSON.stringify({ confirm: true, reason: reason.trim() }),
    });
    const names = (data.files || []).map((f) => f.name);
    out.textContent = JSON.stringify({
      ok: data.ok,
      execution_status: data.execution_status,
      reason_code: data.reason_code,
      url: data.url,
      generated_dir: data.generated_dir,
      files_count: data.files_count,
      manifest: data.manifest || null,
      execution_trend: data.execution_trend || {},
      server_state: data.server_state,
      quality_gate: data.quality_gate || {},
      warnings: data.warnings || [],
      client_sync: data.client_sync || {},
      files: names,
    }, null, 2);
  } catch (e) {
    out.textContent = 'Intel one-click error: ' + String(e);
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

// Dashboard -----------------------------------------------------------------
function clearElement(node) {
  if (node) {
    node.replaceChildren();
  }
}

function createTextElement(tagName, className, text) {
  const node = document.createElement(tagName);
  if (className) {
    node.className = className;
  }
  node.textContent = String(text ?? '');
  return node;
}

function appendText(parent, text) {
  parent.appendChild(document.createTextNode(String(text ?? '')));
}

function safeStatusKey(value, fallback = 'warning') {
  const key = String(value || fallback).toLowerCase().replace(/[^a-z0-9_-]/g, '');
  return key || fallback;
}

function createStatusBadge(statusValue) {
  const normalized = String(statusValue || '').trim().toUpperCase();
  const statusMap = {
    VALIDATED: 'ok',
    GENERATED: 'ok',
    READY: 'ok',
    INGESTED: 'waiting',
    SCOUTING: 'waiting',
    FAILED: 'error',
    ERROR: 'error',
    QUEUED: 'queued',
    RELEASED: 'ok',
    NEW: 'queued',
  };
  const node = document.createElement('span');
  node.className = `badge badge-${statusMap[normalized] || 'queued'}`;
  node.textContent = normalized || 'UNKNOWN';
  return node;
}

function createEmptyTrend(text) {
  return createTextElement('div', 'trend-empty', text);
}

function renderReasonGroup(title, items) {
  const fragment = document.createDocumentFragment();
  if (!Array.isArray(items) || items.length === 0) {
    fragment.appendChild(createEmptyTrend(`Brak sygnalow dla grupy ${title}`));
    return fragment;
  }
  items.forEach((item) => {
    const count = Number(item.count || 0);
    const severity = safeStatusKey(item.severity, 'warning');
    const chip = document.createElement('div');
    chip.className = `trend-chip trend-${severity}`;
    chip.appendChild(createTextElement('span', '', item.code || 'UNKNOWN'));
    chip.appendChild(createTextElement('strong', '', Number.isFinite(count) ? count : 0));
    fragment.appendChild(chip);
  });
  return fragment;
}

function renderTimeline(items) {
  const fragment = document.createDocumentFragment();
  if (!Array.isArray(items) || items.length === 0) {
    fragment.appendChild(createEmptyTrend('Brak zdarzen 24h'));
    return fragment;
  }
  const maxVisible = 8;
  const visible = items.slice(0, maxVisible);
  const hiddenCount = Math.max(0, items.length - visible.length);
  visible.forEach((item) => {
    const severity = safeStatusKey(item.severity, 'warning');
    const row = document.createElement('div');
    row.className = `timeline-item timeline-${severity}`;
    row.appendChild(createTextElement('div', 'timeline-dot', ''));
    const body = document.createElement('div');
    body.appendChild(
      createTextElement('div', 'timeline-main', `${item.reason_code || 'UNKNOWN'} - ${item.event || 'pending'}`)
    );
    body.appendChild(createTextElement('div', 'timeline-meta', item.timestamp || ''));
    row.appendChild(body);
    fragment.appendChild(row);
  });

  if (hiddenCount > 0) {
    fragment.appendChild(createEmptyTrend(`+${hiddenCount} kolejnych zdarzen w oknie 24h`));
  }

  return fragment;
}

function bindTrendToggles(root) {
  root.querySelectorAll('[data-toggle-target]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-toggle-target');
      const panel = root.querySelector(`#${targetId}`);
      if (!panel) return;
      const expanded = btn.getAttribute('aria-expanded') === 'true';
      btn.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      panel.hidden = expanded;
    });
  });
}

function statusClassFromSeverity(severity) {
  const key = String(severity || '').toLowerCase();
  if (key === 'critical' || key === 'error') return 'status-critical';
  if (key === 'warning' || key === 'degraded') return 'status-warning';
  return 'status-info';
}

function appendEmptyTableRow(tbody, colSpan, text) {
  const row = document.createElement('tr');
  const cell = document.createElement('td');
  cell.colSpan = colSpan;
  cell.style.color = '#555';
  cell.textContent = text;
  row.appendChild(cell);
  tbody.appendChild(row);
}

function renderTrendBars(parent, topReasons) {
  const visible = topReasons.slice(0, 3);
  if (visible.length === 0) {
    parent.appendChild(createEmptyTrend('Brak top reason codes'));
    return;
  }

  visible.forEach((item) => {
    const count = Number(item.count || 0);
    const width = Math.max(8, Math.min(100, count * 20));
    const row = document.createElement('div');
    row.style.margin = '4px 0';

    const label = document.createElement('span');
    label.style.display = 'inline-block';
    label.style.minWidth = '165px';
    label.textContent = `${item.code || 'UNKNOWN'} (${Number.isFinite(count) ? count : 0})`;

    const bar = document.createElement('span');
    bar.style.display = 'inline-block';
    bar.style.height = '6px';
    bar.style.background = '#2f80ed';
    bar.style.borderRadius = '999px';
    bar.style.width = `${width}px`;

    row.appendChild(label);
    row.appendChild(bar);
    parent.appendChild(row);
  });
}

function createTrendToggle(targetId, label) {
  const button = document.createElement('button');
  button.className = 'trend-toggle';
  button.type = 'button';
  button.setAttribute('data-toggle-target', targetId);
  button.setAttribute('aria-expanded', 'true');
  button.textContent = label;
  return button;
}

function appendReasonGroup(parent, title, items) {
  const group = document.createElement('div');
  group.className = 'trend-group';
  group.appendChild(createTextElement('div', 'trend-group-title', title));
  group.appendChild(renderReasonGroup(title.toLowerCase(), items));
  parent.appendChild(group);
}

function renderTrendSummary(root, topReasons, dominant, slo, groups, sloTimeline) {
  clearElement(root);

  const shell = document.createElement('div');
  shell.className = 'trend-shell';

  const head = document.createElement('div');
  head.className = 'trend-head';

  const dominantLine = document.createElement('div');
  dominantLine.appendChild(createTextElement('b', '', 'Dominujacy reason_code:'));
  appendText(
    dominantLine,
    dominant ? ` ${dominant.code || 'UNKNOWN'} (${Number(dominant.count || 0)})` : ' brak danych reason_code'
  );

  const successRate = Number(slo.success_rate_24h ?? 1);
  const successTarget = Number(slo.success_rate_target ?? 1);
  const budgetLeft = Number(slo.error_budget_remaining ?? 0);
  const alertActive = Boolean(slo.alert_active);
  const successMet = Boolean(slo.success_rate_met);
  const sloLine = createTextElement(
    'div',
    `trend-slo ${successMet ? 'trend-ready' : 'trend-critical'}`,
    `SLO 24h: ${(successRate * 100).toFixed(1)}% / target ${(successTarget * 100).toFixed(1)}% | budget_left=${budgetLeft} | alert=${alertActive ? 'ON' : 'OFF'}`
  );

  head.appendChild(dominantLine);
  head.appendChild(sloLine);
  shell.appendChild(head);

  const bars = document.createElement('div');
  bars.className = 'trend-bars';
  renderTrendBars(bars, topReasons);
  shell.appendChild(bars);

  const groupsSection = document.createElement('div');
  groupsSection.className = 'trend-section';
  groupsSection.appendChild(createTrendToggle('trend-groups', 'Reason code groups'));
  const groupsPanel = document.createElement('div');
  groupsPanel.id = 'trend-groups';
  groupsPanel.className = 'trend-panel';
  appendReasonGroup(groupsPanel, 'Critical', groups.critical);
  appendReasonGroup(groupsPanel, 'Warning', groups.warning);
  appendReasonGroup(groupsPanel, 'Ready', groups.ready);
  groupsSection.appendChild(groupsPanel);
  shell.appendChild(groupsSection);

  const timelineSection = document.createElement('div');
  timelineSection.className = 'trend-section';
  timelineSection.appendChild(createTrendToggle('trend-timeline', 'SLO timeline 24h'));
  const timelinePanel = document.createElement('div');
  timelinePanel.id = 'trend-timeline';
  timelinePanel.className = 'trend-panel';
  timelinePanel.appendChild(renderTimeline(sloTimeline));
  timelineSection.appendChild(timelinePanel);
  shell.appendChild(timelineSection);

  root.appendChild(shell);
  bindTrendToggles(root);
}

function renderDashboardStatusContext(payload) {
  const messageEl = document.getElementById('dashStatusMessage');
  const detailEl = document.getElementById('dashStatusDetail');
  const impactedEl = document.getElementById('dashStatusImpacted');
  const actionsEl = document.getElementById('dashStatusActions');
  const dotEl = document.getElementById('dashStatusDot');
  const severityEl = document.getElementById('dashStatusSeverity');

  if (!messageEl || !detailEl || !impactedEl || !actionsEl || !dotEl || !severityEl) {
    return;
  }

  const context = payload && typeof payload.status_context === 'object' ? payload.status_context : {};
  const status = String((payload && payload.status) || '').toLowerCase();
  const severity = String(
    context.severity || (status === 'error' ? 'critical' : status === 'degraded' ? 'warning' : 'info')
  ).toLowerCase();
  const cssClass = statusClassFromSeverity(severity);

  const message = String(context.message || (payload && payload.status_message) || status || 'Brak statusu');
  const detail = String(context.detail || 'Brak dodatkowego opisu.');
  const impacted = Array.isArray(context.impacted_sections) ? context.impacted_sections : [];
  const criticalSections = Array.isArray(context.critical_sections) ? context.critical_sections : [];
  const actions = Array.isArray(context.recommended_actions) ? context.recommended_actions : [];

  dotEl.className = `dash-status-dot ${cssClass}`;
  severityEl.className = `dash-status-badge ${cssClass}`;
  severityEl.textContent = String(severity || 'info').toUpperCase();
  messageEl.textContent = message;
  detailEl.textContent = detail;

  clearElement(impactedEl);
  if (impacted.length > 0) {
    const criticalNames = criticalSections.map((name) => String(name));
    impacted.slice(0, 8).forEach((name) => {
      const chipClass = criticalNames.includes(String(name))
        ? 'dash-impact-chip-critical'
        : 'dash-impact-chip-warning';
      impactedEl.appendChild(createTextElement('span', `dash-impact-chip ${chipClass}`, name));
    });
  } else {
    impactedEl.textContent = 'Brak sekcji.';
  }

  clearElement(actionsEl);
  if (actions.length > 0) {
    actions.slice(0, 5).forEach((action) => {
      actionsEl.appendChild(createTextElement('li', '', action));
    });
  } else {
    actionsEl.appendChild(createTextElement('li', '', 'Brak akcji.'));
  }
}

document.getElementById('refreshDash').onclick = async () => {
  try {
    const d = await api('/api/dashboard');
    const out = document.getElementById('agentStatusOut');
    const trendSummary = document.getElementById('trendSummary');

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
      document.getElementById('dashLauncher').textContent = launched ? 'RELEASED' : 'pending';
      document.getElementById('dashModuleBar').style.width = Math.min(100, mods * 2) + '%';
      document.getElementById('dashProgramBar').style.width = Math.min(100, progs * 20) + '%';
    }

    // servers table: [id, url, status, created_at]
    const srvBody = document.querySelector('#dashServers tbody');
    if (srvBody) {
      clearElement(srvBody);
      if (d.servers && d.servers.length > 0) {
        d.servers.forEach((r) => {
          const row = document.createElement('tr');
          row.appendChild(createTextElement('td', '', r[0] || ''));
          const urlCell = createTextElement('td', '', r[1] || '');
          urlCell.style.maxWidth = '160px';
          urlCell.style.overflow = 'hidden';
          urlCell.style.textOverflow = 'ellipsis';
          row.appendChild(urlCell);
          const statusCell = document.createElement('td');
          statusCell.appendChild(createStatusBadge(r[2]));
          row.appendChild(statusCell);
          srvBody.appendChild(row);
        });
      } else {
        appendEmptyTableRow(srvBody, 3, 'brak danych');
      }
    }

    // top modules: [task_id, output_file, quality_score, status]
    const topBody = document.querySelector('#dashTop tbody');
    if (topBody) {
      clearElement(topBody);
      if (d.top && d.top.length > 0) {
        d.top.forEach((r) => {
          const quality = Number(r[2]);
          const safeQuality = Number.isFinite(quality) ? quality : '?';
          const row = document.createElement('tr');
          row.appendChild(createTextElement('td', '', r[0] || ''));
          row.appendChild(createTextElement('td', '', r[1] || ''));
          const qualityCell = document.createElement('td');
          qualityCell.appendChild(createTextElement('b', '', `${safeQuality}%`));
          row.appendChild(qualityCell);
          const statusCell = document.createElement('td');
          statusCell.appendChild(createStatusBadge(r[3]));
          row.appendChild(statusCell);
          topBody.appendChild(row);
        });
      } else {
        appendEmptyTableRow(topBody, 4, 'brak danych');
      }
    }

    const topReasons = Array.isArray(d.top_reason_codes) ? d.top_reason_codes : [];
    const dominant = topReasons.length > 0 ? topReasons[0] : null;
    const slo = d.slo_summary || {};
    const groups = d.reason_code_groups || {};
    const sloTimeline = Array.isArray(d.slo_timeline) ? d.slo_timeline : [];
    if (trendSummary) {
      renderTrendSummary(trendSummary, topReasons, dominant, slo, groups, sloTimeline);
    }

    renderDashboardStatusContext(d);

    const timelinePreview = (d.health_timeline || []).slice(0, 5).map((item) => ({
      date: item.date,
      avg_quality: item.avg_quality,
      modules_generated: item.modules_generated,
      programs_generated: item.programs_generated,
      launcher_released: item.launcher_released,
    }));

    const statusContext = d.status_context || {};
    const dashboardView = {
      dashboard_status: d.status,
      status_message: d.status_message || '',
      status_context: statusContext,
      degraded: d.degraded,
      summary: d.summary || {},
      timeline_summary: d.timeline_summary || {},
      top_reason_codes: d.top_reason_codes || [],
      reason_code_groups: d.reason_code_groups || {},
      dominant_signal: d.dominant_signal || null,
      slo_summary: d.slo_summary || {},
      slo_timeline_preview: sloTimeline.slice(0, 5),
      health_timeline_preview: timelinePreview,
    };

    if (d.degraded) {
      const degradedSections = Array.isArray(d.summary?.degraded_sections)
        ? d.summary.degraded_sections
        : [];
      const diagnostics = d.query_diagnostics || {};
      const diagnosticsPreview = Object.entries(diagnostics)
        .filter(([, meta]) => meta && meta.status !== 'ok')
        .slice(0, 3)
        .map(([name, meta]) => ({
          section: name,
          status: meta.status,
          duration_ms: meta.duration_ms,
          row_count: meta.row_count,
        }));
      dashboardView.degraded_compact = {
        degraded_sections_count: degradedSections.length,
        degraded_sections: degradedSections,
        diagnostics_preview: diagnosticsPreview,
        detail: statusContext.detail || '',
        recommended_actions: Array.isArray(statusContext.recommended_actions)
          ? statusContext.recommended_actions.slice(0, 3)
          : [],
      };
      dashboardView.errors = d.errors || {};
    }

    out.textContent = JSON.stringify(dashboardView, null, 2);
  } catch (e) {
    renderDashboardStatusContext({
      status: 'error',
      status_message: 'Dashboard error',
      status_context: {
        severity: 'critical',
        detail: String(e),
        impacted_sections: ['dashboard'],
        critical_sections: ['dashboard'],
        recommended_actions: [
          'Sprawdz polaczenie z API i token sesyjny.',
          'Ponow odswiezenie dashboardu.',
        ],
      },
    });
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

// Agent logs ----------------------------------------------------------------
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

tokenInput.value = '';
setRoleBadge('guest');
void checkAuthAuto();
