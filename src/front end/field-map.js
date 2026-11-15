// Field planner on the dashboard's "Field map & climate" tab, on a real Google satellite map.
// The map opens on the farm address picked on the Select Your Location screen. The farmer clicks
// on the map to drop corner points for the active field (F001, F002, ...) and the points are
// joined into a filled polygon. Corners can be dragged to adjust, and each field gets its area.
// Outlines are kept in appState.fieldPolygons as { fieldNumber: [{ lat, lng }, ...] }.
// Without a Google Maps key this script does nothing and app.js's square planner stays.

(async () => {
  const container = document.getElementById('satellite-map-canvas');
  if (!container || !window.farmingAuraGoogleReady) return;
  if (!(await window.farmingAuraGoogleReady)) return;

  const COLORS = ['#f2c14e', '#5bc0eb', '#9bc53d', '#fa7921', '#e55934', '#c879ff', '#2ec4b6', '#ff9f1c'];
  const colorFor = (num) => COLORS[(num - 1) % COLORS.length];
  const SQ_M_PER_ACRE = 4046.8564224;

  appState.fieldPolygons = appState.fieldPolygons || {};
  const shapes = {}; // field number -> { polygon, label, labelEl, listeners }
  let map = null;
  let homeMarker = null;
  let MarkerClass = null;
  let PolygonClass = null;
  let spherical = null;
  let started = false;
  let pendingCenter = null;

  const style = document.createElement('style');
  style.textContent = `
    .gm-field-map { position: absolute; inset: 0; display: none; }
    .satellite-map-container.google-live .gm-field-map { display: block; }
    .satellite-map-container.google-live .satellite-clean-terrain,
    .satellite-map-container.google-live .map-borders-layer { display: none; }
    .gm-field-label { background: rgba(20, 40, 28, 0.85); color: #fff; font: 700 11px/1.2 sans-serif;
      padding: 3px 6px; border-radius: 2px; white-space: nowrap; transform: translateY(50%); }
    .gm-field-label.active { background: #fff; color: #183925; box-shadow: 0 1px 4px rgba(0,0,0,0.35); }
  `;
  document.head.appendChild(style);

  const mapBox = document.createElement('div');
  mapBox.className = 'gm-field-map';
  container.appendChild(mapBox);

  // ---- Helpers ----
  function farmLocation() {
    if (appState.farmLocation) return appState.farmLocation;
    const lat = parseFloat((document.getElementById('step1-lat-input') || {}).value) || 42.6526;
    const lon = parseFloat((document.getElementById('step1-lon-input') || {}).value) || -73.7562;
    const labelEl = document.getElementById('step1-region-selected');
    return { lat, lon, label: labelEl ? labelEl.textContent.trim() : 'Your farm' };
  }

  function areaAcres(points) {
    if (!spherical || points.length < 3) return null;
    return spherical.computeArea(points) / SQ_M_PER_ACRE;
  }

  function centerOf(points) {
    const lat = points.reduce((s, p) => s + p.lat, 0) / points.length;
    const lng = points.reduce((s, p) => s + p.lng, 0) / points.length;
    return { lat, lng };
  }

  function selectField(num) {
    appState.selectedFieldNumber = num;
    appState.selectedFieldId = getFieldIdForNumber(num);
    appState.selectedRankIndex = 0;
    renderDashboard();
  }

  // ---- Drawing one field's polygon ----
  function readPathBack(num) {
    const s = shapes[num];
    if (!s) return;
    appState.fieldPolygons[num] = s.polygon
      .getPath()
      .getArray()
      .map((p) => ({ lat: p.lat(), lng: p.lng() }));
    updateLabel(num);
    updateHint();
    if (typeof renderDashboard === 'function') renderDashboard();
  }

  function updateLabel(num) {
    const s = shapes[num];
    const points = appState.fieldPolygons[num] || [];
    if (!s || !points.length) return;
    const acres = areaAcres(points);
    s.labelEl.textContent = formatFieldCode(num) + (acres !== null ? ` · ${acres.toFixed(1)} ac` : '');
    s.labelEl.classList.toggle('active', num === appState.selectedFieldNumber);
    s.label.position = centerOf(points);
  }

  function drawField(num) {
    const points = appState.fieldPolygons[num] || [];
    let s = shapes[num];

    if (!points.length) {
      if (s) {
        s.listeners.forEach((l) => l.remove());
        s.polygon.setMap(null);
        s.label.map = null;
        delete shapes[num];
      }
      return;
    }

    if (!s) {
      const color = colorFor(num);
      const polygon = new PolygonClass({ map, strokeColor: color, fillColor: color, strokeWeight: 2 });
      polygon.addListener('click', (e) => {
        // clicks on a corner handle or edge midpoint are for dragging, not for adding points
        if (e.vertex !== undefined || e.edge !== undefined) return;
        if (num === appState.selectedFieldNumber) addPoint(e.latLng);
        else selectField(num);
      });
      const labelEl = document.createElement('div');
      labelEl.className = 'gm-field-label';
      const label = new MarkerClass({ map, content: labelEl, zIndex: 5 });
      s = shapes[num] = { polygon, label, labelEl, listeners: [] };
    }

    // setPaths swaps the path object, so re-attach the "corner was dragged" listeners each time
    s.listeners.forEach((l) => l.remove());
    s.polygon.setPaths(points);
    const path = s.polygon.getPath();
    s.listeners = ['set_at', 'insert_at', 'remove_at'].map((evt) => path.addListener(evt, () => readPathBack(num)));

    const active = num === appState.selectedFieldNumber;
    s.polygon.setOptions({
      editable: active,
      strokeWeight: active ? 3 : 2,
      fillOpacity: active ? 0.45 : 0.25,
      zIndex: active ? 2 : 1
    });
    updateLabel(num);
  }

  function drawAll() {
    Object.keys(appState.fieldPolygons).forEach((key) => {
      const num = Number(key);
      if (num > appState.fieldCount) delete appState.fieldPolygons[key];
    });
    Object.keys(shapes).forEach((key) => {
      if (!appState.fieldPolygons[key]) drawField(Number(key));
    });
    Object.keys(appState.fieldPolygons).forEach((key) => drawField(Number(key)));
    updateHint();
  }

  function addPoint(latLng) {
    const num = appState.selectedFieldNumber;
    const points = appState.fieldPolygons[num] || (appState.fieldPolygons[num] = []);
    points.push({ lat: latLng.lat(), lng: latLng.lng() });
    drawField(num);
    updateHint();
    if (typeof renderDashboard === 'function') renderDashboard();
  }

  // ---- Controls: swap app.js's square-drawing buttons for point-based ones ----
  const originals = {};
  function swapElement(oldId, newId, text) {
    const old = document.getElementById(oldId);
    if (!old) return null;
    const fresh = old.cloneNode(false); // cloning drops app.js's click handlers
    fresh.id = newId;
    fresh.classList.remove('active-draw-mode');
    fresh.textContent = text;
    old.replaceWith(fresh);
    originals[newId] = old;
    return fresh;
  }

  let hintEl = null;
  function updateHint() {
    if (!hintEl) return;
    const farm = farmLocation();
    const num = appState.selectedFieldNumber;
    const code = formatFieldCode(num);
    const points = appState.fieldPolygons[num] || [];
    const acres = areaAcres(points);
    const progress =
      points.length === 0
        ? `Click on the map to drop the first corner of ${code}.`
        : points.length < 3
          ? `${code}: ${points.length} corner${points.length === 1 ? '' : 's'} placed, add ${3 - points.length} more to fill the field.`
          : `${code}: ${points.length} corners · ${acres.toFixed(1)} acres. Keep clicking to add corners, or drag the white dots to adjust.`;
    hintEl.textContent = `Farm: ${farm.label} (${farm.lat.toFixed(5)}, ${farm.lon.toFixed(5)}). ${progress} Pick another field under "Active field" to outline it.`;
  }

  function installControls() {
    const undoBtn = swapElement('map-draw-mode-btn', 'gm-undo-point-btn', 'Undo last point');
    const clearBtn = swapElement('map-reset-grid-btn', 'gm-clear-field-btn', 'Clear this field');
    hintEl = swapElement('map-draw-hint', 'gm-field-hint', '');

    if (undoBtn) {
      undoBtn.addEventListener('click', () => {
        const points = appState.fieldPolygons[appState.selectedFieldNumber];
        if (points && points.length) points.pop();
        drawField(appState.selectedFieldNumber);
        updateHint();
        if (typeof renderDashboard === 'function') renderDashboard();
      });
    }
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        delete appState.fieldPolygons[appState.selectedFieldNumber];
        drawField(appState.selectedFieldNumber);
        updateHint();
        if (typeof renderDashboard === 'function') renderDashboard();
      });
    }

    const badge = document.querySelector('.map-builder-card .map-api-badge');
    if (badge) {
      originals.badgeText = badge.textContent;
      badge.textContent = 'Google Maps · Satellite';
    }
    const sub = document.querySelector('.map-builder-card .map-builder-header .water-demand-sub');
    if (sub) {
      originals.subText = sub.textContent;
      sub.textContent =
        'Choose a field under "Active field", then click around its edge on the satellite map to drop corner points. The points fill in as the field outline. Zoom with the + / − buttons or Ctrl/⌘ + scroll.';
    }
  }

  function restoreControls() {
    ['gm-undo-point-btn', 'gm-clear-field-btn', 'gm-field-hint'].forEach((id) => {
      const current = document.getElementById(id);
      if (current && originals[id]) current.replaceWith(originals[id]);
    });
    const badge = document.querySelector('.map-builder-card .map-api-badge');
    if (badge && originals.badgeText) badge.textContent = originals.badgeText;
    const sub = document.querySelector('.map-builder-card .map-builder-header .water-demand-sub');
    if (sub && originals.subText) sub.textContent = originals.subText;
    hintEl = null;
  }

  // ---- Map start-up ----
  const originalRenderBorders = renderMapFieldBorders;

  async function startMap() {
    if (started) return;
    started = true;
    try {
      const { Map, Polygon } = await google.maps.importLibrary('maps');
      const { AdvancedMarkerElement } = await google.maps.importLibrary('marker');
      ({ spherical } = await google.maps.importLibrary('geometry'));
      MarkerClass = AdvancedMarkerElement;
      PolygonClass = Polygon;

      const farm = farmLocation();
      map = new Map(mapBox, {
        center: { lat: farm.lat, lng: farm.lon },
        zoom: 17,
        mapTypeId: 'satellite',
        mapId: 'DEMO_MAP_ID',
        tilt: 0,
        clickableIcons: false,
        gestureHandling: 'cooperative',
        streetViewControl: false,
        mapTypeControl: false,
        fullscreenControl: true
      });
      homeMarker = new MarkerClass({ map, position: { lat: farm.lat, lng: farm.lon }, title: 'Your farm address' });
      map.addListener('click', (e) => addPoint(e.latLng));

      container.classList.add('google-live');
      installControls();

      // app.js redraws the planner whenever the field count or active field changes; keep polygons in step
      renderMapFieldBorders = function () {
        originalRenderBorders();
        if (map) drawAll();
      };
      drawAll();
    } catch (err) {
      console.warn('[Farming Aura] Field planner map did not load, keeping the square planner.', err.message);
      giveUp();
    }
  }

  function giveUp() {
    started = true; // don't try again
    map = null;
    container.classList.remove('google-live');
    restoreControls();
    renderMapFieldBorders = originalRenderBorders;
    originalRenderBorders();
  }

  // The farm address changed on the location screen: move the planner there
  window.addEventListener('farm-location-changed', (e) => {
    const pos = { lat: e.detail.lat, lng: e.detail.lon };
    if (homeMarker) homeMarker.position = pos;
    if (!map) return;
    if (container.clientWidth > 0) map.setCenter(pos);
    else pendingCenter = pos; // centering a hidden map goes wrong, so wait until it's visible
    updateHint();
  });

  window.addEventListener('farming-aura-maps-failed', giveUp);

  // A map made inside a hidden tab comes out blank, so wait until the planner is showing
  new ResizeObserver(() => {
    if (container.clientWidth === 0) return;
    if (!started) startMap();
    else if (map && pendingCenter) {
      map.setCenter(pendingCenter);
      pendingCenter = null;
    }
  }).observe(container);
})();
