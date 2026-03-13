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

tokenInput.value = getToken();
