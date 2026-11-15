// Frontend-to-Backend Connector for Farming Aura (Field Shift)
// Bridges client-side `appState` and UI rendering in `app.js` with `src/backend/frontend_bridge.py` (`POST /api/frontend-sync`).
// Automatically falls back to the built-in client-side engine when opened offline or without the Python server running.

(function () {
  const CANDIDATE_API_BASES = [
    window.FARMING_AURA_API_URL,
    window.location.protocol.startsWith('http') ? window.location.origin : null,
    'http://127.0.0.1:8000',
    'http://localhost:8000'
  ].filter(Boolean);

  const bridgeState = {
    apiBaseUrl: null,
    connected: false,
    checking: false,
    syncTimer: null,
    inFlightController: null,
    lastSignature: '',
    lastResponse: null,
    applyingUpdate: false
  };

  window.FarmingAuraBridge = bridgeState;

  function buildStateSignature() {
    if (typeof appState === 'undefined') return '';
    const latInput = document.getElementById('step1-lat-input');
    const lonInput = document.getElementById('step1-lon-input');
    return JSON.stringify({
      activeTab: appState.activeTab,
      city: appState.selectedCity,
      fieldId: appState.selectedFieldId,
      fieldNum: appState.selectedFieldNumber,
      lat: latInput ? latInput.value.trim() : null,
      lon: lonInput ? lonInput.value.trim() : null,
      prevCrop: appState.previousCropId,
      profile: appState.selectedProfile,
      intensity: appState.profileIntensity,
      crops: [...(appState.selectedCrops || [])].sort(),
      water: appState.maxWaterDemand,
      sensorEnabled: appState.sensorEnabled,
      probeMode: appState.probeMode
    });
  }

  function buildRequestPayload() {
    const cityInfo =
      typeof CITY_LOCATIONS !== 'undefined' && CITY_LOCATIONS[appState.selectedCity]
        ? CITY_LOCATIONS[appState.selectedCity]
        : null;

    const latInput = document.getElementById('step1-lat-input');
    const lonInput = document.getElementById('step1-lon-input');
    const rawLatStr = latInput ? latInput.value.trim() : '';
    const rawLonStr = lonInput ? lonInput.value.trim() : '';
    const parsedLat = parseFloat(rawLatStr);
    const parsedLon = parseFloat(rawLonStr);

    const isDefaultCityCoord =
      cityInfo &&
      Math.abs(parsedLat - parseFloat(cityInfo.lat)) < 0.0005 &&
      Math.abs(parsedLon - parseFloat(cityInfo.lon)) < 0.0005;

    const customCoords =
      !Number.isNaN(parsedLat) &&
      !Number.isNaN(parsedLon) &&
      !isDefaultCityCoord;

    return {
      activeTab: appState.activeTab,
      selectedCity: appState.selectedCity,
      selectedFieldId: appState.selectedFieldId,
      selectedFieldNumber: appState.selectedFieldNumber,
      customCoords,
      lat: !Number.isNaN(parsedLat) ? parsedLat : undefined,
      lon: !Number.isNaN(parsedLon) ? parsedLon : undefined,
      previousCropId: appState.previousCropId,
      selectedProfile: appState.selectedProfile,
      profileIntensity: appState.profileIntensity,
      selectedCrops: [...(appState.selectedCrops || [])],
      maxWaterDemand: appState.maxWaterDemand,
      sensorEnabled: appState.sensorEnabled,
      probeMode: appState.probeMode
    };
  }

  async function detectBackendServer() {
    if (bridgeState.checking) return bridgeState.connected;
    bridgeState.checking = true;

    for (const base of CANDIDATE_API_BASES) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 1200);
        const resp = await fetch(`${base}/health`, {
          method: 'GET',
          headers: { Accept: 'application/json' },
          signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (resp.ok) {
          const data = await resp.json();
          if (data && data.status === 'ok') {
            bridgeState.apiBaseUrl = base;
            bridgeState.connected = true;
            bridgeState.checking = false;
            return true;
          }
        }
      } catch (_err) {
        // Ignore connection error and try next candidate base URL or fall back to offline mode
      }
    }

    bridgeState.connected = false;
    bridgeState.checking = false;
    return false;
  }

  function applyBackendOverlayToDom(data) {
    if (!data || !data.connected) return;

    const activeFieldCode =
      typeof formatFieldCode === 'function'
        ? formatFieldCode(appState.selectedFieldNumber)
        : appState.selectedFieldId;

    const dashEyebrow = document.getElementById('dash-eyebrow-text');
    if (dashEyebrow && data.field) {
      const nasaSrc = (data.dataSources && data.dataSources.nasa_power) || 'cache';
      const soilSrc = (data.dataSources && data.dataSources.usda_soil) || 'cache';
      dashEyebrow.textContent = `FIELD ${activeFieldCode} / BACKEND CONNECTED (NASA: ${nasaSrc.toUpperCase()} · USDA: ${soilSrc.toUpperCase()})`;
    }

    const sensorStatus = document.getElementById('sidebar-sensor-status');
    if (sensorStatus) {
      sensorStatus.textContent = appState.sensorEnabled
        ? 'Enabled · live backend'
        : 'Disabled · NASA satellite only';
    }

    if (data.sensorReport) {
      const sr = data.sensorReport;
      const nasaRzm = document.getElementById('sensor-nasa-rzm');
      const nasaTemp = document.getElementById('sensor-nasa-temp');
      const nasaPrecip = document.getElementById('sensor-nasa-precip');
      const devRzm = document.getElementById('sensor-dev-rzm');
      const devSt = document.getElementById('sensor-dev-st');
      const devAh = document.getElementById('sensor-dev-ah');
      const alertTitle = document.getElementById('sensor-alert-title');
      const alertSub = document.getElementById('sensor-alert-sub');
      const backendHeading = document.getElementById('moisture-backend-heading');
      const backendLine1 = document.getElementById('moisture-backend-line-1');
      const backendLine2 = document.getElementById('moisture-backend-line-2');

      if (nasaRzm && sr.nasaRzm !== undefined) nasaRzm.textContent = `${Number(sr.nasaRzm).toFixed(2)} m³/m³`;
      if (nasaTemp && sr.nasaTempC !== undefined) nasaTemp.textContent = `${Number(sr.nasaTempC).toFixed(1)} °C`;
      if (nasaPrecip && sr.nasaPrecipMm !== undefined) nasaPrecip.textContent = `${sr.nasaPrecipMm} mm`;
      if (devRzm && sr.probeRzm !== undefined) {
        const modeLabel = sr.mode === 'dry' ? 'Dry' : 'Wet';
        devRzm.textContent = `${Number(sr.probeRzm).toFixed(2)} m³/m³ (${modeLabel})`;
      }
      if (devSt && sr.probeSoilTempC !== undefined) devSt.textContent = `${Number(sr.probeSoilTempC).toFixed(1)} °C`;
      if (devAh && sr.humidityPct !== undefined) devAh.textContent = `${sr.humidityPct} % RH`;
      if (alertTitle && sr.alertTitle) alertTitle.textContent = sr.alertTitle;
      if (alertSub && sr.alertSub) alertSub.textContent = sr.alertSub;
      if (backendHeading && sr.heading) backendHeading.textContent = sr.heading;
      if (backendLine1 && sr.line1) backendLine1.textContent = sr.line1;
      if (backendLine2 && sr.line2) backendLine2.textContent = sr.line2;
    }
  }

  async function syncWithBackend(force = false) {
    const sig = buildStateSignature();
    if (!force && sig === bridgeState.lastSignature && bridgeState.lastResponse) {
      applyBackendOverlayToDom(bridgeState.lastResponse);
      return bridgeState.lastResponse;
    }

    if (!bridgeState.connected) {
      const ok = await detectBackendServer();
      if (!ok) return null;
    }

    if (bridgeState.inFlightController) {
      bridgeState.inFlightController.abort();
    }
    const controller = new AbortController();
    bridgeState.inFlightController = controller;

    try {
      const payload = buildRequestPayload();
      const resp = await fetch(`${bridgeState.apiBaseUrl}/api/frontend-sync`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json'
        },
        body: JSON.stringify(payload),
        signal: controller.signal
      });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      const data = await resp.json();
      if (sig !== buildStateSignature()) {
        return null;
      }

      bridgeState.lastSignature = sig;
      bridgeState.lastResponse = data;

      if (data.field && typeof FIELDS_DATA !== 'undefined') {
        const fid = appState.selectedFieldId || 'F001';
        FIELDS_DATA[fid] = { ...(FIELDS_DATA[fid] || {}), ...data.field };
      }

      if (typeof window._originalRenderDashboard === 'function') {
        bridgeState.applyingUpdate = true;
        window._originalRenderDashboard();
        applyBackendOverlayToDom(data);
        bridgeState.applyingUpdate = false;
      }

      return data;
    } catch (err) {
      if (err && err.name === 'AbortError') {
        return null;
      }
      bridgeState.connected = false;
      return null;
    } finally {
      if (bridgeState.inFlightController === controller) {
        bridgeState.inFlightController = null;
      }
    }
  }

  function scheduleBackendSync() {
    if (bridgeState.applyingUpdate) return;
    if (bridgeState.syncTimer) clearTimeout(bridgeState.syncTimer);
    bridgeState.syncTimer = setTimeout(() => {
      syncWithBackend(false);
    }, 120);
  }

  function installFrontendHooks() {
    if (typeof getRankedRotations === 'function' && !window._originalGetRankedRotations) {
      window._originalGetRankedRotations = getRankedRotations;
      window.getRankedRotations = function () {
        const currentSig = buildStateSignature();
        if (
          bridgeState.connected &&
          bridgeState.lastResponse &&
          bridgeState.lastSignature === currentSig &&
          Array.isArray(bridgeState.lastResponse.rankedRotations) &&
          bridgeState.lastResponse.rankedRotations.length > 0
        ) {
          return bridgeState.lastResponse.rankedRotations;
        }
        return window._originalGetRankedRotations();
      };
    }

    if (typeof evaluateCropSelection === 'function' && !window._originalEvaluateCropSelection) {
      window._originalEvaluateCropSelection = evaluateCropSelection;
      window.evaluateCropSelection = function (selectedIds, topPick) {
        const currentSig = buildStateSignature();
        if (
          bridgeState.connected &&
          bridgeState.lastResponse &&
          bridgeState.lastSignature === currentSig &&
          bridgeState.lastResponse.evaluation
        ) {
          const ev = { ...bridgeState.lastResponse.evaluation };
          if (appState.selectedRankIndex > 0 && topPick && topPick.label) {
            ev.line2 = `Selected alternative sequence (#${appState.selectedRankIndex + 1}): ${topPick.label} (within ${appState.maxWaterDemand} mm water budget).`;
          }
          return ev;
        }
        return window._originalEvaluateCropSelection(selectedIds, topPick);
      };
    }

    if (typeof renderDashboard === 'function' && !window._originalRenderDashboard) {
      window._originalRenderDashboard = renderDashboard;
      window.renderDashboard = function () {
        window._originalRenderDashboard();
        if (bridgeState.connected && bridgeState.lastResponse) {
          applyBackendOverlayToDom(bridgeState.lastResponse);
        }
        scheduleBackendSync();
      };
    }
  }

  // Install hooks immediately since `app.js` has already defined its top-level functions
  installFrontendHooks();

  document.addEventListener('DOMContentLoaded', () => {
    installFrontendHooks();
    syncWithBackend(true);
  });
})();

