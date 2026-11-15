// Connects the dashboard to the Python backend (src/backend/main.py).
// app.js draws everything. This file connects the backend algorithms:
// 1. Sends frontend dropdown inputs (GPS coords, previous crop, selected crops, profile, water demand) to POST /analyze
// 2. Receives NASA POWER climate data, USDA SSURGO soil lab data, and ranked crop rotations
// 3. Updates the dashboard KPIs (Soil health, pH, OC, Annual rainfall, 1-mo precip, Soil moisture, Soil temp, Air temp, N-fixation)
// 4. Feeds Gemini AI plain-English rotation explanations via POST /explain

(() => {
  const onThisComputer = location.protocol === 'file:' || ['localhost', '127.0.0.1'].includes(location.hostname);
  const sameServer = onThisComputer && location.port === '8000';
  const API_BASE = window.FARMING_AURA_API || (sameServer ? '' : onThisComputer ? 'http://localhost:8000' : null);
  if (API_BASE === null) return;

  const RETRY_AFTER_MS = 10000;
  const answers = new Map(); // request text -> backend response
  const waiting = new Set(); // requests currently in flight
  let backendDownSince = 0;
  let lastSource = null;

  // Untouched copy of sample fields so we can blend or restore cleanly
  const sampleFields = typeof FIELDS_DATA !== 'undefined' ? JSON.parse(JSON.stringify(FIELDS_DATA)) : {};
  const localRanking = typeof getRankedRotations === 'function' ? getRankedRotations : () => [];

  // 1. GATHER ALL FRONTEND INPUTS FROM DROPDOWNS & MAP CONTROLS
  function buildRequest() {
    const latInput = document.getElementById('step1-lat-input');
    const lonInput = document.getElementById('step1-lon-input');
    const inputLat = parseFloat(latInput ? latInput.value : '');
    const inputLon = parseFloat(lonInput ? lonInput.value : '');

    const city = (typeof CITY_LOCATIONS !== 'undefined' && appState.selectedCity)
      ? CITY_LOCATIONS[appState.selectedCity]
      : null;

    const lat = Number.isFinite(inputLat)
      ? inputLat
      : (appState.farmLocation?.lat ?? (city ? parseFloat(city.lat) : 42.6526));
    const lon = Number.isFinite(inputLon)
      ? inputLon
      : (appState.farmLocation?.lon ?? (city ? parseFloat(city.lon) : -73.7562));

    return {
      field_id: appState.selectedFieldId || 'F001',
      city: appState.selectedCity || 'Albany',
      lat: Number.isFinite(lat) ? lat : 42.6526,
      lon: Number.isFinite(lon) ? lon : -73.7562,
      profile: appState.selectedProfile || 'Balanced',
      profile_name: appState.selectedProfile || 'Balanced',
      intensity: appState.profileIntensity || 50,
      selected_crops: (appState.selectedCrops && appState.selectedCrops.length) ? appState.selectedCrops : ['C01', 'C02', 'C03'],
      previous_crop: appState.previousCropId || 'C02',
      max_water: appState.maxWaterDemand || 550,
      max_water_demand_mm: appState.maxWaterDemand || 550,
      rotation_length: 3,
      top_n: 5,
      dry_probe: appState.sensorEnabled && appState.probeMode === 'dry' && appState.activeTab === 'sensors'
    };
  }

  // 2. APPLY BACKEND NASA & USDA VALUES TO ALL FIELDS IN FIELDS_DATA
  function applyFieldUpdate(fieldId, update) {
    if (!update || typeof FIELDS_DATA === 'undefined') return;
    Object.keys(FIELDS_DATA).forEach((fid) => {
      const f = FIELDS_DATA[fid];
      if (f) Object.assign(f, update);
    });
  }

  // 3. CONVERT BACKEND ROTATION SHAPE INTO DASHBOARD OBJECT
  function toDashboardShape(row) {
    const seq = Array.isArray(row.seqIds)
      ? row.seqIds
      : (typeof row.seq_ids === 'string' ? row.seq_ids.split('->').map((s) => s.trim()) : []);

    const crops = seq.map((id) => {
      if (typeof CROPS_DATA !== 'undefined' && CROPS_DATA[id]) return CROPS_DATA[id];
      return {
        id,
        name: id,
        roleTag: 'Crop rotation partner',
        water: 400,
        nFix: 0.5,
        droughtTol: 0.5,
        type: 'cover',
        isPerennial: false
      };
    });

    return {
      ...row,
      seqIds: seq,
      crops,
      label: row.label || row.seq_names || crops.map((c) => c.name).join(' → '),
      totalScore: Number(row.totalScore ?? row.total_score ?? 0.75),
      soilHealth: Number(row.soilHealth ?? row.soil_health ?? 0.75),
      waterSafety: Number(row.waterSafety ?? row.water_stress ?? 0.8),
      resilience: Number(row.resilience ?? row.climate_res ?? 0.8),
      yieldPotential: Number(row.yieldPotential ?? row.yield_potential ?? 0.7),
      nFixAvg: Number(row.nFixAvg ?? row.nitrogen_fixation ?? 0.6)
    };
  }

  // 4. SEND INPUTS TO BACKEND AND RECEIVE DATA
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
        if (!res.ok) throw new Error(`backend status ${res.status}`);
        return res.json();
      })
      .then((data) => {
        const rawRotations = data.ranked || data.recommended_rotations;
        if (!data || !Array.isArray(rawRotations) || !rawRotations.length) throw new Error('empty rotation list');
        backendDownSince = 0;

        // Ensure ranked array is formatted
        data.ranked = rawRotations.map(toDashboardShape);

        // Save into memory cache
        answers.set(key, data);

        // Update USDA soil and NASA climate numbers
        applyFieldUpdate(request.field_id, data.field_update);
        lastSource = data.nasa_source || (data.data_sources?.nasa_power) || 'live';

        // Re-render dashboard if user state still matches
        if (JSON.stringify(buildRequest()) === key && typeof renderAll === 'function') {
          renderAll();
        }
      })
      .catch((err) => {
        if (!backendDownSince) console.warn('[Farming Aura] backend analyze failed, using fallback:', err.message);
        backendDownSince = Date.now();
        const hadBackend = lastSource !== null;
        lastSource = null;
        if (hadBackend && typeof renderAll === 'function') renderAll();
      })
      .finally(() => waiting.delete(key));
  }

  // 5. INTERCEPT getRankedRotations CALLED BY app.js
  getRankedRotations = function () {
    const request = buildRequest();
    const key = JSON.stringify(request);
    const data = answers.get(key);

    if (data && Array.isArray(data.ranked) && data.ranked.length) {
      applyFieldUpdate(request.field_id, data.field_update);
      lastSource = data.nasa_source || (data.data_sources?.nasa_power) || 'live';
      return data.ranked.map(toDashboardShape);
    }

    // Trigger backend fetch
    askBackend(key, request);

    if (backendDownSince) {
      lastSource = null;
    }
    return localRanking();
  };

  // 6. GEMINI AI EXPLANATIONS
  const AI_WAIT_MS = 600;
  const aiAnswers = new Map();
  const aiWaiting = new Set();
  let aiEnabled = true;
  let aiTimer = null;

  function climateSeries(field) {
    const rain2023 = Math.round(field.spring2023Precip + field.summer2023Precip);
    const rain2024 = Math.round(field.spring2024Precip + field.summer2024Precip);
    const rainStep = Math.round((rain2024 - rain2023) * 0.45);
    const tempDrift = rain2024 < rain2023 ? 0.35 : -0.2;
    const t = field.tempSummer;
    return {
      years: [2020, 2021, 2022, 2023, 2024],
      rain: [
        clip(rain2023 - rainStep * 2 + 18, 360, 780),
        clip(rain2023 - rainStep - 12, 360, 780),
        clip(rain2023 + 14, 360, 780),
        rain2023,
        rain2024
      ],
      temp: [3.6, 2.5, 1.8, 0.9, 0].map((k) => Number((t - tempDrift * k).toFixed(1)))
    };
  }

  function buildExplainRequest() {
    const ranked = getRankedRotations();
    const top = ranked[appState.selectedRankIndex] || ranked[0];
    const field = FIELDS_DATA[appState.selectedFieldId] || FIELDS_DATA.F001;
    if (!top) return null;
    const series = climateSeries(field);
    const probeCounts = appState.sensorEnabled && appState.activeTab === 'sensors';
    const two = (n) => Number(Number(n || 0).toFixed(2));
    return {
      field_number: appState.selectedFieldNumber,
      city: appState.selectedCity,
      profile: appState.selectedProfile,
      previous_crop: appState.previousCropId,
      max_water: appState.maxWaterDemand,
      probe: probeCounts ? appState.probeMode : 'off',
      rotation: top.seqIds,
      scores: {
        soil_health: two(top.soilHealth),
        water_safety: two(top.waterSafety),
        resilience: two(top.resilience),
        yield_potential: two(top.yieldPotential),
        nitrogen_fixation: two(top.nFixAvg)
      },
      total_score: two(top.totalScore),
      years: series.years,
      summer_temp_c: series.temp,
      season_rain_mm: series.rain
    };
  }

  function askGemini(key, request) {
    if (aiWaiting.has(key) || aiAnswers.has(key)) return;
    aiWaiting.add(key);
    fetch(`${API_BASE}/explain`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    })
      .then((res) => {
        if (!res.ok) throw new Error(`backend said ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (data.enabled === false) aiEnabled = false;
        aiAnswers.set(key, data.text || null);
        const now = buildExplainRequest();
        if (data.text && now && JSON.stringify(now) === key && typeof renderDashboard === 'function') {
          renderDashboard();
        }
      })
      .catch((err) => console.warn('[Farming Aura] Gemini explanation not available.', err.message))
      .finally(() => aiWaiting.delete(key));
  }

  function showGeminiText() {
    if (!aiEnabled) return;
    const request = buildExplainRequest();
    if (!request) return;
    const key = JSON.stringify(request);
    const text = aiAnswers.get(key);

    if (text) {
      const put = (id, value) => {
        const el = document.getElementById(id);
        if (el && value) el.textContent = value;
      };
      put('why-won-line-1', text.why_line_1);
      put('why-won-line-2', text.why_line_2);
      put('climate-temp-explanation', text.temp_explanation);
      put('climate-rain-explanation', text.rain_explanation);
      const heading = document.getElementById('why-won-heading');
      if (heading && !heading.textContent.endsWith('· Gemini')) heading.textContent += ' · Gemini';
      return;
    }

    if (aiAnswers.has(key)) return;
    clearTimeout(aiTimer);
    aiTimer = setTimeout(() => {
      const latest = buildExplainRequest();
      if (latest && JSON.stringify(latest) === key) askGemini(key, latest);
    }, AI_WAIT_MS);
  }

  // 7. AFTER DRAWING DASHBOARD, UPDATE BADGES & TRIGGER GEMINI
  const drawDashboard = typeof renderDashboard === 'function' ? renderDashboard : () => {};
  renderDashboard = function () {
    drawDashboard();
    const eyebrow = document.getElementById('dash-eyebrow-text');
    const labels = {
      live: 'PYTHON BACKEND · NASA POWER & USDA LIVE',
      cache: 'PYTHON BACKEND · NASA POWER & USDA (SAVED COPY)',
      demo: 'PYTHON BACKEND · SAMPLE CLIMATE DATA'
    };
    if (eyebrow && lastSource && labels[lastSource]) {
      eyebrow.textContent = eyebrow.textContent.replace('DEMO DATA', labels[lastSource]);
    }
    showGeminiText();
  };

  window.FarmingAuraAPI = {
    status: () => ({ apiBase: API_BASE || location.origin, connected: lastSource !== null, nasa: lastSource, gemini: aiEnabled }),
    request: buildRequest
  };
})();
