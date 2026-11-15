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
    let lat = parseFloat(latInput ? latInput.value : '');
    let lon = parseFloat(lonInput ? lonInput.value : '');

    // If the active field has a custom polygon drawn on the Google satellite map, use its center coordinates
    const poly = appState.fieldPolygons && appState.fieldPolygons[appState.selectedFieldNumber];
    if (Array.isArray(poly) && poly.length > 0) {
      lat = poly.reduce((s, p) => s + p.lat, 0) / poly.length;
      lon = poly.reduce((s, p) => s + p.lng, 0) / poly.length;
    } else if ((!Number.isFinite(lat) || !Number.isFinite(lon)) && appState.farmLocation) {
      lat = appState.farmLocation.lat;
      lon = appState.farmLocation.lon;
    }

    return {
      field_id: appState.selectedFieldId,
      city: appState.selectedCity,
      lat: Number.isFinite(lat) ? Number(lat.toFixed(4)) : null,
      lon: Number.isFinite(lon) ? Number(lon.toFixed(4)) : null,
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

  // The backend sends crop ids, app.js wants the full crop objects
  function toDashboardShape(row) {
    return { ...row, crops: row.seqIds.map((id) => CROPS_DATA[id]).filter(Boolean) };
  }

  const MONTH_DAYS_JS = { 1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31 };

  async function fetchDirectNasaUpdate(lat, lon) {
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
    const url =
      `https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=ALLSKY_SFC_SW_DWN,WS2M,PRECTOTCORR,T2M,TS,GWETROOT` +
      `&community=AG&latitude=${lat.toFixed(4)}&longitude=${lon.toFixed(4)}&start=2020&end=2024&format=JSON`;
    const res = await fetch(url);
    if (!res.ok) return null;
    const json = await res.json();
    const p = (json.properties && json.properties.parameter) || {};
    const rain = p.PRECTOTCORR || {};
    const t2m = p.T2M || {};
    const ts = p.TS || {};
    const gwet = p.GWETROOT || {};

    const sumMonths = (series, yr, months) => {
      let tot = 0;
      let count = 0;
      for (const m of months) {
        const v = series[`${yr}${String(m).padStart(2, '0')}`];
        if (typeof v === 'number' && v > -900) {
          tot += v * MONTH_DAYS_JS[m];
          count++;
        }
      }
      return count === months.length ? Math.round(tot) : null;
    };

    const rain5 = [];
    const temp5 = [];
    for (const yr of [2020, 2021, 2022, 2023, 2024]) {
      const sp = sumMonths(rain, yr, [3, 4, 5]);
      const su = sumMonths(rain, yr, [6, 7, 8]);
      if (sp !== null && su !== null) rain5.push(sp + su);
      const tVals = [6, 7, 8]
        .map((m) => t2m[`${yr}${String(m).padStart(2, '0')}`])
        .filter((v) => typeof v === 'number' && v > -900);
      if (tVals.length) temp5.push(Number((tVals.reduce((a, b) => a + b, 0) / tVals.length).toFixed(1)));
    }

    const sp23 = sumMonths(rain, 2023, [3, 4, 5]);
    const su23 = sumMonths(rain, 2023, [6, 7, 8]);
    const sp24 = sumMonths(rain, 2024, [3, 4, 5]);
    const su24 = sumMonths(rain, 2024, [6, 7, 8]);
    const ann24 = sumMonths(rain, 2024, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]);
    if (sp24 === null || su24 === null) return null;

    const gwetVals = [4, 5, 6, 7, 8, 9]
      .map((m) => gwet[`2024${String(m).padStart(2, '0')}`])
      .filter((v) => typeof v === 'number' && v > -900);
    const tsVals = [5, 6, 7, 8, 9]
      .map((m) => ts[`2024${String(m).padStart(2, '0')}`])
      .filter((v) => typeof v === 'number' && v > -900);
    const suTempVals = [6, 7, 8]
      .map((m) => t2m[`2024${String(m).padStart(2, '0')}`])
      .filter((v) => typeof v === 'number' && v > -900);

    const moistureAvg = gwetVals.length
      ? Number((gwetVals.reduce((a, b) => a + b, 0) / gwetVals.length).toFixed(2))
      : 0.65;
    const soilTempC = tsVals.length
      ? Number((tsVals.reduce((a, b) => a + b, 0) / tsVals.length).toFixed(1))
      : 19.0;
    const tempSummer = suTempVals.length
      ? Number((suTempVals.reduce((a, b) => a + b, 0) / suTempVals.length).toFixed(1))
      : 21.0;

    return {
      lat: Number(lat.toFixed(4)),
      lon: Number(lon.toFixed(4)),
      spring2023Precip: sp23 !== null ? sp23 : sp24,
      summer2023Precip: su23 !== null ? su23 : su24,
      spring2024Precip: sp24,
      summer2024Precip: su24,
      annualTotalMm: ann24 !== null ? ann24 : Math.round((sp24 + su24) * 1.6),
      moistureAvg,
      mapMoisture: moistureAvg,
      tempSummer,
      soilTempC,
      rainSeries2020_2024: rain5.length === 5 ? rain5 : undefined,
      tempSeries2020_2024: temp5.length === 5 ? temp5 : undefined,
      nasaSource: 'live'
    };
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
      .catch(async (err) => {
        if (!backendDownSince) console.warn('[Farming Aura] backend not reachable, querying NASA POWER directly.', err.message);
        try {
          const directUpdate = await fetchDirectNasaUpdate(request.lat, request.lon);
          if (directUpdate) {
            applyFieldUpdate(request.field_id, directUpdate);
            const rankedLocal = localRanking();
            answers.set(key, {
              nasa_source: 'live',
              field_update: directUpdate,
              ranked: rankedLocal.map((r) => ({ ...r, seqIds: r.crops.map((c) => c.id) }))
            });
            lastSource = 'live';
            if (JSON.stringify(buildRequest()) === key) renderAll();
            return;
          }
        } catch (_nasaErr) {
          // ignore
        }
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

    // Backend was down and NASA POWER answered directly: built-in ranking plus real NASA numbers
    if (data && Array.isArray(data.ranked)) {
      applyFieldUpdate(request.field_id, data.field_update);
      lastSource = data.nasa_source || 'live';
      return data.ranked.map(toDashboardShape);
    }

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

  // Same numbers the chart in app.js plots (true 2020-2024 NASA POWER PRECTOTCORR & T2M series)
  function climateSeries(field) {
    const rain2023 = Math.round(field.spring2023Precip + field.summer2023Precip);
    const rain2024 = Math.round(field.spring2024Precip + field.summer2024Precip);
    const t = Number(field.tempSummer || 21.0);
    return {
      years: [2020, 2021, 2022, 2023, 2024],
      rain:
        Array.isArray(field.rainSeries2020_2024) && field.rainSeries2020_2024.length === 5
          ? field.rainSeries2020_2024.map((v) => Math.round(Number(v)))
          : [rain2023, rain2023, rain2023, rain2023, rain2024],
      temp:
        Array.isArray(field.tempSeries2020_2024) && field.tempSeries2020_2024.length === 5
          ? field.tempSeries2020_2024.map((v) => Number(Number(v).toFixed(1)))
          : [t, t, t, t, t]
    };
  }

  function buildExplainRequest() {
    const ranked = getRankedRotations();
    const top = ranked[appState.selectedRankIndex] || ranked[0];
    const field = FIELDS_DATA[appState.selectedFieldId] || FIELDS_DATA.F001;
    if (!top) return null;
    const reqCoords = buildRequest();
    const series = climateSeries(field);
    const probeCounts = appState.sensorEnabled && appState.activeTab === 'sensors';
    const two = (n) => Number(Number(n || 0).toFixed(2));
    const annualRain = Math.round(field.spring2024Precip + field.summer2024Precip);
    return {
      field_number: appState.selectedFieldNumber,
      city: appState.selectedCity,
      lat: reqCoords.lat !== null ? reqCoords.lat : field.lat,
      lon: reqCoords.lon !== null ? reqCoords.lon : field.lon,
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
      nasa_kpis: {
        soil_health_score: two(top.soilHealth),
        soil_oc_pct: Number(field.oc.toFixed(1)),
        soil_ph: Number(field.ph.toFixed(1)),
        annual_rainfall_mm: annualRain,
        annual_total_mm: field.annualTotalMm || Math.round(annualRain * 1.8),
        root_zone_moisture: two(field.moistureAvg),
        soil_temp_c: Number(field.soilTempC.toFixed(1))
      },
      ranked_alternatives: ranked.slice(0, 5).map((r) => ({
        label: r.label,
        total_score: two(r.totalScore),
        soil_health: two(r.soilHealth),
        water_safety: two(r.waterSafety),
        yield_potential: two(r.yieldPotential),
        nitrogen_fixation: two(r.nFixAvg)
      })),
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

    // "Generated from Gemini" tags only show while Gemini's own text is on screen
    const geminiTags = ['why-won-gemini-tag', 'climate-gemini-tag', 'banner-gemini-tag', 'sequence-gemini-tag']
      .map((id) => document.getElementById(id))
      .filter(Boolean);

    if (text) {
      const put = (id, value) => {
        const el = document.getElementById(id);
        if (el && value) el.textContent = value;
      };
      put('why-won-line-1', text.why_line_1);
      put('why-won-line-2', text.why_line_2);
      put('banner-sequence-analysis-text', text.sequence_analysis);
      put('sequence-analysis-text', text.sequence_analysis);
      put('climate-temp-explanation', text.temp_explanation);
      put('climate-rain-explanation', text.rain_explanation);
      if (Array.isArray(text.ranked_analyses)) {
        text.ranked_analyses.forEach((line, idx) => {
          put(`ranked-row-analysis-${idx}`, line);
        });
      }
      const heading = document.getElementById('why-won-heading');
      if (heading) {
        heading.textContent = heading.textContent.replace(/\s*·\s*Gemini\s*$/i, '');
      }
      geminiTags.forEach((tag) => {
        tag.style.display = 'inline-flex';
      });
      return;
    }

    geminiTags.forEach((tag) => {
      tag.style.display = 'none';
    });

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
      live: 'NASA POWER LIVE',
      cache: 'NASA POWER',
      demo: 'SAMPLE CLIMATE DATA'
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
