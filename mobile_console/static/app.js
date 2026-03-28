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
  return sessionStorage.getItem('ctoa_live_token') || sessionStorage.getItem('ctoa_admin_api_token_v1') || '';
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
      applyRoleState(data.role || 'guest');
      await refreshOwnerUi();
    } else {
      authState.textContent = 'Token NIEPOPRAWNY: zapisz aktualny CTOA_MOBILE_TOKEN';
      authState.style.color = '#ff9999';
      applyRoleState('guest');
    }
  } catch (e) {
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
    const data = await api('/api/agents/execution/run', {
      method: 'POST',
      body: JSON.stringify({}),
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

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function renderReasonGroup(title, items) {
  if (!Array.isArray(items) || items.length === 0) {
    return `<div class="trend-empty">Brak sygnałów dla grupy ${escapeHtml(title)}</div>`;
  }
  return items.map((item) => {
    const code = escapeHtml(item.code || 'UNKNOWN');
    const count = Number(item.count || 0);
    const severity = escapeHtml(item.severity || 'warning');
    return `
      <div class="trend-chip trend-${severity}">
        <span>${code}</span>
        <strong>${count}</strong>
      </div>
    `;
  }).join('');
}

function renderTimeline(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return '<div class="trend-empty">Brak zdarzeń 24h</div>';
  }
  const maxVisible = 8;
  const visible = items.slice(0, maxVisible);
  const hiddenCount = Math.max(0, items.length - visible.length);
  const rows = visible.map((item) => {
    const severity = escapeHtml(item.severity || 'warning');
    const eventName = escapeHtml(item.event || 'pending');
    const reasonCode = escapeHtml(item.reason_code || 'UNKNOWN');
    const timestamp = escapeHtml(item.timestamp || '');
    return `
      <div class="timeline-item timeline-${severity}">
        <div class="timeline-dot"></div>
        <div>
          <div class="timeline-main">${reasonCode} · ${eventName}</div>
          <div class="timeline-meta">${timestamp}</div>
        </div>
      </div>
    `;
  }).join('');

  const overflow = hiddenCount > 0
    ? `<div class="trend-empty">+${hiddenCount} kolejnych zdarzeń w oknie 24h</div>`
    : '';

  return rows + overflow;
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

    const topReasons = Array.isArray(d.top_reason_codes) ? d.top_reason_codes : [];
    const dominant = topReasons.length > 0 ? topReasons[0] : null;
    const slo = d.slo_summary || {};
    const groups = d.reason_code_groups || {};
    const sloTimeline = Array.isArray(d.slo_timeline) ? d.slo_timeline : [];
    if (trendSummary) {
      const bars = topReasons.slice(0, 3).map((item) => {
          const c = Number(item.count || 0);
          const w = Math.max(8, Math.min(100, c * 20));
          return `<div style="margin:4px 0"><span style="display:inline-block;min-width:165px">${item.code} (${c})</span><span style="display:inline-block;height:6px;background:#2f80ed;border-radius:999px;width:${w}px"></span></div>`;
        }).join('');
      const successRate = Number(slo.success_rate_24h ?? 1);
      const successTarget = Number(slo.success_rate_target ?? 1);
      const budgetLeft = Number(slo.error_budget_remaining ?? 0);
      const alertActive = Boolean(slo.alert_active);
      const successMet = Boolean(slo.success_rate_met);
      const dominantLabel = dominant
        ? `${escapeHtml(dominant.code)} (${dominant.count})`
        : 'brak danych reason_code';

      trendSummary.innerHTML =
        `<div class="trend-shell">` +
          `<div class="trend-head">` +
            `<div><b>Dominujący reason_code:</b> ${dominantLabel}</div>` +
            `<div class="trend-slo ${successMet ? 'trend-ready' : 'trend-critical'}">SLO 24h: ${(successRate * 100).toFixed(1)}% / target ${(successTarget * 100).toFixed(1)}% · budget_left=${budgetLeft} · alert=${alertActive ? 'ON' : 'OFF'}</div>` +
          `</div>` +
          `<div class="trend-bars">${bars || '<div class="trend-empty">Brak top reason codes</div>'}</div>` +
          `<div class="trend-section">` +
            `<button class="trend-toggle" type="button" data-toggle-target="trend-groups" aria-expanded="true">Reason code groups</button>` +
            `<div id="trend-groups" class="trend-panel">` +
              `<div class="trend-group"><div class="trend-group-title">Critical</div>${renderReasonGroup('critical', groups.critical)}</div>` +
              `<div class="trend-group"><div class="trend-group-title">Warning</div>${renderReasonGroup('warning', groups.warning)}</div>` +
              `<div class="trend-group"><div class="trend-group-title">Ready</div>${renderReasonGroup('ready', groups.ready)}</div>` +
            `</div>` +
          `</div>` +
          `<div class="trend-section">` +
            `<button class="trend-toggle" type="button" data-toggle-target="trend-timeline" aria-expanded="true">SLO timeline 24h</button>` +
            `<div id="trend-timeline" class="trend-panel">${renderTimeline(sloTimeline)}</div>` +
          `</div>` +
        `</div>`;
      bindTrendToggles(trendSummary);
    }

    const timelinePreview = (d.health_timeline || []).slice(0, 5).map((item) => ({
      date: item.date,
      avg_quality: item.avg_quality,
      modules_generated: item.modules_generated,
      programs_generated: item.programs_generated,
      launcher_released: item.launcher_released,
    }));

    const dashboardView = {
      dashboard_status: d.status,
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
      };
      dashboardView.errors = d.errors || {};
    }

    out.textContent = JSON.stringify(dashboardView, null, 2);
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
