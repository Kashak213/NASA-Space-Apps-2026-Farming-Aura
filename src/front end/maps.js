// Real Google Map for the Select Your Location screen.
// The key is NOT written in this file: the backend reads GOOGLE_MAPS_API_KEY from .env
// and hands it over at GET /config. With no key (or no backend), the drawn schematic map stays.
// With a key, the schematic is swapped for a satellite map with the same five city pins,
// and clicking anywhere on the map picks a custom farm location.

(async () => {
  // Same backend address rules as api.js
  const onThisComputer = location.protocol === 'file:' || ['localhost', '127.0.0.1'].includes(location.hostname);
  const sameServer = onThisComputer && location.port === '8000';
  const API_BASE = window.FARMING_AURA_API || (sameServer ? '' : onThisComputer ? 'http://localhost:8000' : null);
  if (API_BASE === null) return;

  let GOOGLE_MAPS_API_KEY = null;
  try {
    const res = await fetch(`${API_BASE}/config`);
    if (res.ok) GOOGLE_MAPS_API_KEY = (await res.json()).google_maps_api_key;
  } catch (err) {
    console.warn('[Farming Aura] backend not reachable, keeping the schematic map.', err.message);
  }
  if (!GOOGLE_MAPS_API_KEY) return;

  const canvas = document.querySelector('.schematic-map-canvas');
  if (!canvas) return;

  let map = null;
  let customMarker = null;
  const cityMarkers = {};
  let started = false;

  // Extra styles for the live map, kept here so styles.css doesn't need to change
  const style = document.createElement('style');
  style.textContent = `
    .google-map-canvas { position: absolute; inset: 0; display: none; }
    .schematic-map-canvas.google-live .google-map-canvas { display: block; }
    .schematic-map-canvas.google-live .schematic-svg,
    .schematic-map-canvas.google-live > .city-pin,
    .schematic-map-canvas.google-live .map-zoom-controls,
    .schematic-map-canvas.google-live .map-Disclaim-caption { display: none; }
    .city-pin.gm-pin { position: relative; top: auto; left: auto; transform: translate(50%, 50%) translateX(-12px); }
    .city-pin.gm-pin:hover { transform: translate(50%, 50%) translateX(-12px) scale(1.05); }
  `;
  document.head.appendChild(style);

  const mapBox = document.createElement('div');
  mapBox.id = 'google-map-canvas';
  mapBox.className = 'google-map-canvas';
  canvas.insertBefore(mapBox, canvas.firstChild);

  // Google calls this if the key is wrong or not allowed on this site, so go back to the schematic
  window.gm_authFailure = () => {
    console.warn('[Farming Aura] Google Maps rejected the API key, showing the schematic map instead.');
    canvas.classList.remove('google-live');
  };

  function loadGoogleMaps() {
    return new Promise((resolve, reject) => {
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

  // Same look as the schematic pins, so the real map matches the design
  function buildPinElement(city) {
    const pin = document.createElement('div');
    pin.className = 'city-pin gm-pin';
    pin.dataset.city = city.cityKey;
    pin.innerHTML = '<div class="city-pin-dot"></div><div class="city-pin-label"></div>';
    pin.querySelector('.city-pin-label').textContent = city.cityKey;
    pin.classList.toggle('selected-city', city.cityKey === appState.selectedCity);
    return pin;
  }

  function highlightCity(cityKey) {
    Object.entries(cityMarkers).forEach(([key, marker]) => {
      marker.content.classList.toggle('selected-city', key === cityKey);
    });
  }

  // Farmer clicked a spot that isn't one of our cities
  function pickCustomSpot(latLng, AdvancedMarkerElement) {
    const lat = latLng.lat().toFixed(4);
    const lon = latLng.lng().toFixed(4);

    const setText = (id, text) => {
      const el = document.getElementById(id);
      if (el) el.textContent = text;
    };
    setText('step1-region-selected', 'Custom farm location');
    setText('step1-latlon-display', `${lat}, ${lon}`);
    setText('step1-dropdown-label', 'Custom farm location');
    const latInput = document.getElementById('step1-lat-input');
    const lonInput = document.getElementById('step1-lon-input');
    if (latInput) latInput.value = lat;
    if (lonInput) lonInput.value = lon;

    highlightCity(null);
    if (!customMarker) {
      customMarker = new AdvancedMarkerElement({ map, title: 'Custom farm location' });
    }
    customMarker.position = latLng;
    customMarker.map = map;

    // the backend reads the lat/lon boxes, so redraw to pull NASA data for the new spot
    renderAll();
  }

  async function startMap() {
    if (started) return;
    started = true;
    try {
      await loadGoogleMaps();
      const { Map } = await google.maps.importLibrary('maps');
      const { AdvancedMarkerElement } = await google.maps.importLibrary('marker');

      const home = CITY_LOCATIONS[appState.selectedCity] || CITY_LOCATIONS.Albany;
      map = new Map(mapBox, {
        center: { lat: parseFloat(home.lat), lng: parseFloat(home.lon) },
        zoom: 9,
        mapTypeId: 'hybrid',
        mapId: 'DEMO_MAP_ID',
        streetViewControl: false,
        fullscreenControl: false,
        mapTypeControl: false
      });

      Object.values(CITY_LOCATIONS).forEach((city) => {
        const marker = new AdvancedMarkerElement({
          map,
          position: { lat: parseFloat(city.lat), lng: parseFloat(city.lon) },
          title: city.label,
          content: buildPinElement(city)
        });
        marker.addListener('click', () => {
          selectCityLocation(city.cityKey);
          renderAll();
        });
        cityMarkers[city.cityKey] = marker;
      });

      map.addListener('click', (e) => pickCustomSpot(e.latLng, AdvancedMarkerElement));
      canvas.classList.add('google-live');
    } catch (err) {
      console.warn('[Farming Aura] Google Maps did not load, showing the schematic map instead.', err.message);
      canvas.classList.remove('google-live');
    }
  }

  // Whenever a city gets picked anywhere (pin, dropdown, search box), move the real map too
  const pickCity = selectCityLocation;
  selectCityLocation = function (cityKey) {
    pickCity(cityKey);
    const city = CITY_LOCATIONS[cityKey];
    if (!map || !city) return;
    highlightCity(cityKey);
    if (customMarker) customMarker.map = null;
    map.panTo({ lat: parseFloat(city.lat), lng: parseFloat(city.lon) });
  };

  // A map made inside a hidden screen comes out blank, so wait until the location screen is showing
  const watcher = new ResizeObserver(() => {
    if (canvas.clientWidth > 0) {
      watcher.disconnect();
      startMap();
    }
  });
  watcher.observe(canvas);
})();
