// Connects the dashboard to the Python backend (src/backend/main.py).
// app.js still draws everything. This file swaps the rotation ranking for the backend's answer
// and falls back to the built-in scoring in app.js whenever the backend can't be reached.

(() => {
  // Where the backend lives. Served by uvicorn it is the same address as the page.
  // Opened from a file or Live Server it looks for a backend on this computer.
  // On a public site like GitHub Pages it stays off unless window.FARMING_AURA_API
  // is set to the deployed backend URL before this script loads.
  const onThisComputer = location.protocol === 'file:' || ['localhost', '127.0.0.1'].includes(location.hostname);
  const sameServer = onThisComputer && location.port === '8000';
  const API_BASE = window.FARMING_AURA_API || (sameServer ? '' : onThisComputer ? 'http://localhost:8000' : null);
  if (API_BASE === null) return;

  const RETRY_AFTER_MS = 15000;
  const answers = new Map(); // request text -> backend response
  const waiting = new Set(); // requests that are in the air right now
  let backendDownSince = 0;
  let lastSource = null; // 'live', 'cache' or 'demo' from the latest backend answer we showed

  // untouched copy of the sample fields so NASA numbers can be removed again
  const sampleFields = JSON.parse(JSON.stringify(FIELDS_DATA));
  const localRanking = getRankedRotations;

  function buildRequest() {
    const latInput = document.getElementById('step1-lat-input');
    const lonInput = document.getElementById('step1-lon-input');
    const lat = parseFloat(latInput ? latInput.value : '');
    const lon = parseFloat(lonInput ? lonInput.value : '');
    return {
      field_id: appState.selectedFieldId,
      city: appState.selectedCity,
      lat: Number.isFinite(lat) ? lat : null,
      lon: Number.isFinite(lon) ? lon : null,
      profile: appState.selectedProfile,
      intensity: appState.profileIntensity,
      selected_crops: appState.selectedCrops || [],
      previous_crop: appState.previousCropId,
      max_water: appState.maxWaterDemand,
      // same rule app.js uses, the dry probe only counts while the sensor tab is open
      dry_probe: appState.sensorEnabled && appState.probeMode === 'dry' && appState.activeTab === 'sensors'
    };
  }

  // Put NASA's rain and temperature onto the selected field, or put the sample numbers back
  function applyFieldUpdate(fieldId, update) {
    const field = FIELDS_DATA[fieldId];
    if (!field || !sampleFields[fieldId]) return;
    Object.assign(field, sampleFields[fieldId], update || {});
  }

  // The backend sends crop ids, app.js wants the full crop objects
  function toDashboardShape(row) {
    return { ...row, crops: row.seqIds.map((id) => CROPS_DATA[id]).filter(Boolean) };
  }

  function askBackend(key, request) {
    if (waiting.has(key)) return;
    if (backendDownSince && Date.now() - backendDownSince < RETRY_AFTER_MS) return;
    waiting.add(key);

    fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    })
      .then((res) => {
        if (!res.ok) throw new Error(`backend said ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (!data || !Array.isArray(data.ranked) || !data.ranked.length) throw new Error('empty answer');
        backendDownSince = 0;
        answers.set(key, data);
        // only redraw if the farmer hasn't changed something else in the meantime
        if (JSON.stringify(buildRequest()) === key) renderAll();
      })
      .catch((err) => {
        if (!backendDownSince) console.warn('[Farming Aura] backend not reachable, using built-in scoring.', err.message);
        backendDownSince = Date.now();
        const hadBackend = lastSource !== null;
        lastSource = null;
        if (hadBackend) renderAll();
      })
      .finally(() => waiting.delete(key));
  }

  // app.js calls this every time it redraws
  getRankedRotations = function () {
    const request = buildRequest();
    const key = JSON.stringify(request);
    const data = answers.get(key);

    if (data) {
      applyFieldUpdate(request.field_id, data.field_update);
      lastSource = data.nasa_source;
      return data.ranked.map(toDashboardShape);
    }

    askBackend(key, request);
    if (backendDownSince) {
      applyFieldUpdate(request.field_id, null);
      lastSource = null;
    }
    return localRanking();
  };

  // After app.js draws the dashboard, say where the numbers came from
  const drawDashboard = renderDashboard;
  renderDashboard = function () {
    drawDashboard();
    const eyebrow = document.getElementById('dash-eyebrow-text');
    if (!eyebrow) return;
    const labels = {
      live: 'PYTHON BACKEND · NASA POWER LIVE',
      cache: 'PYTHON BACKEND · NASA POWER (SAVED COPY)',
      demo: 'PYTHON BACKEND · SAMPLE CLIMATE DATA'
    };
    if (lastSource && labels[lastSource]) {
      eyebrow.textContent = eyebrow.textContent.replace('DEMO DATA', labels[lastSource]);
    }
  };

  // handy in the browser console: FarmingAuraAPI.status()
  window.FarmingAuraAPI = {
    status: () => ({ apiBase: API_BASE || location.origin, connected: lastSource !== null, nasa: lastSource }),
    request: buildRequest
  };
})();
