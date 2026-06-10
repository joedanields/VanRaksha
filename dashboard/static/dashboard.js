const state = { start: Date.now(), muted: false };
const socket = io();
const videoFileInput = document.getElementById('videoFile');
const videoStatus = document.getElementById('videoStatus');
const uploadBtn = document.getElementById('uploadBtn');
const stopVideoBtn = document.getElementById('stopVideoBtn');

function setVideoStatus(message) {
  if (!videoStatus) return;
  videoStatus.textContent = message;
}

function updateClock() {
  const now = new Date();
  document.getElementById('liveClock').textContent = now.toLocaleTimeString();
  const up = Math.floor((Date.now() - state.start) / 1000);
  document.getElementById('uptime').textContent = `Uptime: ${up}s`;
}
setInterval(updateClock, 1000);
updateClock();

async function refreshStats() {
  const stats = await fetch('/api/stats').then(r => r.json());
  document.getElementById('totalDetections').textContent = stats.last_24h ?? 0;
  const species = Object.entries(stats.by_species || {}).sort((a, b) => b[1] - a[1]);
  document.getElementById('mostSeen').textContent = species.length ? species[0][0] : '-';
}

async function refreshEvents() {
  const events = await fetch('/api/events').then(r => r.json());
  const body = document.getElementById('eventsBody');
  body.innerHTML = '';
  events.slice(0, 20).forEach(e => {
    const tr = document.createElement('tr');
    tr.className = (e.alert_level || 'SAFE').toLowerCase();
    const riskLabelText = e.risk_label || '-';
    tr.innerHTML = `<td>${e.timestamp || '-'}</td><td>${e.species || '-'}</td><td class="risk-cell">${riskLabelText}</td><td>${(e.threat_score || 0).toFixed ? e.threat_score.toFixed(1) : e.threat_score}</td><td>${e.alert_level || 'SAFE'}</td>`;
    body.appendChild(tr);
  });
}

socket.on('new_alert', data => {
  document.getElementById('species').textContent = data.species || '-';
  document.getElementById('confidence').textContent = `${Math.round((data.confidence || 0) * 100)}%`;
  document.getElementById('score').textContent = data.score?.toFixed ? data.score.toFixed(1) : (data.score || 0);
  document.getElementById('scoreBar').style.width = `${Math.max(0, Math.min(100, data.score || 0))}%`;
  document.getElementById('alertText').textContent = data.alert_level || 'SAFE';
  const badge = document.getElementById('alertBadge');
  const level = (data.alert_level || 'SAFE').toLowerCase();
  badge.className = `badge ${level}`;
  badge.textContent = data.alert_level || 'SAFE';
  document.getElementById('lastAlert').textContent = new Date().toLocaleString();

  // Show risk label prominently when present.
  const riskLabel = data.risk_label || '';
  const riskLabelWrap = document.getElementById('riskLabelWrap');
  const riskLabelEl = document.getElementById('riskLabel');
  if (riskLabel) {
    riskLabelEl.textContent = riskLabel;
    // Determine color class from label prefix.
    riskLabelEl.className = 'risk-label';
    if (riskLabel.startsWith('HIGH')) riskLabelEl.classList.add('risk-high');
    else if (riskLabel.startsWith('CRITICAL')) riskLabelEl.classList.add('risk-critical');
    else if (riskLabel.startsWith('MODERATE')) riskLabelEl.classList.add('risk-moderate');
    else riskLabelEl.classList.add('risk-low');
    riskLabelWrap.style.display = '';
  } else {
    riskLabelWrap.style.display = 'none';
  }

  refreshEvents();
});

socket.on('frame_stats', () => {});

// ── Camera stop / resume toggle ───────────────────────────────────────────
const camToggleBtn = document.getElementById('camToggleBtn');
const camStatus    = document.getElementById('camStatus');
const camStatusText = document.getElementById('camStatusText');
let camLive = true;

camToggleBtn?.addEventListener('click', async () => {
  const endpoint = camLive ? '/api/camera/stop' : '/api/camera/start';
  try {
    const res = await fetch(endpoint, { method: 'POST' });
    const data = await res.json();
    if (!res.ok || !data.ok) return;
    camLive = !camLive;
    if (camLive) {
      camToggleBtn.textContent = '⏹ Stop Live Cam';
      camToggleBtn.classList.remove('cam-resume-btn');
      camToggleBtn.classList.add('cam-stop-btn');
      camStatus.className = 'cam-dot live';
      camStatusText.textContent = 'LIVE';
    } else {
      camToggleBtn.textContent = '▶ Resume Cam';
      camToggleBtn.classList.remove('cam-stop-btn');
      camToggleBtn.classList.add('cam-resume-btn');
      camStatus.className = 'cam-dot paused';
      camStatusText.textContent = 'PAUSED';
    }
  } catch (err) {
    console.error('Camera toggle failed:', err);
  }
});
// ─────────────────────────────────────────────────────────────────────────

document.getElementById('muteBtn').addEventListener('click', async () => {
  state.muted = !state.muted;
  const muteBtn = document.getElementById('muteBtn');
  muteBtn.textContent = state.muted ? 'Unmute voice' : 'Mute voice';
  muteBtn.setAttribute('aria-pressed', String(state.muted));
  await fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ alert_mute: state.muted }),
  });
});

uploadBtn?.addEventListener('click', async () => {
  const file = videoFileInput?.files?.[0];
  if (!file) {
    setVideoStatus('Select a video to upload.');
    return;
  }
  setVideoStatus('Uploading...');
  const form = new FormData();
  form.append('file', file);
  try {
    const response = await fetch('/api/video/upload', { method: 'POST', body: form });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      setVideoStatus(data.error || 'Upload failed.');
      return;
    }
    setVideoStatus(`Playing: ${data.filename}`);
  } catch (err) {
    setVideoStatus('Upload failed.');
  }
});

stopVideoBtn?.addEventListener('click', async () => {
  setVideoStatus('Stopping...');
  try {
    const response = await fetch('/api/video/stop', { method: 'POST' });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      setVideoStatus(data.error || 'Stop failed.');
      return;
    }
    setVideoStatus('Video stopped.');
  } catch (err) {
    setVideoStatus('Stop failed.');
  }
});

setInterval(() => { refreshStats(); refreshEvents(); }, 4000);
refreshStats();
refreshEvents();
