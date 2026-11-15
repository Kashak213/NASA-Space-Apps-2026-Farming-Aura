// Select Your Location screen: address search + real Google Map.
// The Maps key is NOT written in this file: the backend reads GOOGLE_MAPS_API_KEY from .env
// and hands it over at GET /config. With no key (or no backend), the drawn schematic map stays,
// but the address search still works (it falls back to OpenStreetMap's free geocoder).
// Picking a location (search, clicking the map, or typing lat/lon) fills in the region panel
// and the lat/lon boxes that the backend reads.

// Other scripts (field-map.js) wait on this: true once Google Maps is loaded, false if it never will be
let resolveGoogleReady;
window.farmingAuraGoogleReady = new Promise((resolve) => {
  resolveGoogleReady = resolve;
});

(async () => {
  const canvas = document.querySelector('.schematic-map-canvas');
  const searchInput = document.getElementById('step1-map-search');
  if (!canvas) return resolveGoogleReady(false);

  let map = null;
  let marker = null;
  let MarkerClass = null;

  // Extra styles, kept here so styles.css doesn't need to change
  const style = document.createElement('style');
  style.textContent = `
    .google-map-canvas { position: absolute; inset: 0; display: none; }
    .schematic-map-canvas.google-live .google-map-canvas { display: block; }
    .schematic-map-canvas.google-live .schematic-svg,
    .schematic-map-canvas.google-live .map-zoom-controls,
    .schematic-map-canvas.google-live .map-Disclaim-caption { display: none; }
    .map-search-status { display: none; margin-top: 6px; padding: 6px 12px; font-size: 13px;
      background: rgba(255, 255, 255, 0.94); color: #1f3a2b; border-radius: 2px; }
    .map-search-status.show { display: block; }
    .map-search-status.error { color: #9a2d1f; }
  `;
  document.head.appendChild(style);

  // ---- Shared: put a chosen location everywhere the app reads it ----
  function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function setLocation(lat, lon, label) {
    const latStr = Number(lat).toFixed(4);
    const lonStr = Number(lon).toFixed(4);
    setText('step1-region-selected', label);
    setText('step1-latlon-display', `${latStr}, ${lonStr}`);
    const latInput = document.getElementById('step1-lat-input');
    const lonInput = document.getElementById('step1-lon-input');
    if (latInput) latInput.value = latStr;
    if (lonInput) lonInput.value = lonStr;

    // Gemini's explanation says "near <this>", so keep it short
    appState.selectedCity = label.split(',').slice(0, 2).join(',').trim();
    appState.farmLocation = { lat: Number(lat), lon: Number(lon), label };

    // the field planner map listens for this and moves to the farm
    window.dispatchEvent(
      new CustomEvent('farm-location-changed', { detail: { lat: Number(lat), lon: Number(lon), label } })
    );

    if (map) {
      const pos = { lat: Number(lat), lng: Number(lon) };
      map.panTo(pos);
      if (map.getZoom() < 13) map.setZoom(13);
      placeMarker(pos);
    }
    // the backend reads the lat/lon boxes, so redraw to pull data for the new spot
    if (typeof renderAll === 'function') renderAll();
  }

  function placeMarker(pos) {
    if (!map || !MarkerClass) return;
    if (!marker) marker = new MarkerClass({ map, title: 'Your farm' });
    marker.position = pos;
    marker.map = map;
  }

  // ---- Address search ----
  const status = document.createElement('div');
  status.className = 'map-search-status';
  if (searchInput && searchInput.parentElement) searchInput.parentElement.appendChild(status);

  function showStatus(text, isError) {
    status.textContent = text || '';
    status.classList.toggle('show', Boolean(text));
    status.classList.toggle('error', Boolean(isError));
  }

  async function geocodeWithGoogle(query) {
    if (!(window.google && google.maps && google.maps.Geocoder)) return null;
    try {
      const { results } = await new google.maps.Geocoder().geocode({ address: query, region: 'us' });
      const top = results && results[0];
      if (!top) return null;
      return { lat: top.geometry.location.lat(), lon: top.geometry.location.lng(), label: top.formatted_address };
    } catch (err) {
      // REQUEST_DENIED means the Geocoding API isn't enabled for this key; ZERO_RESULTS means no match
      console.warn('[Farming Aura] Google geocoder:', err.code || err.message);
      return null;
    }
  }

  async function geocodeWithOpenStreetMap(query) {
    const url =
      'https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=us&q=' +
      encodeURIComponent(query);
    const res = await fetch(url, { headers: { 'Accept-Language': 'en' } });
    if (!res.ok) return null;
    const rows = await res.json();
    if (!rows.length) return null;
    const label = rows[0].display_name.split(',').slice(0, 3).join(',').trim();
    return { lat: parseFloat(rows[0].lat), lon: parseFloat(rows[0].lon), label };
  }

  let searching = false;
  async function runSearch() {
    const query = (searchInput.value || '').trim();
    if (!query || searching) return;
    searching = true;
    showStatus('Searching…');
    try {
      const found = (await geocodeWithGoogle(query)) || (await geocodeWithOpenStreetMap(query));
      if (found) {
        showStatus('');
        setLocation(found.lat, found.lon, found.label);
      } else {
        showStatus('No match found. Try a fuller address, a town name or a ZIP code.', true);
      }
    } catch (err) {
      showStatus('Address search is unavailable right now. You can type the latitude and longitude instead.', true);
      console.warn('[Farming Aura] address search failed.', err.message);
    } finally {
      searching = false;
    }
  }

  if (searchInput) {
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        runSearch();
      }
    });
    searchInput.addEventListener('input', () => showStatus(''));
  }

  // Typing coordinates by hand moves the map too
  ['step1-lat-input', 'step1-lon-input'].forEach((id) => {
    const input = document.getElementById(id);
    if (!input) return;
    input.addEventListener('change', () => {
      const lat = parseFloat(document.getElementById('step1-lat-input').value);
      const lon = parseFloat(document.getElementById('step1-lon-input').value);
      if (Number.isFinite(lat) && Number.isFinite(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180) {
        setLocation(lat, lon, 'Custom coordinates');
      }
    });
  });

  // ---- Google Map (only when the backend gives us a key) ----
  const onThisComputer = location.protocol === 'file:' || ['localhost', '127.0.0.1'].includes(location.hostname);
  const sameServer = onThisComputer && location.port === '8000';
  const API_BASE = window.FARMING_AURA_API || (sameServer ? '' : onThisComputer ? 'http://localhost:8000' : null);

  let GOOGLE_MAPS_API_KEY = window.GOOGLE_MAPS_API_KEY || null;
  if (!GOOGLE_MAPS_API_KEY && API_BASE !== null) {
    try {
      const res = await fetch(`${API_BASE}/config`);
      if (res.ok) GOOGLE_MAPS_API_KEY = (await res.json()).google_maps_api_key;
    } catch (err) {
      console.warn('[Farming Aura] backend not reachable, keeping the schematic map.', err.message);
    }
  }
  if (!GOOGLE_MAPS_API_KEY) return resolveGoogleReady(false);

  const mapBox = document.createElement('div');
  mapBox.id = 'google-map-canvas';
  mapBox.className = 'google-map-canvas';
  canvas.insertBefore(mapBox, canvas.firstChild);

  // Google calls this if the key is wrong or not allowed on this site, so go back to the schematic
  window.gm_authFailure = () => {
    console.warn('[Farming Aura] Google Maps rejected the API key, showing the schematic map instead.');
    canvas.classList.remove('google-live');
    map = null;
    window.dispatchEvent(new CustomEvent('farming-aura-maps-failed'));
  };

  // Loaded once and shared by the location map here and the field planner in field-map.js
  let loading = null;
  function loadGoogleMaps() {
    if (!loading) {
      loading = new Promise((resolve, reject) => {
        if (window.google && window.google.maps) return resolve();
        window.__farmingAuraMapsReady = resolve;
        const script = document.createElement('script');
        script.src =
          'https://maps.googleapis.com/maps/api/js?key=' + encodeURIComponent(GOOGLE_MAPS_API_KEY) +
          '&v=weekly&loading=async&callback=__farmingAuraMapsReady';
        script.async = true;
        script.onerror = () => reject(new Error('Google Maps script failed to load'));
        document.head.appendChild(script);
      });
    }
    return loading;
  }
  loadGoogleMaps().then(
    () => resolveGoogleReady(true),
    () => resolveGoogleReady(false)
  );

  let started = false;
  async function startMap() {
    if (started) return;
    started = true;
    try {
      await loadGoogleMaps();
      const { Map } = await google.maps.importLibrary('maps');
      const { AdvancedMarkerElement } = await google.maps.importLibrary('marker');
      MarkerClass = AdvancedMarkerElement;

      const lat = parseFloat(document.getElementById('step1-lat-input').value) || 42.6526;
      const lon = parseFloat(document.getElementById('step1-lon-input').value) || -73.7562;
      map = new Map(mapBox, {
        center: { lat, lng: lon },
        zoom: 12,
        mapTypeId: 'hybrid',
        mapId: 'DEMO_MAP_ID',
        streetViewControl: false,
        fullscreenControl: false,
        mapTypeControl: false
      });
      placeMarker({ lat, lng: lon });

      map.addListener('click', (e) => setLocation(e.latLng.lat(), e.latLng.lng(), 'Custom farm location'));
      canvas.classList.add('google-live');
    } catch (err) {
      console.warn('[Farming Aura] Google Maps did not load, showing the schematic map instead.', err.message);
      canvas.classList.remove('google-live');
      map = null;
    }
  }

  // A map made inside a hidden screen comes out blank, so wait until the location screen is showing
  const watcher = new ResizeObserver(() => {
    if (canvas.clientWidth > 0) {
      watcher.disconnect();
      startMap();
    }
  });
  watcher.observe(canvas);
})();
