// Connects the dashboard to the Python backend (src/backend/main.py).
// app.js still draws everything. This file swaps the rotation ranking for the backend's answer,
// adds Gemini's plain-English explanations, and falls back to the built-in scoring and text
// in app.js whenever the backend can't be reached.

(() => {
  // Where the backend lives. Served by uvicorn it is the same address as the page.
  // Opened from a file or Live Server it looks for a backend on this computer.
  // On a public site like GitHub Pages it stays off unless window.FARMING_AURA_API
  // is set to the deployed backend URL before this script loads.
  const isLocalDevPort = ['localhost', '127.0.0.1'].includes(location.hostname) && location.port !== '' && location.port !== '8000' && location.port !== '7860';
  const isStaticGhPages = location.hostname.endsWith('.github.io');
  const API_BASE = window.FARMING_AURA_API !== undefined
    ? window.FARMING_AURA_API
    : (location.protocol === 'file:' || isLocalDevPort)
      ? 'http://localhost:8000'
      : isStaticGhPages
        ? null
        : '';
  if (API_BASE === null) return;

  const RETRY_AFTER_MS = 15000;
  const answers = new Map(); // request text -> backend response
  const waiting = new Set(); // requests that are in the air right now
  let backendDownSince = 0;
  let lastSource = null; // 'live', 'cache' or 'demo' from the latest backend answer we showed

  // untouched copy of the sample fields so NASA numbers can be removed again
  const sampleFields = JSON.parse(JSON.stringify(FIELDS_DATA));
  const localRanking = getRankedRotations;

  // What the dashboard currently shows. Used as the cache key and turned into the backend's format below.
  function buildRequest() {
    const latInput = document.getElementById('step1-lat-input');
    const lonInput = document.getElementById('step1-lon-input');
    const lat = parseFloat(latInput ? latInput.value : '');
    const lon = parseFloat(lonInput ? lonInput.value : '');
    return {
      field_id: appState.selectedFieldId,
      lat: Number.isFinite(lat) ? lat : null,
      lon: Number.isFinite(lon) ? lon : null,
      profile: appState.selectedProfile,
      selected_crops: appState.selectedCrops || [],
      previous_crop: appState.previousCropId,
      max_water: appState.maxWaterDemand,
      // same rule app.js uses, the dry MMS Mobile Measuring Station only counts while the sensor tab is open
      dry_probe: appState.sensorEnabled && appState.probeMode === 'dry' && appState.activeTab === 'sensors'
    };
  }

  // ---- Translating between the dashboard and the backend's /analyze (src/backend/main.py) ----
  const DRY_PROBE_SOIL_MOISTURE = 0.12; // volumetric water content the dry probe reading stands for
  const SELECTED_CROP_BONUS = 0.05; // per selected crop, so rotations using the farmer's picks rank first

  function toBackendPayload(request) {
    const payload = {
      lat: request.lat,
      lon: request.lon,
      selected_crops: request.selected_crops,
      previous_crop: request.previous_crop || null,
      profile_name: request.profile || 'Balanced',
      max_water_demand_mm: Number.isFinite(request.max_water) ? request.max_water : null,
      top_n: 20 // ask for plenty, a few can be dropped when they repeat a crop group the dashboard merges
    };
    if (request.dry_probe) payload.sensor_overrides = { soil_moisture: DRY_PROBE_SOIL_MOISTURE };
    return payload;
  }

  // The backend splits a few of the dashboard's merged crop groups (it has 17 crops, the dashboard 13).
  // Load its crop list once and add the extra ones so their names and numbers can be shown.
  let backendCropsLoaded = false;
  fetch(`${API_BASE}/crops`)
    .then((res) => (res.ok ? res.json() : null))
    .then((data) => {
      (data && data.crops ? data.crops : []).forEach((c) => {
        if (CROPS_DATA[c.crop_id]) return; // the dashboard's own wording wins for crops it already has
        CROPS_DATA[c.crop_id] = {
          id: c.crop_id,
          name: c.crop_name,
          type: c.crop_type,
          isPerennial: Boolean(c.is_perennial),
          roleTag: String(c.crop_type || 'crop').replace(/_/g, ' '),
          water: Number(c.water_demand_mm) || 450,
          nFix: Number(c.nitrogen_fixation) || 0,
          droughtTol: Number(c.drought_tolerance) || 0.5,
          phMin: Number(c.optimal_ph_min) || 6.0,
          phMax: Number(c.optimal_ph_max) || 7.0,
          clayMin: Number(c.optimal_clay_min) || 15,
          clayMax: Number(c.optimal_clay_max) || 35,
          yieldT: Number(c.typical_yield_t_ha) || 5,
          rootM: Number(c.root_depth_m) || 1,
          build: Number(c.soil_building_score) || 0.5
        };
      });
      backendCropsLoaded = true;
      if (answers.size) renderAll();
    })
    .catch(() => {});

  // Backend rotation row -> the row shape app.js draws
  function toDashboardRow(row, selectedIds) {
    const seqIds = String(row.seq_ids || '')
      .split('->')
      .map((s) => s.trim())
      .filter(Boolean);
    const crops = seqIds.map((id) => CROPS_DATA[id]);
    if (!seqIds.length || crops.some((c) => !c)) return null;
    const matchCount = seqIds.filter((id) => selectedIds.includes(id)).length;
    const totalScore = Number(row.total_score) || 0;
    return {
      seqIds,
      crops,
      label: crops.map((c) => c.name).join(' → '),
      totalScore,
      soilHealth: Number(row.soil_health) || 0,
      waterSafety: Number(row.water_stress) || 0, // backend's water_stress: higher = safer
      resilience: Number(row.climate_res) || 0,
      yieldPotential: Number(row.yield_potential) || 0,
      nFixAvg: Number(row.nitrogen_fixation) || 0,
      matchCount,
      sortScore: totalScore + SELECTED_CROP_BONUS * matchCount
    };
  }

  function toRankedRows(data, request) {
    const rows = (data.recommended_rotations || [])
      .map((row) => toDashboardRow(row, request.selected_crops))
      .filter(Boolean);
    rows.sort((a, b) => b.sortScore - a.sortScore || b.totalScore - a.totalScore);
    return rows;
  }

  // Real NASA POWER weather and USDA soil numbers, in the field keys app.js reads
  function toFieldUpdate(data) {
    const update = {};
    const put = (key, value) => {
      if (typeof value === 'number' && Number.isFinite(value)) update[key] = value;
    };
    const sources = data.data_sources || {};
    const climate = data.climate || {};
    const yearly = data.nasa_yearly || {};

    if (sources.nasa_power === 'live' || sources.nasa_power === 'cache') {
      put('tempSummer', climate.summer_temp_c);
      put('moistureAvg', climate.soil_moisture_avg);
      put('mapMoisture', climate.soil_moisture_avg);
      ['2023', '2024'].forEach((yr) => {
        put(`spring${yr}Precip`, (yearly.yearly_spring_precip_mm || {})[yr]);
        put(`summer${yr}Precip`, (yearly.yearly_summer_precip_mm || {})[yr]);
      });
    }
    // 'fallback' soil is a generic default loam, so only real USDA SSURGO readings replace the sample field
    if (sources.usda_soil && sources.usda_soil !== 'fallback') {
      const soil = data.soil || {};
      put('ph', soil.ph);
      put('oc', soil.organic_carbon_pct);
      put('clay', soil.clay_pct);
      put('sand', soil.sand_pct);
      put('bd', soil.bulk_density);
      put('cec', soil.cec);
      put('mapSoilScore', soil.baseline_soil_score);
    }
    return update;
  }

  // Put the backend's numbers onto the selected field, or put the sample numbers back
  function applyFieldUpdate(fieldId, update) {
    const field = FIELDS_DATA[fieldId];
    if (!field || !sampleFields[fieldId]) return;
    Object.assign(field, sampleFields[fieldId], update || {});
  }

  function askBackend(key, request) {
    if (waiting.has(key)) return;
    if (backendDownSince && Date.now() - backendDownSince < RETRY_AFTER_MS) return;
    if (request.lat === null || request.lon === null) return; // the backend needs a location
    waiting.add(key);

    fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(toBackendPayload(request))
    })
      .then((res) => {
        if (!res.ok) throw new Error(`backend said ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (!data || !Array.isArray(data.recommended_rotations) || !data.recommended_rotations.length) {
          throw new Error('empty answer');
        }
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
      const rows = toRankedRows(data, request);
      if (rows.length) {
        applyFieldUpdate(request.field_id, toFieldUpdate(data));
        lastSource = (data.data_sources || {}).nasa_power || 'demo';
        return rows;
      }
      // every row used a crop we couldn't show yet; the built-in ranking covers until /crops loads
      if (backendCropsLoaded) console.warn('[Farming Aura] backend rotations could not be shown, using built-in scoring.');
    }

    askBackend(key, request);
    if (backendDownSince) {
      applyFieldUpdate(request.field_id, null);
      lastSource = null;
    }
    return localRanking();
  };

  // ---- Gemini explanations (written by the backend's /explain route) ----
  const AI_WAIT_MS = 700; // wait for sliders to settle so we don't burn through the free rate limit
  const aiAnswers = new Map(); // request text -> the four explanation strings (or null if Gemini had nothing)
  const aiWaiting = new Set();
  let aiEnabled = true; // flips off if the backend says there is no GEMINI_API_KEY
  let aiTimer = null;

  // Same numbers the chart in app.js plots, so the explanation matches what the farmer sees
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
    const two = (n) => Number(n.toFixed(2));
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
        if (data.text && now && JSON.stringify(now) === key) renderDashboard();
      })
      .catch((err) => console.warn('[Farming Aura] Gemini explanation not available.', err.message))
      .finally(() => aiWaiting.delete(key));
  }

  // Swap the template sentences for Gemini's once they arrive, otherwise leave app.js's text alone
  function showGeminiText() {
    // /explain works on its own, so Gemini text shows even when /analyze can't rank for us
    if (!aiEnabled) return;
    const request = buildExplainRequest();
    if (!request) return;
    const key = JSON.stringify(request);
    const text = aiAnswers.get(key);

    const whyTag = document.getElementById('why-won-gemini-tag');
    const climateTag = document.getElementById('climate-gemini-tag');

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
      if (heading) {
        heading.textContent = heading.textContent.replace(/\s*·\s*Gemini\s*$/i, '');
      }
      if (whyTag) whyTag.style.display = 'inline-flex';
      if (climateTag) climateTag.style.display = 'inline-flex';
      return;
    }

    if (whyTag) whyTag.style.display = 'none';
    if (climateTag) climateTag.style.display = 'none';

    if (aiAnswers.has(key)) return; // already asked and Gemini had nothing
    clearTimeout(aiTimer);
    aiTimer = setTimeout(() => {
      const latest = buildExplainRequest();
      if (latest && JSON.stringify(latest) === key) askGemini(key, latest);
    }, AI_WAIT_MS);
  }

  // After app.js draws the dashboard, say where the numbers came from and add the Gemini text
  const drawDashboard = renderDashboard;
  renderDashboard = function () {
    drawDashboard();
    const eyebrow = document.getElementById('dash-eyebrow-text');
    const labels = {
      live: 'PYTHON BACKEND · NASA POWER LIVE',
      cache: 'PYTHON BACKEND · NASA POWER (SAVED COPY)',
      demo: 'PYTHON BACKEND · SAMPLE CLIMATE DATA'
    };
    if (eyebrow && lastSource && labels[lastSource]) {
      eyebrow.textContent = eyebrow.textContent.replace('DEMO DATA', labels[lastSource]);
    }
    showGeminiText();
  };

  // handy in the browser console: FarmingAuraAPI.status()
  window.FarmingAuraAPI = {
    status: () => ({ apiBase: API_BASE || location.origin, connected: lastSource !== null, nasa: lastSource, gemini: aiEnabled }),
    request: buildRequest
  };
})();
