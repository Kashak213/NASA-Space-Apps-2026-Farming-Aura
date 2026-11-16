// Client-side state, rotation scoring engine, and UI interactions for Farming Aura

const FIELDS_DATA = {
  F001: {
    id: 'F001',
    name: 'Field F001',
    regionLabel: 'Albany, New York',
    lat: 42.6526,
    lon: -73.7562,
    oc: 2.49,
    ph: 6.36,
    clay: 34.1,
    sand: 15.5,
    bd: 1.14,
    cec: 18.89,
    spring2023Precip: 270,
    summer2023Precip: 512,
    spring2024Precip: 385,
    summer2024Precip: 393,
    annualTotalMm: 1202,
    rainSeries2020_2024: [539, 728, 495, 782, 778],
    tempSeries2020_2024: [21.5, 20.9, 21.4, 19.8, 21.0],
    drought2023: 0.14,
    drought2024: 0.15,
    moistureAvg: 0.66,
    ndvi2023: 0.74,
    ndvi2024: 0.75,
    tempSummer: 21.0,
    soilTempC: 19.1,
    anom2023: 8.2,
    anom2024: 7.4,
    mapStatus: 'Healthy',
    mapSoilScore: 0.79,
    mapMoisture: 0.66,
    soilMapUnit: 'Hudson silt loam, 3 to 8 percent slopes',
    nasaSource: 'cache',
    usdaSource: 'cache'
  },
  F002: {
    id: 'F002',
    name: 'Field F002',
    regionLabel: 'Saratoga Springs, New York',
    lat: 43.0831,
    lon: -73.7846,
    oc: 0.75,
    ph: 5.19,
    clay: 1.0,
    sand: 85.0,
    bd: 1.48,
    cec: 0.54,
    spring2023Precip: 274,
    summer2023Precip: 514,
    spring2024Precip: 375,
    summer2024Precip: 396,
    annualTotalMm: 1184,
    rainSeries2020_2024: [530, 694, 540, 788, 771],
    tempSeries2020_2024: [21.3, 21.0, 20.9, 20.1, 21.1],
    drought2023: 0.18,
    drought2024: 0.19,
    moistureAvg: 0.71,
    ndvi2023: 0.71,
    ndvi2024: 0.72,
    tempSummer: 21.1,
    soilTempC: 19.1,
    anom2023: 7.5,
    anom2024: 5.8,
    mapStatus: 'Moderate stress',
    mapSoilScore: 0.42,
    mapMoisture: 0.71,
    soilMapUnit: 'Windsor loamy sand, 3 to 8 percent slopes',
    nasaSource: 'cache',
    usdaSource: 'cache'
  },
  F003: {
    id: 'F003',
    name: 'Field F003',
    regionLabel: 'Schenectady, New York',
    lat: 42.8142,
    lon: -73.9396,
    oc: 3.31,
    ph: 7.0,
    clay: 45.3,
    sand: 11.4,
    bd: 1.11,
    cec: 33.42,
    spring2023Precip: 274,
    summer2023Precip: 514,
    spring2024Precip: 375,
    summer2024Precip: 396,
    annualTotalMm: 1184,
    rainSeries2020_2024: [530, 694, 540, 788, 771],
    tempSeries2020_2024: [21.3, 21.0, 20.9, 20.1, 21.1],
    drought2023: 0.13,
    drought2024: 0.14,
    moistureAvg: 0.71,
    ndvi2023: 0.77,
    ndvi2024: 0.78,
    tempSummer: 21.1,
    soilTempC: 19.1,
    anom2023: 7.5,
    anom2024: 5.8,
    mapStatus: 'Healthy',
    mapSoilScore: 0.79,
    mapMoisture: 0.71,
    soilMapUnit: 'Madalin silty clay loam, 0 to 3 percent slopes',
    nasaSource: 'cache',
    usdaSource: 'cache'
  },
  F004: {
    id: 'F004',
    name: 'Field F004',
    regionLabel: 'Troy, New York',
    lat: 42.7284,
    lon: -73.6918,
    oc: 2.18,
    ph: 5.16,
    clay: 12.0,
    sand: 32.1,
    bd: 1.35,
    cec: 6.83,
    spring2023Precip: 270,
    summer2023Precip: 512,
    spring2024Precip: 385,
    summer2024Precip: 393,
    annualTotalMm: 1202,
    rainSeries2020_2024: [539, 728, 495, 782, 778],
    tempSeries2020_2024: [21.5, 20.9, 21.4, 19.8, 21.0],
    drought2023: 0.16,
    drought2024: 0.17,
    moistureAvg: 0.66,
    ndvi2023: 0.72,
    ndvi2024: 0.73,
    tempSummer: 21.0,
    soilTempC: 19.1,
    anom2023: 8.2,
    anom2024: 7.4,
    mapStatus: 'Moderate stress',
    mapSoilScore: 0.45,
    mapMoisture: 0.66,
    soilMapUnit: 'Chenango gravelly silt loam, 3 to 8 percent slopes',
    nasaSource: 'cache',
    usdaSource: 'cache'
  },
  F005: {
    id: 'F005',
    name: 'Field F005',
    regionLabel: 'Hudson, New York',
    lat: 42.2529,
    lon: -73.7910,
    oc: 2.32,
    ph: 6.38,
    clay: 41.2,
    sand: 15.6,
    bd: 1.24,
    cec: 21.8,
    spring2023Precip: 270,
    summer2023Precip: 512,
    spring2024Precip: 385,
    summer2024Precip: 393,
    annualTotalMm: 1202,
    rainSeries2020_2024: [539, 728, 495, 782, 778],
    tempSeries2020_2024: [21.5, 20.9, 21.4, 19.8, 21.0],
    drought2023: 0.14,
    drought2024: 0.15,
    moistureAvg: 0.66,
    ndvi2023: 0.75,
    ndvi2024: 0.76,
    tempSummer: 21.0,
    soilTempC: 19.1,
    anom2023: 8.2,
    anom2024: 7.4,
    mapStatus: 'Healthy',
    mapSoilScore: 0.74,
    mapMoisture: 0.66,
    soilMapUnit: 'Hudson-Vergennes silt loam complex',
    nasaSource: 'cache',
    usdaSource: 'cache'
  },
  F006: {
    id: 'F006',
    name: 'Field F006',
    regionLabel: 'Albany West, New York',
    lat: 42.6554,
    lon: -73.9734,
    oc: 2.18,
    ph: 5.16,
    clay: 12.0,
    sand: 32.1,
    bd: 1.35,
    cec: 6.83,
    spring2023Precip: 270,
    summer2023Precip: 512,
    spring2024Precip: 385,
    summer2024Precip: 393,
    annualTotalMm: 1202,
    rainSeries2020_2024: [539, 728, 495, 782, 778],
    tempSeries2020_2024: [21.5, 20.9, 21.4, 19.8, 21.0],
    drought2023: 0.16,
    drought2024: 0.17,
    moistureAvg: 0.66,
    ndvi2023: 0.72,
    ndvi2024: 0.73,
    tempSummer: 21.0,
    soilTempC: 19.1,
    anom2023: 8.2,
    anom2024: 7.4,
    mapStatus: 'Healthy',
    mapSoilScore: 0.45,
    mapMoisture: 0.66,
    soilMapUnit: 'Chenango gravelly silt loam, rolling',
    nasaSource: 'cache',
    usdaSource: 'cache'
  },
  F007: {
    id: 'F007',
    name: 'Field F007',
    regionLabel: 'Saratoga South, New York',
    lat: 42.9241,
    lon: -73.6411,
    oc: 2.9,
    ph: 5.3,
    clay: 10.0,
    sand: 63.8,
    bd: 1.35,
    cec: 2.2,
    spring2023Precip: 274,
    summer2023Precip: 514,
    spring2024Precip: 375,
    summer2024Precip: 396,
    annualTotalMm: 1184,
    rainSeries2020_2024: [530, 694, 540, 788, 771],
    tempSeries2020_2024: [21.3, 21.0, 20.9, 20.1, 21.1],
    drought2023: 0.15,
    drought2024: 0.16,
    moistureAvg: 0.71,
    ndvi2023: 0.74,
    ndvi2024: 0.75,
    tempSummer: 21.1,
    soilTempC: 19.1,
    anom2023: 7.5,
    anom2024: 5.8,
    mapStatus: 'Moderate stress',
    mapSoilScore: 0.51,
    mapMoisture: 0.71,
    soilMapUnit: 'Scio very fine sandy loam, 0 to 3 percent slopes',
    nasaSource: 'cache',
    usdaSource: 'cache'
  },
  F008: {
    id: 'F008',
    name: 'Field F008',
    regionLabel: 'Finger Lakes, New York',
    lat: 42.7000,
    lon: -76.8000,
    oc: 2.2,
    ph: 6.7,
    clay: 22.5,
    sand: 26.8,
    bd: 1.35,
    cec: 14.3,
    spring2023Precip: 218,
    summer2023Precip: 359,
    spring2024Precip: 243,
    summer2024Precip: 347,
    annualTotalMm: 993,
    rainSeries2020_2024: [454, 626, 450, 577, 590],
    tempSeries2020_2024: [22.1, 21.5, 21.5, 20.3, 21.6],
    drought2023: 0.19,
    drought2024: 0.18,
    moistureAvg: 0.60,
    ndvi2023: 0.73,
    ndvi2024: 0.74,
    tempSummer: 21.6,
    soilTempC: 19.8,
    anom2023: 2.1,
    anom2024: 4.5,
    mapStatus: 'Healthy',
    mapSoilScore: 0.73,
    mapMoisture: 0.60,
    soilMapUnit: 'Angola silt loam, 3 to 8 percent slopes',
    nasaSource: 'cache',
    usdaSource: 'cache'
  }
};

const CITY_LOCATIONS = {
  Albany: {
    cityKey: 'Albany',
    label: 'Albany, New York',
    displayCoords: '42.6526, -73.7562',
    lat: '42.6526',
    lon: '-73.7562',
    defaultField: 'F001'
  },
  'Saratoga Springs': {
    cityKey: 'Saratoga Springs',
    label: 'Saratoga Springs, New York',
    displayCoords: '43.0831, -73.7846',
    lat: '43.0831',
    lon: '-73.7846',
    defaultField: 'F002'
  },
  Schenectady: {
    cityKey: 'Schenectady',
    label: 'Schenectady, New York',
    displayCoords: '42.8142, -73.9396',
    lat: '42.8142',
    lon: '-73.9396',
    defaultField: 'F003'
  },
  Troy: {
    cityKey: 'Troy',
    label: 'Troy, New York',
    displayCoords: '42.7284, -73.6918',
    lat: '42.7284',
    lon: '-73.6918',
    defaultField: 'F004'
  },
  Hudson: {
    cityKey: 'Hudson',
    label: 'Hudson, New York',
    displayCoords: '42.2529, -73.7910',
    lat: '42.2529',
    lon: '-73.7910',
    defaultField: 'F008'
  }
};

const CROPS_DATA = {
  C01: { id: 'C01', name: 'Hay or Alfalfa (Haylage)', type: 'legume', isPerennial: false, roleTag: 'Forage legume • nitrogen fixation', water: 580, nFix: 0.85, droughtTol: 0.55, phMin: 6.2, phMax: 7.5, clayMin: 18, clayMax: 40, yieldT: 9.5, rootM: 2.8, build: 0.95 },
  C02: { id: 'C02', name: 'Field Corn (Silage or Grain)', type: 'grain', isPerennial: false, roleTag: 'Grain • high silage or grain yield', water: 550, nFix: 0.0, droughtTol: 0.35, phMin: 5.8, phMax: 7.0, clayMin: 20, clayMax: 40, yieldT: 11.0, rootM: 1.2, build: 0.25 },
  C03: { id: 'C03', name: 'Soybeans or Small Grains', type: 'legume', isPerennial: false, roleTag: 'Legume • nitrogen fixation or cover', water: 420, nFix: 0.75, droughtTol: 0.60, phMin: 6.0, phMax: 7.2, clayMin: 18, clayMax: 45, yieldT: 4.2, rootM: 1.3, build: 0.85 },
  C04: { id: 'C04', name: 'Apples', type: 'orchard', isPerennial: true, roleTag: 'Orchard • perennial tree fruit', water: 500, nFix: 0.0, droughtTol: 0.55, phMin: 6.0, phMax: 7.0, clayMin: 15, clayMax: 35, yieldT: 10.0, rootM: 2.0, build: 0.60 },
  C05: { id: 'C05', name: 'Grapes (Juice or Wine)', type: 'vineyard', isPerennial: true, roleTag: 'Vineyard • deep roots or low water', water: 380, nFix: 0.0, droughtTol: 0.75, phMin: 5.5, phMax: 7.0, clayMin: 15, clayMax: 35, yieldT: 8.0, rootM: 2.2, build: 0.55 },
  C06: { id: 'C06', name: 'Cherries, Peaches, Pears or Plums', type: 'orchard', isPerennial: true, roleTag: 'Stone or pome fruit • orchard block', water: 480, nFix: 0.0, droughtTol: 0.50, phMin: 6.0, phMax: 7.0, clayMin: 15, clayMax: 32, yieldT: 8.5, rootM: 1.8, build: 0.55 },
  C07: { id: 'C07', name: 'Berries', type: 'berry', isPerennial: true, roleTag: 'Small fruit • acidic soil specialist', water: 430, nFix: 0.0, droughtTol: 0.45, phMin: 4.8, phMax: 6.5, clayMin: 12, clayMax: 30, yieldT: 6.5, rootM: 0.6, build: 0.50 },
  C08: { id: 'C08', name: 'Sugar Maple (Maple Syrup)', type: 'agroforestry', isPerennial: true, roleTag: 'Agroforestry • deep canopy or carbon', water: 450, nFix: 0.0, droughtTol: 0.70, phMin: 5.5, phMax: 7.2, clayMin: 15, clayMax: 38, yieldT: 4.5, rootM: 2.5, build: 0.90 },
  C09: { id: 'C09', name: 'Cabbage', type: 'vegetable', isPerennial: false, roleTag: 'Brassica • high-value cool crop', water: 440, nFix: 0.0, droughtTol: 0.40, phMin: 6.0, phMax: 7.2, clayMin: 18, clayMax: 38, yieldT: 11.5, rootM: 0.6, build: 0.30 },
  C10: { id: 'C10', name: 'Onions', type: 'root_veg', isPerennial: false, roleTag: 'Allium • shallow root cash crop', water: 410, nFix: 0.0, droughtTol: 0.35, phMin: 6.0, phMax: 7.0, clayMin: 12, clayMax: 30, yieldT: 10.5, rootM: 0.4, build: 0.25 },
  C11: { id: 'C11', name: 'Potatoes', type: 'root_veg', isPerennial: false, roleTag: 'Tuber • high yield or loose soil', water: 480, nFix: 0.0, droughtTol: 0.40, phMin: 5.2, phMax: 6.5, clayMin: 12, clayMax: 32, yieldT: 11.8, rootM: 0.7, build: 0.20 },
  C12: { id: 'C12', name: 'Sweet Corn, Snap Beans or Green Peas', type: 'legume', isPerennial: false, roleTag: 'Vegetable legume • nitrogen builder', water: 430, nFix: 0.65, droughtTol: 0.50, phMin: 5.8, phMax: 7.0, clayMin: 15, clayMax: 38, yieldT: 7.5, rootM: 0.9, build: 0.75 },
  C13: { id: 'C13', name: 'Beets, Carrots, Squash or Pumpkins', type: 'vegetable', isPerennial: false, roleTag: 'Root or vine veg • broad ground cover', water: 400, nFix: 0.0, droughtTol: 0.55, phMin: 5.8, phMax: 7.0, clayMin: 12, clayMax: 35, yieldT: 9.2, rootM: 0.9, build: 0.45 }
};

const CANDIDATE_SEQUENCES = [
  ['C03', 'C02', 'C01'], // Soybeans or Small Grains -> Field Corn -> Hay & Alfalfa
  ['C01', 'C02', 'C03'], // Hay & Alfalfa -> Field Corn -> Soybeans or Small Grains
  ['C03', 'C02', 'C11'], // Soybeans or Small Grains -> Field Corn -> Potatoes
  ['C12', 'C09', 'C10'], // Sweet Corn, Snap Beans or Green Peas -> Cabbage -> Onions
  ['C03', 'C11', 'C13'], // Soybeans or Small Grains -> Potatoes -> Beets, Carrots, Squash or Pumpkins
  ['C12', 'C11', 'C09'], // Sweet Corn, Snap Beans or Green Peas -> Potatoes -> Cabbage
  ['C03', 'C09', 'C13'], // Soybeans or Small Grains -> Cabbage -> Beets, Carrots, Squash or Pumpkins
  ['C12', 'C10', 'C13'], // Sweet Corn, Snap Beans or Green Peas -> Onions -> Beets, Carrots, Squash or Pumpkins
  ['C02', 'C12', 'C13'], // Field Corn -> Sweet Corn, Snap Beans or Green Peas -> Beets, Carrots, Squash or Pumpkins
  ['C04', 'C07', 'C05'], // Apples -> Berries -> Grapes
  ['C06', 'C04', 'C08']  // Cherries, Peaches, Pears or Plums -> Apples -> Sugar Maple
];

const PRIORITY_PROFILES = {
  Balanced: {
    soil_health: 0.20,
    water_stress: 0.20,
    climate_res: 0.15,
    nitrogen_fix: 0.15,
    yield: 0.15,
    drought_tol: 0.10,
    soil_compat: 0.05
  },
  'Max Yield': {
    soil_health: 0.10,
    water_stress: 0.15,
    climate_res: 0.10,
    nitrogen_fix: 0.10,
    yield: 0.40,
    drought_tol: 0.10,
    soil_compat: 0.05
  },
  'Water Conservation': {
    soil_health: 0.10,
    water_stress: 0.35,
    climate_res: 0.15,
    nitrogen_fix: 0.10,
    yield: 0.10,
    drought_tol: 0.15,
    soil_compat: 0.05
  },
  'Soil Health First': {
    soil_health: 0.30,
    water_stress: 0.10,
    climate_res: 0.10,
    nitrogen_fix: 0.25,
    yield: 0.10,
    drought_tol: 0.10,
    soil_compat: 0.05
  },
  'Climate Resilient': {
    soil_health: 0.15,
    water_stress: 0.20,
    climate_res: 0.25,
    nitrogen_fix: 0.10,
    yield: 0.10,
    drought_tol: 0.15,
    soil_compat: 0.05
  }
};

// Application state
const appState = {
  currentView: 'landing-view',
  activeTab: 'rotations',
  selectedCity: 'Albany',
  previousCropId: 'C02',
  fieldCount: 1,
  selectedFieldNumber: 1,
  selectedFieldId: 'F001',
  customFieldBorders: {},
  drawBorderMode: false,
  selectedProfile: 'Balanced',
  profileIntensity: 50,
  selectedCrops: ['C01', 'C02', 'C03'],
  maxWaterDemand: 550,
  sensorEnabled: true,
  probeMode: 'dry', // 'wet' | 'dry'
  mapZoom: 1.0,
  selectedRankIndex: 0,
  // Latest packet from the Mobile Measurement Station (MMS), filled in by pollMms()
  mms: { connected: false, latest: null, lastJson: '' }
};

// Where the backend lives. Use relative URLs when served by FastAPI locally
const MMS_API_BASE = (location.protocol === 'file:' || location.port === '5500' || location.port === '3000')
  ? 'http://127.0.0.1:8000'
  : '';

// True when the MMS is plugged in, sending fresh data, and the sidebar sensor toggle is on
function isMmsLive() {
  return Boolean(appState.sensorEnabled && appState.mms && appState.mms.connected && appState.mms.latest);
}

// Ask the backend for the newest MMS reading
async function pollMms() {
  let next = { connected: false, latest: null };
  try {
    const res = await fetch(`${MMS_API_BASE}/mms/latest`, { cache: 'no-store' });
    if (res.ok) {
      const data = await res.json();
      next = { connected: Boolean(data.connected), latest: data.latest || null };
    }
  } catch (err) {
    // backend not running or offline, keep default
  }

  const nextJson = JSON.stringify(next);
  if (appState.mms && nextJson === appState.mms.lastJson) return;

  appState.mms = { ...next, lastJson: nextJson };
  // When live, the Wet/Dry decision follows the moisture sensor instead of manual buttons
  if (isMmsLive() && appState.mms.latest && appState.mms.latest.probe_mode) {
    appState.probeMode = appState.mms.latest.probe_mode;
  }
  renderDashboard();
}

function clip(val, lo, hi) {
  return Math.max(lo, Math.min(hi, val));
}

function mean(arr) {
  if (!arr.length) return 0;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

// Compute baseline and rotation scores using our multi-factor formula
function computeFieldBaselineSoil(field) {
  const ocScore = clip((field.oc - 1.0) / 4.0, 0, 1);
  const phScore = 1.0 - Math.min(Math.abs(field.ph - 6.5) / 2.0, 1.0);
  const bdScore = clip((1.7 - field.bd) / 0.6, 0, 1);
  const cecScore = clip(field.cec / 40.0, 0, 1);
  const textureScore = 1.0 - clip((Math.abs(field.sand - 40.0) + Math.abs(field.clay - 25.0)) / 60.0, 0, 1);
  return 0.25 * ocScore + 0.20 * phScore + 0.25 * bdScore + 0.15 * cecScore + 0.15 * textureScore;
}

function scoreSequenceForField(seqIds, field, profileName, sensorDryOverride) {
  const crops = seqIds.map((id) => CROPS_DATA[id]).filter(Boolean);
  const n = crops.length;
  const sBase = computeFieldBaselineSoil(field);
  const compactionNeed = clip((field.bd - 1.15) / 0.45, 0.2, 1.0);

  const regenScores = crops.map((c) => {
    const rootNorm = clip(c.rootM / 2.5, 0, 1);
    return 0.65 * c.build + 0.35 * (rootNorm * compactionNeed + c.build * (1.0 - compactionNeed));
  });
  const soilHealth = clip(0.65 * sBase + 0.35 * mean(regenScores), 0, 1);

  const effectiveMoisture = sensorDryOverride ? Math.max(0.14, field.moistureAvg - 0.11) : field.moistureAvg;
  const effectiveDrought = sensorDryOverride ? Math.min(0.68, field.drought2024 + 0.18) : field.drought2024;
  const droughtTrend = effectiveDrought - field.drought2023;
  const droughtScore = 1.0 - clip(effectiveDrought, 0, 1);
  const moistureScore = clip(effectiveMoisture / 0.5, 0, 1);
  const trendPenalty = clip(droughtTrend * 1.2, 0.0, 0.2);
  const supply = clip((droughtScore + moistureScore) / 2.0 - trendPenalty, 0, 1);

  const annualPrecip = (field.spring2024Precip + field.summer2024Precip + field.spring2023Precip + field.summer2023Precip) / 2.0;

  const waterScores = crops.map((c) => {
    const demandNorm = clip((c.water - 150) / 450.0, 0, 1);
    const baseStress = 1.0 - (1.0 - supply) * demandNorm;
    const precipAdequacy = clip(annualPrecip / Math.max(c.water * 1.15, 1.0), 0, 1);
    return clip(0.75 * baseStress + 0.25 * precipAdequacy, 0, 1);
  });
  const waterSafety = mean(waterScores);

  const anomScore = clip((field.anom2024 + 40) / 60.0, 0, 1);
  const ndviScore = clip(field.ndvi2024 / 0.9, 0, 1);
  const anomTrend = field.anom2024 - field.anom2023;
  const anomTrendPen = clip(-anomTrend / 40.0, 0, 0.25);
  const heatPen = clip((field.tempSummer - 24.5) / 8.0, 0, 0.15);
  const cBase = clip((anomScore + ndviScore) / 2.0 - 0.5 * (anomTrendPen + heatPen), 0, 1);

  const uniqueTypes = new Set(crops.map((c) => c.type)).size;
  const diversityScore = clip(uniqueTypes / Math.min(n, 3), 0, 1);
  const droughtHedge = mean(crops.map((c) => c.droughtTol));
  const resilience = clip(0.65 * cBase + 0.35 * (0.55 * diversityScore + 0.45 * droughtHedge), 0, 1);

  let repeatCount = 0;
  let sameTypeCount = 0;
  let nSynergy = 0;
  let rootAlt = 0;

  for (let i = 0; i < n; i++) {
    const curr = crops[i];
    const nxt = crops[(i + 1) % n];
    const stepW = 1.0 - 0.06 * i;
    if (curr.id === nxt.id) repeatCount += 1;
    else if (curr.type === nxt.type) sameTypeCount += 1;

    if (curr.nFix >= 0.5 && nxt.nFix === 0.0) {
      const demandW = clip(nxt.yieldT / 10.5, 0.3, 1.0);
      nSynergy += curr.nFix * demandW * stepW;
    }
    rootAlt += clip(Math.abs(curr.rootM - nxt.rootM) / 1.5, 0, 1) * stepW;
  }

  const ocDeficit = clip((3.0 - field.oc) / 2.0, 0, 1);
  const year1Bonus = 0.04 * (crops[0].nFix + crops[0].build) * (0.5 + 0.5 * ocDeficit);
  const nCarryBonus = clip(nSynergy / n + year1Bonus, 0, 0.25);
  const penaltyMult = clip(1.0 - 0.35 * (repeatCount / n) - 0.08 * (sameTypeCount / n), 0.65, 1.0);
  const transScore = clip((0.5 * clip(rootAlt / n, 0, 1) + 0.5 * clip(nSynergy / Math.max(n * 0.5, 1.0), 0, 1)) * penaltyMult, 0, 1);

  const nFixAvg = clip(0.85 * mean(crops.map((c) => c.nFix)) + 0.6 * nCarryBonus, 0, 1);
  const yieldAvg = mean(crops.map((c) => clip(c.yieldT / 12.0, 0, 1)));

  const compatScores = crops.map((c) => {
    const phCenter = (c.phMax + c.phMin) / 2.0;
    const phHalf = (c.phMax - c.phMin) / 2.0 + 0.5;
    const phS = Math.max(0, 1.0 - Math.abs(field.ph - phCenter) / phHalf);
    const clayCenter = (c.clayMax + c.clayMin) / 2.0;
    const clayHalf = (c.clayMax - c.clayMin) / 2.0 + 5.0;
    const clayS = Math.max(0, 1.0 - Math.abs(field.clay - clayCenter) / clayHalf);
    return (phS + clayS) / 2.0;
  });
  const soilCompat = clip(0.8 * mean(compatScores) + 0.2 * transScore, 0, 1);

  const baseBalanced = PRIORITY_PROFILES.Balanced;
  const targetWeights = PRIORITY_PROFILES[profileName] || baseBalanced;
  const clamped = clip(Number(appState.profileIntensity) || 50, 1, 100);
  // At 50 intensity use the profile's standard weights; scale emphasis smoothly from 1 to 100
  const powerScale = clamped <= 50
    ? 0.15 + ((clamped - 1) / 49) * 0.85
    : 1.0 + ((clamped - 50) / 50) * 1.50;

  let rawWeights;
  if (profileName === 'Balanced' || targetWeights === baseBalanced) {
    const uniform = 1 / 7;
    const balScale = clamped <= 50
      ? (clamped - 1) / 49
      : 1.0 + ((clamped - 50) / 50) * 1.75;
    rawWeights = {
      soil_health: uniform + (baseBalanced.soil_health - uniform) * balScale,
      water_stress: uniform + (baseBalanced.water_stress - uniform) * balScale,
      climate_res: uniform + (baseBalanced.climate_res - uniform) * balScale,
      nitrogen_fix: uniform + (baseBalanced.nitrogen_fix - uniform) * balScale,
      yield: uniform + (baseBalanced.yield - uniform) * balScale,
      drought_tol: uniform + (baseBalanced.drought_tol - uniform) * balScale,
      soil_compat: uniform + (baseBalanced.soil_compat - uniform) * balScale
    };
  } else {
    rawWeights = {
      soil_health: baseBalanced.soil_health + (targetWeights.soil_health - baseBalanced.soil_health) * powerScale,
      water_stress: baseBalanced.water_stress + (targetWeights.water_stress - baseBalanced.water_stress) * powerScale,
      climate_res: baseBalanced.climate_res + (targetWeights.climate_res - baseBalanced.climate_res) * powerScale,
      nitrogen_fix: baseBalanced.nitrogen_fix + (targetWeights.nitrogen_fix - baseBalanced.nitrogen_fix) * powerScale,
      yield: baseBalanced.yield + (targetWeights.yield - baseBalanced.yield) * powerScale,
      drought_tol: baseBalanced.drought_tol + (targetWeights.drought_tol - baseBalanced.drought_tol) * powerScale,
      soil_compat: baseBalanced.soil_compat + (targetWeights.soil_compat - baseBalanced.soil_compat) * powerScale
    };
  }
  const weightSum = Object.values(rawWeights).reduce((acc, v) => acc + Math.max(0.01, v), 0);
  const w = {};
  Object.keys(rawWeights).forEach((k) => {
    w[k] = Math.max(0.01, rawWeights[k]) / weightSum;
  });

  const rawTotal =
    w.soil_health * soilHealth +
    w.water_stress * waterSafety +
    w.climate_res * resilience +
    w.nitrogen_fix * nFixAvg +
    w.yield * yieldAvg +
    w.drought_tol * droughtHedge +
    w.soil_compat * soilCompat;

  const totalScore = clip(rawTotal * penaltyMult, 0, 1);

  return {
    seqIds,
    crops,
    label: crops.map((c) => c.name).join(' → '),
    totalScore,
    soilHealth,
    waterSafety,
    resilience,
    yieldPotential: clip(yieldAvg + 0.28, 0.35, 0.94),
    nFixAvg
  };
}

// Check whether 3 selected crops form a well-balanced rotation on their own
function isGoodThreeCropSelection(selectedIds) {
  if (selectedIds.length !== 3) return false;
  const crops = selectedIds.map((id) => CROPS_DATA[id]).filter(Boolean);
  if (crops.length !== 3) return false;

  const hasPerennial = crops.some((c) => c.isPerennial);
  const allPerennial = crops.every((c) => c.isPerennial);
  // Mixing perennial trees/vines with annual row crops on the same plot is not practical
  if (hasPerennial && !allPerennial) return false;

  // If all 3 are compatible perennial orchard/berry/vineyard crops with diverse families, it is a valid guild
  const uniqueTypes = new Set(crops.map((c) => c.type)).size;
  if (allPerennial) return uniqueTypes >= 2;

  // For annual field and vegetable crops, a good 3-crop rotation needs at least one nitrogen-fixing legume
  // and at least 2 distinct crop families so soil nitrogen is replenished and pest cycles are broken
  const hasLegume = crops.some((c) => c.nFix >= 0.5);
  return hasLegume && uniqueTypes >= 2;
}

// Build candidate 3-year sequences tailored to the user's selected crops
function buildCandidatePool(selectedIds) {
  const pool = [...CANDIDATE_SEQUENCES];
  const seen = new Set(pool.map((seq) => seq.join('-')));

  const addSeq = (seq) => {
    const key = seq.join('-');
    if (!seen.has(key) && new Set(seq).size === 3) {
      seen.add(key);
      pool.push(seq);
    }
  };

  if (selectedIds.length === 1) {
    const c1 = selectedIds[0];
    const crop1 = CROPS_DATA[c1];
    if (crop1 && crop1.isPerennial) {
      const partners = ['C04', 'C05', 'C06', 'C07', 'C08'].filter((id) => id !== c1);
      addSeq([c1, partners[0], partners[1]]);
      addSeq([partners[0], c1, partners[1]]);
    } else {
      const legumes = ['C03', 'C01', 'C12'].filter((id) => id !== c1);
      const cash = ['C02', 'C11', 'C13', 'C09', 'C10'].filter((id) => id !== c1);
      addSeq([legumes[0], c1, cash[0]]);
      addSeq([c1, legumes[0], cash[1]]);
      addSeq([legumes[1], c1, cash[0]]);
    }
  } else if (selectedIds.length === 2) {
    const [c1, c2] = selectedIds;
    const bothPerennial = CROPS_DATA[c1]?.isPerennial && CROPS_DATA[c2]?.isPerennial;
    const thirdOptions = bothPerennial
      ? ['C04', 'C05', 'C07', 'C08', 'C06']
      : ['C03', 'C01', 'C12', 'C02', 'C13', 'C11', 'C09'];
    thirdOptions.forEach((c3) => {
      if (c3 !== c1 && c3 !== c2) {
        addSeq([c1, c2, c3]);
        addSeq([c3, c1, c2]);
        addSeq([c1, c3, c2]);
      }
    });
  } else if (selectedIds.length === 3) {
    const [a, b, c] = selectedIds;
    if (isGoodThreeCropSelection(selectedIds)) {
      addSeq([a, b, c]);
      addSeq([b, c, a]);
      addSeq([c, a, b]);
      addSeq([a, c, b]);
      addSeq([b, a, c]);
      addSeq([c, b, a]);
    } else {
      // Build better 3-crop suggestions that keep 2 of their picks and swap in a nitrogen-fixing legume or compatible partner
      const legumes = ['C03', 'C12', 'C01'];
      legumes.forEach((leg) => {
        addSeq([leg, a, b]);
        addSeq([leg, a, c]);
        addSeq([leg, b, c]);
      });
    }
  } else if (selectedIds.length >= 4) {
    // Narrow their large selection down to balanced 3-crop subsets
    for (let i = 0; i < selectedIds.length; i++) {
      for (let j = i + 1; j < selectedIds.length; j++) {
        for (let k = j + 1; k < selectedIds.length; k++) {
          const sub = [selectedIds[i], selectedIds[j], selectedIds[k]];
          if (isGoodThreeCropSelection(sub)) {
            addSeq(sub);
            addSeq([sub[1], sub[0], sub[2]]);
          }
        }
      }
    }
    const annualPicks = selectedIds.filter((id) => !CROPS_DATA[id]?.isPerennial);
    if (annualPicks.length >= 2) {
      addSeq(['C03', annualPicks[0], annualPicks[1]]);
      addSeq(['C12', annualPicks[0], annualPicks[1]]);
    }
  }

  return pool;
}

function getRankedRotations() {
  const field = FIELDS_DATA[appState.selectedFieldId] || FIELDS_DATA.F001;
  const selectedIds = appState.selectedCrops || [];
  const maxWater = appState.maxWaterDemand;
  const dryProbeActive = Boolean(appState.sensorEnabled && appState.probeMode === 'dry');

  const candidatePool = buildCandidatePool(selectedIds);

  let filtered = candidatePool.filter((seq) => {
    const withinWater = seq.every((cid) => CROPS_DATA[cid].water <= maxWater);
    return withinWater;
  });

  if (filtered.length < 3) {
    filtered = candidatePool;
  }

  const goodThreePick = isGoodThreeCropSelection(selectedIds);

  const scored = filtered.map((seq) => {
    const base = scoreSequenceForField(seq, field, appState.selectedProfile, dryProbeActive);
    const matchCount = seq.filter((id) => selectedIds.includes(id)).length;

    // Prioritize sequences that incorporate the user's selected crops appropriately
    let selectionBonus = 0;
    if (selectedIds.length === 3 && goodThreePick) {
      selectionBonus = matchCount === 3 ? 0.18 : matchCount * 0.03;
    } else if (selectedIds.length >= 1 && selectedIds.length <= 3) {
      selectionBonus = Math.min(matchCount, 2) * 0.07;
    } else if (selectedIds.length >= 4) {
      selectionBonus = matchCount * 0.05;
    }

    // Factor in what the previous crop planted was so Year 01 does not repeat it
    const prevCrop = CROPS_DATA[appState.previousCropId];
    const year1Crop = CROPS_DATA[seq[0]];
    let prevCropDelta = 0;
    if (prevCrop && year1Crop) {
      if (prevCrop.id === year1Crop.id) {
        prevCropDelta = -0.08;
      } else if (prevCrop.nFix === 0.0 && year1Crop.nFix >= 0.5) {
        prevCropDelta = 0.04;
      } else if (prevCrop.type !== year1Crop.type) {
        prevCropDelta = 0.02;
      }
    }

    const adjustedTotal = clip(base.totalScore + prevCropDelta * 0.5, 0, 1);

    return {
      ...base,
      totalScore: adjustedTotal,
      matchCount,
      sortScore: adjustedTotal + selectionBonus + prevCropDelta
    };
  });

  scored.sort((a, b) => {
    if (Math.abs(b.sortScore - a.sortScore) > 0.0001) return b.sortScore - a.sortScore;
    if (Math.abs(b.totalScore - a.totalScore) > 0.0001) return b.totalScore - a.totalScore;
    if (Math.abs(b.waterSafety - a.waterSafety) > 0.0001) return b.waterSafety - a.waterSafety;
    return b.nFixAvg - a.nFixAvg;
  });

  // Deduplicate by rotation label so all top 5 rotations are distinct
  const uniqueScored = [];
  const seenLabels = new Set();
  scored.forEach((item) => {
    if (item && item.label && !seenLabels.has(item.label)) {
      seenLabels.add(item.label);
      uniqueScored.push(item);
    }
  });

  return uniqueScored;
}

// Build a distinct, data-grounded small quick analysis for each alternative rotation
function buildAlternativeQuickAnalysis(item, rankIdx, field, annualRain) {
  const c1 = item.crops[0]?.name || 'Year 1 crop';
  const c2 = item.crops[1]?.name || 'Year 2 crop';
  const c3 = item.crops[2]?.name || 'Year 3 crop';
  const maxWater = Math.max(...item.crops.map((c) => c.water || 450));
  const avgRoot = (item.crops.reduce((s, c) => s + (c.rootM || 1.0), 0) / Math.max(1, item.crops.length)).toFixed(1);
  const legumeCrops = item.crops.filter((c) => (c.nFix || 0) >= 0.5).map((c) => c.name);

  if (rankIdx === 1) {
    const legText = legumeCrops.length
      ? `${legumeCrops[0]} supplies biological nitrogen (${item.nFixAvg.toFixed(2)} N-fix)`
      : `alternating crop families preserves soil nutrients`;
    return `Starts with ${c1} followed by ${c2} and ${c3} (score ${item.totalScore.toFixed(2)}): ${legText}, achieving ${item.soilHealth.toFixed(2)} soil health and ${item.yieldPotential.toFixed(2)} yield potential with ${annualRain} mm rainfall.`;
  }
  if (rankIdx === 2) {
    return `Pairs ${c1} → ${c2} → ${c3} (score ${item.totalScore.toFixed(2)}) to keep peak water demand (${maxWater} mm) within ${annualRain} mm NASA rainfall and ${field.moistureAvg.toFixed(2)} RZM moisture (water safety ${item.waterSafety.toFixed(2)}, resilience ${item.resilience.toFixed(2)}).`;
  }
  if (rankIdx === 3) {
    return `Rotates ${c1}, ${c2}, and ${c3} across ${avgRoot} m average root depth on OC ${field.oc.toFixed(1)}% · pH ${field.ph.toFixed(1)} soil (score ${item.totalScore.toFixed(2)}), balancing ${item.soilHealth.toFixed(2)} soil health with ${item.yieldPotential.toFixed(2)} yield.`;
  }
  return `Sequence ${item.label} scores ${item.totalScore.toFixed(2)} at ${field.soilTempC.toFixed(1)}°C soil temperature, combining ${item.waterSafety.toFixed(2)} water safety, ${item.resilience.toFixed(2)} climate resilience, and ${item.nFixAvg.toFixed(2)} nitrogen fixation.`;
}

// Template logic evaluating the user's crop selection (to be combined with the backend API later)
function evaluateCropSelection(selectedIds, topPick) {
  const count = selectedIds.length;
  const pickedNames = selectedIds.map((id) => CROPS_DATA[id]?.name).filter(Boolean);
  const recLabel = topPick ? topPick.label : 'Soybeans or Small Grains → Field Corn (Silage or Grain) → Hay or Alfalfa (Haylage)';
  const sensorClause = appState.sensorEnabled
    ? `MMS Mobile Measuring Station active (${appState.probeMode === 'dry' ? 'Dry soil mode' : 'Wet soil mode'})`
    : 'satellite baseline only (local MMS sensor disabled)';

  if (count === 0) {
    return {
      bannerEyebrow: 'SUGGESTION / PICK YOUR CROPS IN THE SIDEBAR',
      bannerTitle: 'This might be a better idea to start with.',
      heading: 'Suggestion: Pick 1 to 3 crops in the sidebar',
      line1: 'You have not selected any crops yet — try picking your preferred New York crops in the Crops dropdown on the left.',
      line2: `Better suggestion for this field: ${recLabel} (${sensorClause}).`
    };
  }

  if (count >= 4) {
    return {
      bannerEyebrow: `WARNING / ${count} CROPS SELECTED (TOO MANY)`,
      bannerTitle: 'Picking this many crops is bad — try this better 3-crop plan.',
      heading: 'Why picking this many crops is bad',
      line1: `Selecting ${count} crops at once (${pickedNames.slice(0, 4).join(', ')}${count > 4 ? '...' : ''}) splits field management, mixes incompatible harvest schedules, and weakens soil recovery.`,
      line2: `Better suggestion: Narrow your field down to ${recLabel} for stronger soil nitrogen and higher yield (${sensorClause}).`
    };
  }

  if (count === 3 && isGoodThreeCropSelection(selectedIds)) {
    return {
      bannerEyebrow: 'GOOD SELECTION / BALANCED THREE-YEAR ROTATION',
      bannerTitle: 'This is a good crop selection for your field.',
      heading: 'This is a good crop mix — why it works',
      line1: `Your 3 selected crops (${pickedNames.join(', ')}) form a strong rotation that balances nitrogen fixation, root depth, and pest resistance.`,
      line2: `Recommended 3-year sequence: ${recLabel} within your ${appState.maxWaterDemand} mm water budget • ${sensorClause}.`
    };
  }

  // Case: 1, 2, or 3 crops where a better suggestion is recommended
  if (count === 1) {
    return {
      bannerEyebrow: 'SUGGESTION / 1 CROP SELECTED — THIS MIGHT BE A BETTER IDEA',
      bannerTitle: 'This might be a better idea than planting a single crop.',
      heading: 'Suggestion: This might be a better idea',
      line1: `You only picked ${pickedNames[0]} — planting 1 crop repeatedly depletes soil nutrients and builds up crop-specific pests.`,
      line2: `Better suggestion: Rotate ${pickedNames[0]} inside ${recLabel} to restore nitrogen and protect topsoil (${sensorClause}).`
    };
  }

  if (count === 2) {
    return {
      bannerEyebrow: 'SUGGESTION / 2 CROPS SELECTED — THIS MIGHT BE A BETTER IDEA',
      bannerTitle: 'This might be a better idea for a full 3-year cycle.',
      heading: 'Suggestion: This might be a better idea',
      line1: `You picked ${pickedNames.join(' and ')} — adding a 3rd complementary crop completes a 3-year cycle and boosts organic carbon.`,
      line2: `Better suggestion: Try ${recLabel} to pair your selection with balanced soil recovery (${sensorClause}).`
    };
  }

  // count === 3 but not an optimal combination (e.g. missing a legume or mixing perennials & annuals)
  return {
    bannerEyebrow: 'SUGGESTION / 3 CROPS SELECTED — THIS MIGHT BE A BETTER IDEA',
    bannerTitle: 'This might be a better idea for soil balance.',
    heading: 'Suggestion: This might be a better idea',
    line1: `Your 3 picks (${pickedNames.join(', ')}) either lack a nitrogen-fixing legume or mix perennial tree/vine crops with annual row crops.`,
    line2: `Better suggestion: Swap in a complementary nitrogen builder with ${recLabel} (${sensorClause}).`
  };
}

// Switch between top-level views with smooth fade transitions and browser history support
function navigateToView(viewId, pushHistory = true) {
  const allViews = document.querySelectorAll('.app-view');
  const target = document.getElementById(viewId);
  if (!target) return;

  closeAllDropdowns();

  allViews.forEach((v) => {
    v.classList.remove('visible-view');
    v.classList.remove('active-view');
  });

  target.classList.add('active-view');
  window.scrollTo({ top: 0, behavior: 'instant' });

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      target.classList.add('visible-view');
      if (viewId === 'location-view' && typeof window.refreshFarmingAuraLocationMap === 'function') {
        window.refreshFarmingAuraLocationMap();
      } else if (viewId === 'dashboard-view' && typeof window.refreshFarmingAuraFieldMap === 'function') {
        window.refreshFarmingAuraFieldMap();
      }
    });
  });

  setTimeout(() => {
    if (viewId === 'location-view' && typeof window.refreshFarmingAuraLocationMap === 'function') {
      window.refreshFarmingAuraLocationMap();
    } else if (viewId === 'dashboard-view' && typeof window.refreshFarmingAuraFieldMap === 'function') {
      window.refreshFarmingAuraFieldMap();
    }
  }, 120);

  if (pushHistory && window.history && typeof window.history.pushState === 'function') {
    const hashTarget = viewId === 'landing-view' ? window.location.pathname + window.location.search : `#${viewId}`;
    if (window.location.hash !== `#${viewId}`) {
      try {
        window.history.pushState({ viewId }, '', hashTarget);
      } catch (_err) {
        // ignore file:// history restrictions
      }
    }
  }

  appState.currentView = viewId;
  renderAll();
}

// Switch between the 3 tabs inside the Dashboard
function switchDashboardTab(tabKey) {
  appState.activeTab = tabKey;
  closeAllDropdowns();

  const tabBtns = document.querySelectorAll('.dash-tab-btn');
  tabBtns.forEach((btn) => {
    btn.classList.toggle('active-tab', btn.dataset.tab === tabKey);
  });

  const panels = document.querySelectorAll('.dash-tab-panel');
  panels.forEach((panel) => {
    const isMatch = panel.id === `tab-panel-${tabKey}`;
    panel.classList.remove('visible-panel');
    panel.classList.toggle('active-panel', isMatch);
    if (isMatch) {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          panel.classList.add('visible-panel');
          if (tabKey === 'map' && typeof window.refreshFarmingAuraFieldMap === 'function') {
            window.refreshFarmingAuraFieldMap();
          }
        });
      });
    }
  });

  if (tabKey === 'map') {
    setTimeout(() => {
      if (typeof window.refreshFarmingAuraFieldMap === 'function') {
        window.refreshFarmingAuraFieldMap();
      }
    }, 100);
  }

  // Update sensor switch color to match Figma (green on Tab 2/3, brown on Tab 1)
  const sensorSwitch = document.getElementById('sidebar-sensor-switch');
  if (sensorSwitch) {
    sensorSwitch.classList.toggle('sensor-green', tabKey === 'map' || tabKey === 'sensors');
  }

  renderDashboard();
}

// Select a city on Step 1 map or dropdown
function selectCityLocation(cityKey) {
  const city = CITY_LOCATIONS[cityKey];
  if (!city) return;

  appState.selectedCity = cityKey;
  appState.selectedFieldId = city.defaultField;
  const numFromId = parseInt(city.defaultField.replace(/\D/g, ''), 10) || 1;
  appState.selectedFieldNumber = Math.min(numFromId, appState.fieldCount);

  const regionBox = document.getElementById('step1-region-selected');
  const latLonBox = document.getElementById('step1-latlon-display');
  const latInput = document.getElementById('step1-lat-input');
  const lonInput = document.getElementById('step1-lon-input');
  const triggerText = document.getElementById('step1-dropdown-label');

  if (regionBox) regionBox.textContent = city.label;
  if (latLonBox) latLonBox.textContent = city.displayCoords;
  if (latInput) latInput.value = city.lat;
  if (lonInput) lonInput.value = city.lon;
  if (triggerText) triggerText.textContent = city.label;

  document.querySelectorAll('.city-pin').forEach((pin) => {
    pin.classList.toggle('selected-city', pin.dataset.city === cityKey);
  });

  document.querySelectorAll('.region-dropdown-item').forEach((item) => {
    item.classList.toggle('active-item', item.dataset.city === cityKey);
  });
}

// Format a 1-based field number as F001, F002, ..., F346, etc.
function formatFieldCode(fieldNum) {
  const n = Math.max(1, Math.floor(fieldNum) || 1);
  return `F${String(n).padStart(3, '0')}`;
}

// Map any 1-based field number (1..N) to one of our 8 base field profiles (F001..F008) for soil/climate simulation
function getFieldIdForNumber(fieldNum) {
  const allIds = Object.keys(FIELDS_DATA);
  const idx = (Math.max(1, fieldNum) - 1) % allIds.length;
  return allIds[idx];
}

// Get display label for a 1-based field number (Field F001, Field F002, ..., Field F346)
function getFieldDisplayName(fieldNum) {
  return `Field ${formatFieldCode(fieldNum)}`;
}

// Update total number of fields from the typed input (no upper cap)
function setFieldCount(count) {
  const n = Math.max(1, Math.floor(count) || 1);
  appState.fieldCount = n;
  if (appState.selectedFieldNumber > n) {
    appState.selectedFieldNumber = n;
    appState.selectedFieldId = getFieldIdForNumber(n);
  }
}

// Compute an automatic square/rectangle border position on the map for every field 1..totalFields
function computeAutoFieldBorder(fieldNum, totalFields) {
  const n = Math.max(1, totalFields);
  const idx = Math.max(0, Math.min(n - 1, fieldNum - 1));
  const cols = Math.ceil(Math.sqrt(n * 1.45));
  const rows = Math.ceil(n / cols);

  const padX = n <= 16 ? 4.0 : n <= 64 ? 2.5 : 1.5;
  const padY = n <= 16 ? 5.0 : n <= 64 ? 3.0 : 1.5;
  const gapX = n <= 16 ? 1.8 : n <= 64 ? 0.9 : n <= 200 ? 0.4 : 0.15;
  const gapY = n <= 16 ? 2.2 : n <= 64 ? 1.1 : n <= 200 ? 0.5 : 0.15;

  const availW = Math.max(10, 100 - padX * 2 - gapX * Math.max(0, cols - 1));
  const availH = Math.max(10, 100 - padY * 2 - gapY * Math.max(0, rows - 1));
  const cellW = availW / cols;
  const cellH = availH / rows;
  const c = idx % cols;
  const r = Math.floor(idx / cols);

  return {
    left: Number((padX + c * (cellW + gapX)).toFixed(3)),
    top: Number((padY + r * (cellH + gapY)).toFixed(3)),
    width: Number(cellW.toFixed(3)),
    height: Number(cellH.toFixed(3))
  };
}

// Render the field count input, active field selector, and all X square field borders on the Tab 2 satellite map
function renderMapFieldBorders() {
  const countInput = document.getElementById('map-field-count-input');
  const activeSelect = document.getElementById('map-active-field-select');
  const bordersLayer = document.getElementById('map-borders-layer');
  const mapCanvas = document.getElementById('satellite-map-canvas');
  const drawModeBtn = document.getElementById('map-draw-mode-btn');
  const drawHint = document.getElementById('map-draw-hint');

  if (countInput && document.activeElement !== countInput) {
    countInput.value = String(appState.fieldCount);
  }

  if (drawModeBtn) {
    drawModeBtn.classList.toggle('active-draw-mode', appState.drawBorderMode);
    drawModeBtn.textContent = appState.drawBorderMode ? 'Drawing border... (click & drag)' : 'Draw border on map';
  }
  if (mapCanvas) {
    mapCanvas.classList.toggle('drawing-cursor', appState.drawBorderMode);
  }
  if (drawHint) {
    const activeCode = formatFieldCode(appState.selectedFieldNumber);
    drawHint.textContent = appState.drawBorderMode
      ? `Draw mode active: Click and drag on the satellite map below to draw the square border for ${activeCode}.`
      : `Showing all ${appState.fieldCount} field rectangle${appState.fieldCount === 1 ? '' : 's'} (F001–${formatFieldCode(appState.fieldCount)}). Click any square on the map to select it, or click "Draw border on map" to draw custom borders.`;
  }

  if (activeSelect) {
    activeSelect.innerHTML = '';
    const selectFrag = document.createDocumentFragment();
    for (let num = 1; num <= appState.fieldCount; num++) {
      const opt = document.createElement('option');
      opt.value = String(num);
      opt.textContent = `${formatFieldCode(num)} (${getFieldDisplayName(num)})`;
      if (num === appState.selectedFieldNumber) opt.selected = true;
      selectFrag.appendChild(opt);
    }
    activeSelect.appendChild(selectFrag);
  }

  if (!bordersLayer) return;
  bordersLayer.innerHTML = '';

  const total = Math.max(1, appState.fieldCount);
  const fontSizePx = total <= 12 ? 11.5 : total <= 36 ? 9.5 : total <= 100 ? 7.5 : total <= 250 ? 6 : 5;
  const borderWidthPx = total <= 36 ? 1.5 : 1;

  const frag = document.createDocumentFragment();
  for (let num = 1; num <= total; num++) {
    const code = formatFieldCode(num);
    const rect = appState.customFieldBorders[num] || computeAutoFieldBorder(num, total);
    const box = document.createElement('button');
    box.type = 'button';
    box.className = `field-border-square ${num === appState.selectedFieldNumber ? 'active-border-square' : ''}`;
    box.style.left = `${rect.left}%`;
    box.style.top = `${rect.top}%`;
    box.style.width = `${rect.width}%`;
    box.style.height = `${rect.height}%`;
    box.style.fontSize = `${fontSizePx}px`;
    box.style.borderWidth = `${borderWidthPx}px`;
    box.title = `Select ${getFieldDisplayName(num)}`;
    box.textContent = code;
    box.addEventListener('click', (e) => {
      if (appState.drawBorderMode) return;
      e.stopPropagation();
      appState.selectedFieldNumber = num;
      appState.selectedFieldId = getFieldIdForNumber(num);
      appState.selectedRankIndex = 0;
      renderDashboard();
    });
    frag.appendChild(box);
  }
  bordersLayer.appendChild(frag);
}

// Build 5-year temperature and rainfall series (2020 to 2024) for a field and render the dual-Y-axis SVG line chart
function renderClimateLineChart(field) {
  const svg = document.getElementById('climate-line-chart-svg');
  if (!svg) return;

  const years = [2020, 2021, 2022, 2023, 2024];
  const rain2023 = Math.round(field.spring2023Precip + field.summer2023Precip);
  const rain2024 = Math.round(field.spring2024Precip + field.summer2024Precip);

  // Use true 2020-2024 NASA POWER PRECTOTCORR series when available
  const rainSeries =
    Array.isArray(field.rainSeries2020_2024) && field.rainSeries2020_2024.length === 5
      ? field.rainSeries2020_2024.map((v) => Math.round(Number(v)))
      : [rain2023, rain2023, rain2023, rain2023, rain2024];

  const t2024 = Number(field.tempSummer || 21.0);
  // Use true 2020-2024 NASA POWER T2M summer series when available
  const tempSeriesC =
    Array.isArray(field.tempSeries2020_2024) && field.tempSeries2020_2024.length === 5
      ? field.tempSeries2020_2024.map((v) => Number(Number(v).toFixed(1)))
      : [t2024, t2024, t2024, t2024, t2024];

  const toF = (c) => Math.round((c * 9) / 5 + 32);

  // Chart coordinate space inside 820x300 viewBox
  const padLeft = 120;
  const padRight = 104;
  const padTop = 34;
  const padBottom = 52;
  const plotW = 820 - padLeft - padRight;
  const plotH = 300 - padTop - padBottom;
  // Inset the first/last data points from the Y-axes so centered point labels never overlap axis ticks
  const xInset = 54;

  // Dynamic axis bounds fitted to the true NASA POWER temperature and rainfall range
  const minT = Math.min(...tempSeriesC);
  const maxT = Math.max(...tempSeriesC);
  const tempMin = Math.floor(Math.min(18, minT - 2));
  const tempMax = Math.ceil(Math.max(26, maxT + 2));

  const minR = Math.min(...rainSeries);
  const maxR = Math.max(...rainSeries);
  const rainMin = Math.max(0, Math.floor((minR - 80) / 50) * 50);
  const rainMax = Math.ceil((maxR + 80) / 50) * 50;

  const xAt = (i) => padLeft + xInset + (i / (years.length - 1)) * (plotW - xInset * 2);
  const yTemp = (c) => padTop + (1 - clip((c - tempMin) / (tempMax - tempMin), 0, 1)) * plotH;
  const yRain = (mm) => padTop + (1 - clip((mm - rainMin) / (rainMax - rainMin), 0, 1)) * plotH;

  let gridHtml = '';
  const ticks = 4;
  for (let t = 0; t <= ticks; t++) {
    const frac = t / ticks;
    const y = padTop + (1 - frac) * plotH;
    const cVal = (tempMin + frac * (tempMax - tempMin)).toFixed(0);
    const fVal = toF(Number(cVal));
    const rVal = Math.round(rainMin + frac * (rainMax - rainMin));

    gridHtml += `
      <line x1="${padLeft}" y1="${y}" x2="${padLeft + plotW}" y2="${y}" stroke="#e5dfd3" stroke-dasharray="4 4" stroke-width="1" />
      <text x="${padLeft - 10}" y="${y + 4}" text-anchor="end" fill="#b8501c" font-size="11" font-weight="600">${cVal}°C / ${fVal}°F</text>
      <text x="${padLeft + plotW + 10}" y="${y + 4}" text-anchor="start" fill="#183925" font-size="11" font-weight="600">${rVal} mm</text>
    `;
  }

  // Axis titles
  const leftAxisY = padTop + plotH / 2;
  const rightAxisY = padTop + plotH / 2;
  gridHtml += `
    <text x="20" y="${leftAxisY}" text-anchor="middle" fill="#b8501c" font-size="11.5" font-weight="700" transform="rotate(-90 20 ${leftAxisY})">Temperature (°C / °F)</text>
    <text x="802" y="${rightAxisY}" text-anchor="middle" fill="#183925" font-size="11.5" font-weight="700" transform="rotate(90 802 ${rightAxisY})">Rainfall (mm)</text>
    <text x="${padLeft + plotW / 2}" y="292" text-anchor="middle" fill="#4f5d53" font-size="12" font-weight="700">Years (5-Year Historical Window)</text>
  `;

  // X-axis year labels and vertical guides
  years.forEach((yr, idx) => {
    const x = xAt(idx);
    gridHtml += `
      <line x1="${x}" y1="${padTop}" x2="${x}" y2="${padTop + plotH}" stroke="#ece7dc" stroke-width="1" />
      <text x="${x}" y="${padTop + plotH + 22}" text-anchor="middle" fill="#2c3e31" font-size="12" font-weight="600">${yr}</text>
    `;
  });

  // Polyline paths
  const tempPoints = tempSeriesC.map((c, i) => `${xAt(i)},${yTemp(c)}`).join(' ');
  const rainPoints = rainSeries.map((mm, i) => `${xAt(i)},${yRain(mm)}`).join(' ');

  let markersHtml = `
    <polyline fill="none" stroke="#b8501c" stroke-width="3" points="${tempPoints}" />
    <polyline fill="none" stroke="#183925" stroke-width="3" points="${rainPoints}" />
  `;

  // Place each point's label on the outer side of the two series so labels never collide with each other or dots
  years.forEach((_, i) => {
    const x = xAt(i);
    const yT = yTemp(tempSeriesC[i]);
    const yR = yRain(rainSeries[i]);
    const c = tempSeriesC[i];
    const f = toF(c);
    const mm = rainSeries[i];

    const tempIsHigher = yT <= yR;
    const tempLabelY = tempIsHigher ? yT - 12 : yT + 20;
    const rainLabelY = tempIsHigher ? yR + 20 : yR - 12;

    markersHtml += `
      <circle cx="${x}" cy="${yT}" r="5" fill="#b8501c" stroke="#ffffff" stroke-width="1.5" />
      <circle cx="${x}" cy="${yR}" r="5" fill="#183925" stroke="#ffffff" stroke-width="1.5" />
      <text x="${x}" y="${tempLabelY}" text-anchor="middle" fill="#b8501c" stroke="#faf8f2" stroke-width="3" paint-order="stroke" font-size="10.5" font-weight="700">${c}°C (${f}°F)</text>
      <text x="${x}" y="${rainLabelY}" text-anchor="middle" fill="#183925" stroke="#faf8f2" stroke-width="3" paint-order="stroke" font-size="10.5" font-weight="700">${mm} mm</text>
    `;
  });

  svg.innerHTML = gridHtml + markersHtml;

  // Update the description below the chart explaining how temp/rainfall increases & decreases work
  const tempDiffC = Number((tempSeriesC[4] - tempSeriesC[0]).toFixed(1));
  const tempDiffF = Number(((tempDiffC * 9) / 5).toFixed(1));
  const rainDiff = rainSeries[4] - rainSeries[0];

  const tempExplEl = document.getElementById('climate-temp-explanation');
  const rainExplEl = document.getElementById('climate-rain-explanation');

  const activeFieldLabel = getFieldDisplayName(appState.selectedFieldNumber);
  if (tempExplEl) {
    const signC = tempDiffC >= 0 ? `+${tempDiffC}°C` : `${tempDiffC}°C`;
    const signF = tempDiffF >= 0 ? `+${tempDiffF}°F` : `${tempDiffF}°F`;
    tempExplEl.textContent = `From 2020 to 2024 on ${activeFieldLabel}, summer temperature shifted by ${signC} (${signF}). An increase in temperature (+°C / +°F) raises evapotranspiration and soil heat stress, which penalizes shallow-rooted crops and increases water demand. A decrease in temperature (-°C / -°F) slows soil moisture loss and favors cool-season New York crops like Cabbage, Potatoes, Onions, and Green Peas.`;
  }

  if (rainExplEl) {
    const signRain = rainDiff >= 0 ? `+${rainDiff} mm` : `${rainDiff} mm`;
    rainExplEl.textContent = `From 2020 to 2024 on ${activeFieldLabel}, annual growing-season rainfall changed by ${signRain} (${rainSeries[0]} mm to ${rainSeries[4]} mm). An increase in rainfall (+mm) recharges root-zone soil moisture and supports higher-transpiration crops like Hay & Alfalfa and Field Corn. A decrease in rainfall (-mm) elevates drought risk and shifts our rotation score toward water-safe legumes like Soybeans or Small Grains.`;
  }
}

// Close all custom dropdowns and popovers
function closeAllDropdowns() {
  document.querySelectorAll('.field-dropdown-menu, .cream-popover-menu, .region-dropdown-menu').forEach((menu) => {
    menu.classList.remove('open');
  });
  document.querySelectorAll('.custom-select-trigger').forEach((trig) => {
    trig.classList.remove('open');
  });
}

// Toggle a specific custom dropdown menu
function toggleDropdown(menuId, triggerId, event) {
  if (event) event.stopPropagation();
  const menu = document.getElementById(menuId);
  const trigger = triggerId ? document.getElementById(triggerId) : null;
  if (!menu) return;

  const wasOpen = menu.classList.contains('open');
  closeAllDropdowns();

  if (!wasOpen) {
    menu.classList.add('open');
    if (trigger) trigger.classList.add('open');
  }
}

// Update the Dashboard UI with current field, profile, crops selection, water slider, and sensor state
function renderDashboard() {
  const field = FIELDS_DATA[appState.selectedFieldId] || FIELDS_DATA.F001;
  const ranked = getRankedRotations();
  const topPick = ranked[appState.selectedRankIndex] || ranked[0];
  const selectedIds = appState.selectedCrops || [];

  // Sidebar trigger labels for Previous Crop (single-select), Priority Profile, and Crops
  const prevSummaryText = CROPS_DATA[appState.previousCropId]?.name || 'Field Corn (Silage or Grain)';
  const prevCropTrigLabel = document.getElementById('sidebar-prev-crop-label');
  const profileTrigLabel = document.getElementById('sidebar-profile-label');
  const equipTrigLabel = document.getElementById('sidebar-equip-label');
  if (prevCropTrigLabel) prevCropTrigLabel.textContent = prevSummaryText;
  if (profileTrigLabel) profileTrigLabel.textContent = appState.selectedProfile;
  if (equipTrigLabel) {
    if (selectedIds.length === 0) {
      equipTrigLabel.textContent = 'Select crops...';
    } else if (selectedIds.length === 1) {
      equipTrigLabel.textContent = CROPS_DATA[selectedIds[0]]?.name || '1 crop selected';
    } else {
      equipTrigLabel.textContent = `${selectedIds.length} crops selected`;
    }
  }

  // Highlight active items inside sidebar dropdowns
  document.querySelectorAll('[data-prev-crop-option]').forEach((btn) => {
    btn.classList.toggle('active-option', btn.dataset.prevCropOption === appState.previousCropId);
  });
  document.querySelectorAll('[data-profile-option]').forEach((btn) => {
    btn.classList.toggle('active-option', btn.dataset.profileOption === appState.selectedProfile);
  });
  document.querySelectorAll('[data-crop-option]').forEach((btn) => {
    const cid = btn.dataset.cropOption;
    const isChecked = selectedIds.includes(cid);
    btn.classList.toggle('active-option', isChecked);
    const box = btn.querySelector('.crop-check-box');
    if (box) box.textContent = isChecked ? '✓' : '';
  });

  // Priority profile intensity slider readout and track fill (1-100)
  const intensityVal = clip(appState.profileIntensity || 50, 1, 100);
  const intensityPct = Math.round(((intensityVal - 1) / 99) * 100);
  const intensityBg = `linear-gradient(to right, #8f4419 0%, #8f4419 ${intensityPct}%, #e7b892 ${intensityPct}%, #e7b892 100%)`;

  const intensityReadout = document.getElementById('profile-intensity-readout');
  const intensitySlider = document.getElementById('profile-intensity-slider');
  const onboardingReadout = document.getElementById('onboarding-intensity-readout');
  const onboardingSlider = document.getElementById('onboarding-intensity-slider');

  if (intensityReadout) intensityReadout.textContent = `${intensityVal} / 100`;
  if (intensitySlider) {
    intensitySlider.value = String(intensityVal);
    intensitySlider.style.background = intensityBg;
  }
  if (onboardingReadout) onboardingReadout.textContent = `${intensityVal} / 100`;
  if (onboardingSlider) {
    onboardingSlider.value = String(intensityVal);
    onboardingSlider.style.background = intensityBg;
  }

  // Water demand slider readout and track fill
  const waterReadout = document.getElementById('water-demand-readout');
  const waterSlider = document.getElementById('water-demand-slider');
  if (waterReadout) waterReadout.textContent = `${appState.maxWaterDemand} mm / yr`;
  if (waterSlider) {
    const pct = Math.round(((appState.maxWaterDemand - 250) / (650 - 250)) * 100);
    waterSlider.style.background = `linear-gradient(to right, #8f4419 0%, #8f4419 ${pct}%, #e7b892 ${pct}%, #e7b892 100%)`;
  }

  // Sensor switch state
  const sensorSwitch = document.getElementById('sidebar-sensor-switch');
  const sensorStatus = document.getElementById('sidebar-sensor-status');
  if (sensorSwitch) sensorSwitch.classList.toggle('active', appState.sensorEnabled);
  if (sensorStatus) {
    if (isMmsLive()) {
      sensorStatus.textContent = 'Live · MMS connected';
    } else {
      sensorStatus.textContent = appState.sensorEnabled ? 'Enabled · demo (MMS offline)' : 'Disabled · satellite only';
    }
  }

  // Header eyebrow, title, and subtitles
  const activeFieldCode = formatFieldCode(appState.selectedFieldNumber);
  const activeFieldName = getFieldDisplayName(appState.selectedFieldNumber);
  const dashEyebrow = document.getElementById('dash-eyebrow-text');
  const dashMainTitle = document.getElementById('dash-main-title');
  const dashSubLeft = document.getElementById('dash-subtitle-left');
  const dashSubRight = document.getElementById('dash-subtitle-right');
  if (dashEyebrow) {
    dashEyebrow.textContent = `FIELD ${activeFieldCode} / DEMO DATA`;
  }
  if (dashMainTitle) {
    dashMainTitle.textContent = activeFieldName;
  }
  if (dashSubLeft) {
    const fieldCountText = appState.fieldCount === 1 ? '1 field' : `${appState.fieldCount} fields`;
    dashSubLeft.textContent = `Previous crop(s): ${prevSummaryText} • ${fieldCountText} • ${appState.selectedProfile} (${intensityVal}/100)`;
  }
  if (dashSubRight) {
    const pickedNames = selectedIds.map((id) => CROPS_DATA[id]?.name).filter(Boolean);
    if (pickedNames.length === 0) {
      dashSubRight.textContent = 'Crops selected: none yet (pick crops in sidebar)';
    } else if (pickedNames.length <= 3) {
      dashSubRight.textContent = `Crops selected (${pickedNames.length}): ${pickedNames.join(', ')}`;
    } else {
      dashSubRight.textContent = `Crops selected (${pickedNames.length} — too many): ${pickedNames.slice(0, 3).join(', ')} + ${pickedNames.length - 3} more`;
    }
  }

  // Top 4 KPI cards
  const annualRain = Math.round(field.spring2024Precip + field.summer2024Precip);
  const kpiSoilVal = document.getElementById('kpi-soil-val');
  const kpiSoilSub = document.getElementById('kpi-soil-sub');
  const kpiRainVal = document.getElementById('kpi-rain-val');
  const kpiRainSub = document.getElementById('kpi-rain-sub');
  const kpiMoistureVal = document.getElementById('kpi-moisture-val');
  const kpiMoistureSub = document.getElementById('kpi-moisture-sub');
  const kpiTempVal = document.getElementById('kpi-temp-val');
  const kpiTempSub = document.getElementById('kpi-temp-sub');

  const hasNasaData = Boolean(field.nasaSource && field.nasaSource !== 'demo');
  const coordBadge =
    typeof field.lat === 'number' && typeof field.lon === 'number'
      ? `${field.lat.toFixed(2)}°, ${field.lon.toFixed(2)}°`
      : '';

  if (kpiSoilVal && topPick) kpiSoilVal.textContent = `${topPick.soilHealth.toFixed(2)} SH`;
  if (kpiSoilSub) {
    const unitShort = field.soilMapUnit ? field.soilMapUnit.split(',')[0] : 'USDA SSURGO';
    kpiSoilSub.textContent = hasNasaData
      ? `OC ${field.oc.toFixed(2)}% · pH ${field.ph.toFixed(2)} · ${unitShort}`
      : `OC ${field.oc.toFixed(2)}% · pH ${field.ph.toFixed(2)}`;
  }
  if (kpiRainVal) kpiRainVal.textContent = `${annualRain} mm`;
  if (kpiRainSub) {
    const spRain = Math.round(field.spring2024Precip || 0);
    const suRain = Math.round(field.summer2024Precip || 0);
    kpiRainSub.textContent = hasNasaData
      ? `NASA POWER · Spring ${spRain} mm · Summer ${suRain} mm`
      : `Spring ${spRain} mm · Summer ${suRain} mm`;
  }
  if (kpiMoistureVal) kpiMoistureVal.textContent = `${field.moistureAvg.toFixed(2)} RZM`;
  if (kpiMoistureSub) {
    kpiMoistureSub.textContent = hasNasaData
      ? `NASA GWETROOT · ${coordBadge}`
      : 'Sample soil moisture';
  }
  if (kpiTempVal) kpiTempVal.textContent = `${field.soilTempC.toFixed(1)}°C`;
  if (kpiTempSub) {
    const tempStatus = field.soilTempC >= 12.0 ? 'Above planting threshold' : 'Cool topsoil (<12°C)';
    kpiTempSub.textContent = hasNasaData ? `NASA POWER · ${tempStatus}` : tempStatus;
  }

  // Tab 1: 3-year recommended rotation cards
  if (topPick && topPick.crops.length >= 3) {
    for (let i = 0; i < 3; i++) {
      const c = topPick.crops[i];
      const nameEl = document.getElementById(`year-0${i + 1}-crop`);
      const roleEl = document.getElementById(`year-0${i + 1}-role`);
      if (nameEl) nameEl.textContent = c.name;
      if (roleEl) roleEl.textContent = c.roleTag;
    }
  }

  // Evaluate crop selection and update banner + feedback card
  const evalResult = evaluateCropSelection(selectedIds, topPick);
  const bannerEyebrow = document.getElementById('rotation-banner-eyebrow');
  const bannerTitle = document.getElementById('rotation-banner-title');
  const whyHeading = document.getElementById('why-won-heading');
  const whyLine1 = document.getElementById('why-won-line-1');
  const whyLine2 = document.getElementById('why-won-line-2');

  if (bannerEyebrow) bannerEyebrow.textContent = evalResult.bannerEyebrow;
  if (bannerTitle) bannerTitle.textContent = evalResult.bannerTitle;
  if (whyHeading) whyHeading.textContent = evalResult.heading;
  if (whyLine1) whyLine1.textContent = evalResult.line1;
  if (whyLine2) whyLine2.textContent = evalResult.line2;

  // Rotation score breakdown bars (5 metrics from 0 to 1, averaged into a score out of 100)
  const barSoil = document.getElementById('bar-soil-health');
  const barWater = document.getElementById('bar-water-safety');
  const barRes = document.getElementById('bar-resilience');
  const barYield = document.getElementById('bar-yield-potential');
  const barNFix = document.getElementById('bar-nitrogen-fix');

  const valSoil = document.getElementById('val-soil-health');
  const valWater = document.getElementById('val-water-safety');
  const valRes = document.getElementById('val-resilience');
  const valYield = document.getElementById('val-yield-potential');
  const valNFix = document.getElementById('val-nitrogen-fix');
  const avgScoreBadge = document.getElementById('breakdown-avg-score');

  if (topPick) {
    if (barSoil) barSoil.style.width = `${Math.round(topPick.soilHealth * 100)}%`;
    if (barWater) barWater.style.width = `${Math.round(topPick.waterSafety * 100)}%`;
    if (barRes) barRes.style.width = `${Math.round(topPick.resilience * 100)}%`;
    if (barYield) barYield.style.width = `${Math.round(topPick.yieldPotential * 100)}%`;
    if (barNFix) barNFix.style.width = `${Math.round(topPick.nFixAvg * 100)}%`;

    if (valSoil) valSoil.textContent = topPick.soilHealth.toFixed(2);
    if (valWater) valWater.textContent = topPick.waterSafety.toFixed(2);
    if (valRes) valRes.textContent = topPick.resilience.toFixed(2);
    if (valYield) valYield.textContent = topPick.yieldPotential.toFixed(2);
    if (valNFix) valNFix.textContent = topPick.nFixAvg.toFixed(2);

    const scoreOutOf100 = Math.round(Number(topPick.totalScore.toFixed(2)) * 100);
    if (avgScoreBadge) avgScoreBadge.textContent = `${scoreOutOf100} / 100`;
  }

  // Ranked alternatives table (RANK, ROTATION, TOTAL SCORE) + 4 small quick analyses for the other 4 crop rotations
  const topFive = ranked.slice(0, 5);
  const activeRankIdx = topFive[appState.selectedRankIndex] ? appState.selectedRankIndex : 0;
  const tbody = document.getElementById('ranked-alternatives-tbody');
  if (tbody) {
    tbody.innerHTML = '';
    topFive.forEach((item, idx) => {
      const tr = document.createElement('tr');
      tr.className = `ranked-row ${idx === activeRankIdx ? 'selected-rank-row' : ''}`;
      const rankNum = String(idx + 1).padStart(2, '0');
      tr.innerHTML = `
        <td class="col-rank">${rankNum}</td>
        <td class="col-rotation">
          <div class="ranked-seq-title">${item.label}</div>
        </td>
        <td class="col-score">${item.totalScore.toFixed(2)}</td>
      `;
      tr.addEventListener('click', () => {
        appState.selectedRankIndex = idx;
        renderDashboard();
      });
      tbody.appendChild(tr);
    });
  }

  // Top banner quick analysis for the active rotation + 4 small quick analyses at the bottom for the other 4 rotations
  const bannerSeqText = document.getElementById('banner-sequence-analysis-text');
  if (topPick && bannerSeqText) {
    bannerSeqText.textContent = `Generated sequence ${topPick.label} scores ${topPick.totalScore.toFixed(2)} at (${field.lat.toFixed(2)}°, ${field.lon.toFixed(2)}°) with ${annualRain} mm rainfall, ${field.moistureAvg.toFixed(2)} RZM root-zone moisture, ${field.soilTempC.toFixed(1)}°C soil temperature, and OC ${field.oc.toFixed(1)}% · pH ${field.ph.toFixed(1)} (soil health ${topPick.soilHealth.toFixed(2)}, water safety ${topPick.waterSafety.toFixed(2)}, yield ${topPick.yieldPotential.toFixed(2)}).`;
  }

  const altAnalysisBox = document.getElementById('sequence-quick-analysis-box');
  if (altAnalysisBox) {
    altAnalysisBox.className = 'sequence-quick-analysis-grid';
    altAnalysisBox.innerHTML = '';
    const otherFour = topFive
      .map((item, idx) => ({ item, idx }))
      .filter((entry) => entry.idx !== activeRankIdx)
      .slice(0, 4);

    otherFour.forEach(({ item, idx }, cardPos) => {
      const rankNum = String(idx + 1).padStart(2, '0');
      const card = document.createElement('div');
      card.className = 'alt-quick-analysis-card';
      const defaultAltText = buildAlternativeQuickAnalysis(item, cardPos + 1, field, annualRain);
      card.innerHTML = `
        <div class="alt-quick-analysis-header">
          <div class="alt-quick-analysis-title-group">
            <span class="quick-analysis-title alt-quick-analysis-title">Quick analysis · Rank #${rankNum}</span>
            <span class="gemini-attribution-tag sequence-gemini-tag" style="display: none;">
              <svg class="gemini-sparkle-icon" viewBox="0 0 24 24" width="12" height="12" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M12 0C12 6.627 6.627 12 0 12C6.627 12 12 17.373 12 24C12 17.373 17.373 12 24 12C17.373 12 12 6.627 12 0Z" fill="#9B72CB"/>
              </svg>
              <span>Generated by Gemini</span>
            </span>
          </div>
          <span class="alt-quick-analysis-score">Score ${item.totalScore.toFixed(2)}</span>
        </div>
        <div class="alt-quick-analysis-seq">${item.label}</div>
        <p id="ranked-row-analysis-${idx}" class="sequence-analysis-text alt-quick-analysis-text">${defaultAltText}</p>
      `;
      card.addEventListener('click', () => {
        appState.selectedRankIndex = idx;
        renderDashboard();
      });
      altAnalysisBox.appendChild(card);
    });
  }

  // Tab 2: Render field borders on the map and update meta text
  renderMapFieldBorders();
  const mapSelectedMeta = document.getElementById('map-selected-field-meta');
  const mapRotationMeta = document.getElementById('map-rotation-preview-meta');
  if (mapSelectedMeta) {
    mapSelectedMeta.textContent = `Selected field: ${activeFieldCode} (1 of ${appState.fieldCount} fields) • Previous crop(s): ${prevSummaryText} • Soil ${field.mapSoilScore.toFixed(2)} · Moisture ${field.mapMoisture.toFixed(2)}`;
  }
  if (mapRotationMeta && topPick) {
    mapRotationMeta.textContent = `Rotation preview: ${topPick.label}`;
  }

  // Tab 2: Crop water demand bars
  const rainSub = document.getElementById('crop-water-rain-sub');
  if (rainSub) rainSub.textContent = `Annual rainfall: ${annualRain} mm`;
  const demandCrops = [
    { id: 'c05', water: 380 },
    { id: 'c03', water: 420 },
    { id: 'c11', water: 480 },
    { id: 'c02', water: 550 },
    { id: 'c01', water: 580 }
  ];
  demandCrops.forEach((dc) => {
    const barEl = document.getElementById(`water-bar-${dc.id}`);
    if (barEl) {
      const exceeds = dc.water > annualRain || dc.water > appState.maxWaterDemand;
      barEl.classList.toggle('exceeds-rain', exceeds);
    }
  });

  // Tab 2: 5-year dual-axis temperature & rainfall line chart
  renderClimateLineChart(field);

  // Tab 3: Live sensor readings & MMS Mobile Measuring Station decision (Wet or Dry)
  const nasaRzm = document.getElementById('sensor-nasa-rzm');
  const nasaTemp = document.getElementById('sensor-nasa-temp');
  const nasaPrecip = document.getElementById('sensor-nasa-precip');
  const devRzm = document.getElementById('sensor-dev-rzm');
  const devSt = document.getElementById('sensor-dev-st');
  const devAh = document.getElementById('sensor-dev-ah');
  const devRain = document.getElementById('sensor-dev-rain');
  const alertTitle = document.getElementById('sensor-alert-title');
  const alertSub = document.getElementById('sensor-alert-sub');
  const backendHeading = document.getElementById('moisture-backend-heading');
  const backendLine1 = document.getElementById('moisture-backend-line-1');
  const backendLine2 = document.getElementById('moisture-backend-line-2');

  const liveMms = isMmsLive() ? appState.mms.latest : null;

  if (nasaRzm) nasaRzm.textContent = `${field.moistureAvg.toFixed(2)} m³/m³`;
  if (nasaTemp) nasaTemp.textContent = `${field.tempSummer.toFixed(1)} °C`;
  if (nasaPrecip) nasaPrecip.textContent = `${field.summer2024Precip} mm`;

  if (!appState.sensorEnabled) {
    if (devRzm) devRzm.textContent = 'Disabled (satellite only)';
    if (devSt) devSt.textContent = `${field.soilTempC.toFixed(1)} °C (satellite)`;
    if (devAh) devAh.textContent = 'Disabled in sidebar';
    if (devRain) devRain.textContent = 'Disabled in sidebar';
    if (alertTitle) {
      alertTitle.textContent = 'MMS Mobile Measuring Station: Disabled in sidebar — using NASA satellite baseline only';
    }
    if (alertSub) {
      alertSub.textContent =
        'Local sensor readings are currently turned off in the sidebar. Toggle "Local sensor readings" on in the sidebar or click Wet / Dry below to activate MMS ground-truth calibration.';
    }
    if (backendHeading) {
      backendHeading.textContent = `Backend report for ${activeFieldName} · Satellite Baseline Only (MMS Disabled)`;
    }
    if (backendLine1) {
      backendLine1.textContent = `Local MMS sensor override is disabled. Rotations are scored using NASA POWER root-zone moisture (${field.moistureAvg.toFixed(2)} m³/m³) and ${field.summer2024Precip} mm summer precipitation without local probe adjustments.`;
    }
    if (backendLine2) {
      backendLine2.textContent = `Click "MMS Mobile Measuring Station: Wet" or "MMS Mobile Measuring Station: Dry" above (or enable the sidebar toggle) to apply local soil moisture readings to ${topPick ? topPick.label : 'your rotation'}.`;
    }
  } else if (appState.probeMode === 'dry') {
    const localMoist = liveMms && liveMms.soil_moisture_m3 != null ? liveMms.soil_moisture_m3 : Math.max(0.14, field.moistureAvg - 0.13);
    if (devRzm) devRzm.textContent = `${localMoist.toFixed(2)} m³/m³ (Dry)`;
    if (devSt) devSt.textContent = `${(liveMms && liveMms.soil_temp_c != null ? liveMms.soil_temp_c : field.soilTempC + 2.3).toFixed(1)} °C`;
    if (devAh) devAh.textContent = liveMms && liveMms.air_humidity_pct != null ? `${Math.round(liveMms.air_humidity_pct)} % RH` : '38 % RH';
    if (alertTitle) alertTitle.textContent = 'MMS Mobile Measuring Station: Dry soil selected — rotation adjusted';
    if (alertSub) {
      alertSub.textContent =
        'Backend response: Root-zone moisture is below the NASA satellite baseline. Prioritizing drought-tolerant legumes and lower water demand.';
    }
    if (backendHeading) backendHeading.textContent = `Backend report for ${activeFieldName} · MMS Mobile Measuring Station: DRY`;
    if (backendLine1) {
      backendLine1.textContent = `Your MMS Mobile Measuring Station indicates dry topsoil (${localMoist.toFixed(2)} m³/m³ vs NASA ${field.moistureAvg.toFixed(2)} m³/m³). Backend advises reducing tillage, scheduling supplemental irrigation if available, and leading with nitrogen-fixing legumes that tolerate dry spells.`;
    }
    if (backendLine2) {
      backendLine2.textContent = `Backend recommended rotation for Dry soil: ${topPick ? topPick.label : 'Soybeans or Small Grains → Beets, Carrots, Squash or Pumpkins → Hay or Alfalfa (Haylage)'}.`;
    }
  } else {
    const localMoist = liveMms && liveMms.soil_moisture_m3 != null ? liveMms.soil_moisture_m3 : Math.min(0.49, field.moistureAvg + 0.06);
    if (devRzm) devRzm.textContent = `${localMoist.toFixed(2)} m³/m³ (Wet)`;
    if (devSt) devSt.textContent = `${(liveMms && liveMms.soil_temp_c != null ? liveMms.soil_temp_c : field.soilTempC).toFixed(1)} °C`;
    if (devAh) devAh.textContent = liveMms && liveMms.air_humidity_pct != null ? `${Math.round(liveMms.air_humidity_pct)} % RH` : '68 % RH';
    if (alertTitle) alertTitle.textContent = 'MMS Mobile Measuring Station: Wet soil selected — full water budget available';
    if (alertSub) {
      alertSub.textContent = `Backend response: Root-zone moisture is well-supplied (${localMoist.toFixed(2)} m³/m³). High-yield crops and deep-rooted forages are supported.`;
    }
    if (backendHeading) backendHeading.textContent = `Backend report for ${activeFieldName} · MMS Mobile Measuring Station: WET`;
    if (backendLine1) {
      backendLine1.textContent = `Your MMS Mobile Measuring Station confirms wet root-zone conditions (${localMoist.toFixed(2)} m³/m³ vs NASA ${field.moistureAvg.toFixed(2)} m³/m³). Backend advises monitoring field drainage to prevent root compaction and taking advantage of strong moisture reserves for high-biomass crops.`;
    }
    if (backendLine2) {
      backendLine2.textContent = `Backend recommended rotation for Wet soil: ${topPick ? topPick.label : 'Soybeans or Small Grains → Field Corn (Silage or Grain) → Hay or Alfalfa (Haylage)'}.`;
    }
  }

  if (appState.sensorEnabled && devRain) {
    devRain.textContent = liveMms
      ? (liveMms.is_raining ? `Raining (${liveMms.rain_intensity_pct}%)` : 'Dry')
      : 'No MMS data';
  }
  if (appState.sensorEnabled && liveMms && alertTitle) {
    alertTitle.textContent = `MMS Mobile Measuring Station: ${appState.probeMode === 'dry' ? 'Dry' : 'Wet'} soil detected — live telemetry`;
  }

  document.querySelectorAll('.probe-mode-btn').forEach((btn) => {
    btn.classList.toggle('active-probe-mode', Boolean(appState.sensorEnabled && btn.dataset.probe === appState.probeMode));
  });
}

function renderAll() {
  document.querySelectorAll('.profile-choice-btn').forEach((btn) => {
    btn.classList.toggle('selected-profile-btn', btn.dataset.profile === appState.selectedProfile);
  });
  renderDashboard();
}

// Wire up event listeners when DOM loads
document.addEventListener('DOMContentLoaded', () => {
  selectCityLocation(appState.selectedCity);
  // Global click closes open dropdowns
  document.addEventListener('click', () => {
    closeAllDropdowns();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeAllDropdowns();
      const modal = document.getElementById('data-sources-modal');
      if (modal) modal.classList.remove('open');
    }
  });

  // Hero Login/Sign-up button scrolls smoothly to the login section below
  const heroLoginBtn = document.getElementById('hero-login-scroll-btn');
  if (heroLoginBtn) {
    heroLoginBtn.addEventListener('click', () => {
      const loginSection = document.getElementById('login-section');
      if (loginSection) loginSection.scrollIntoView({ behavior: 'smooth' });
    });
  }

  // Continue button on lower landing credits section -> transitions to Screen 2: Select your location
  const loginContinueBtn = document.getElementById('login-continue-btn');
  if (loginContinueBtn) {
    loginContinueBtn.addEventListener('click', () => {
      navigateToView('location-view');
    });
  }

  // Step 1 map city pins
  document.querySelectorAll('.city-pin').forEach((pin) => {
    pin.addEventListener('click', () => {
      selectCityLocation(pin.dataset.city);
    });
  });

  // Step 1 search box: address lookup lives in maps.js (Google geocoder, OpenStreetMap fallback)

  // Step 1 map zoom controls
  const zoomInBtn = document.getElementById('map-zoom-in');
  const zoomOutBtn = document.getElementById('map-zoom-out');
  const schematicSvg = document.getElementById('schematic-map-svg');
  if (zoomInBtn && schematicSvg) {
    zoomInBtn.addEventListener('click', () => {
      appState.mapZoom = clip(appState.mapZoom + 0.15, 0.85, 1.6);
      schematicSvg.style.transform = `scale(${appState.mapZoom})`;
    });
  }
  if (zoomOutBtn && schematicSvg) {
    zoomOutBtn.addEventListener('click', () => {
      appState.mapZoom = clip(appState.mapZoom - 0.15, 0.85, 1.6);
      schematicSvg.style.transform = `scale(${appState.mapZoom})`;
    });
  }

  // Step 1 Change Region dropdown
  const step1Trig = document.getElementById('step1-dropdown-trigger');
  if (step1Trig) {
    step1Trig.addEventListener('click', (e) => {
      toggleDropdown('step1-dropdown-menu', 'step1-dropdown-trigger', e);
    });
  }

  document.querySelectorAll('.region-dropdown-item').forEach((item) => {
    item.addEventListener('click', (e) => {
      e.stopPropagation();
      const cityKey = item.dataset.city;
      const fieldKey = item.dataset.field;
      if (cityKey) {
        selectCityLocation(cityKey);
      } else if (fieldKey && FIELDS_DATA[fieldKey]) {
        appState.selectedFieldId = fieldKey;
        const numFromId = parseInt(fieldKey.replace(/\D/g, ''), 10) || 1;
        if (numFromId > appState.fieldCount) {
          appState.fieldCount = numFromId;
        }
        appState.selectedFieldNumber = numFromId;
        const f = FIELDS_DATA[fieldKey];
        const regionBox = document.getElementById('step1-region-selected');
        const latLonBox = document.getElementById('step1-latlon-display');
        const latInput = document.getElementById('step1-lat-input');
        const lonInput = document.getElementById('step1-lon-input');
        const triggerText = document.getElementById('step1-dropdown-label');
        if (regionBox) regionBox.textContent = `${f.name} (${f.regionLabel})`;
        if (latLonBox) latLonBox.textContent = `${f.lat.toFixed(4)}, ${f.lon.toFixed(4)}`;
        if (latInput) latInput.value = f.lat;
        if (lonInput) lonInput.value = f.lon;
        if (triggerText) triggerText.textContent = f.name;
      }
      closeAllDropdowns();
    });
  });

  // Step 1 Confirm region button -> transitions to Screen 3: Choose a priority profile
  const confirmRegionBtn = document.getElementById('confirm-region-btn');
  if (confirmRegionBtn) {
    confirmRegionBtn.addEventListener('click', () => {
      navigateToView('profile-view');
    });
  }

  // Step 2 Priority profile choice buttons -> select profile and transition to Dashboard
  document.querySelectorAll('.profile-choice-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      appState.selectedProfile = btn.dataset.profile;
      appState.selectedRankIndex = 0;
      navigateToView('dashboard-view');
    });
  });

  // Dashboard sidebar dropdown 1: Previous crop planted (single-select)
  const prevCropTrigger = document.getElementById('sidebar-prev-crop-trigger');
  if (prevCropTrigger) {
    prevCropTrigger.addEventListener('click', (e) => {
      toggleDropdown('sidebar-prev-crop-menu', 'sidebar-prev-crop-trigger', e);
    });
  }

  document.querySelectorAll('[data-prev-crop-option]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      appState.previousCropId = btn.dataset.prevCropOption;
      appState.selectedRankIndex = 0;
      closeAllDropdowns();
      renderDashboard();
    });
  });

  // Tab 2: Field count input, active field selector, and border drawing on the map
  const mapFieldCountInput = document.getElementById('map-field-count-input');
  if (mapFieldCountInput) {
    mapFieldCountInput.addEventListener('input', (e) => {
      const parsed = parseInt(e.target.value, 10);
      if (!Number.isNaN(parsed) && parsed >= 1) {
        setFieldCount(parsed);
        appState.selectedRankIndex = 0;
        renderDashboard();
      }
    });
    mapFieldCountInput.addEventListener('change', (e) => {
      const parsed = parseInt(e.target.value, 10) || 1;
      setFieldCount(parsed);
      mapFieldCountInput.value = String(appState.fieldCount);
      appState.selectedRankIndex = 0;
      renderDashboard();
    });
  }

  const mapActiveFieldSelect = document.getElementById('map-active-field-select');
  if (mapActiveFieldSelect) {
    mapActiveFieldSelect.addEventListener('change', (e) => {
      const num = parseInt(e.target.value, 10) || 1;
      appState.selectedFieldNumber = num;
      appState.selectedFieldId = getFieldIdForNumber(num);
      appState.selectedRankIndex = 0;
      renderDashboard();
    });
  }

  const mapDrawModeBtn = document.getElementById('map-draw-mode-btn');
  if (mapDrawModeBtn) {
    mapDrawModeBtn.addEventListener('click', () => {
      appState.drawBorderMode = !appState.drawBorderMode;
      renderMapFieldBorders();
    });
  }

  const mapResetGridBtn = document.getElementById('map-reset-grid-btn');
  if (mapResetGridBtn) {
    mapResetGridBtn.addEventListener('click', () => {
      appState.customFieldBorders = {};
      appState.drawBorderMode = false;
      renderMapFieldBorders();
    });
  }

  // Click and drag on #satellite-map-canvas to draw a custom square/rectangle border for the active field
  const mapCanvas = document.getElementById('satellite-map-canvas');
  if (mapCanvas) {
    let isDraggingBorder = false;
    let startX = 0;
    let startY = 0;

    mapCanvas.addEventListener('mousedown', (e) => {
      if (!appState.drawBorderMode) return;
      const rect = mapCanvas.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      isDraggingBorder = true;
      startX = clip(((e.clientX - rect.left) / rect.width) * 100, 0, 96);
      startY = clip(((e.clientY - rect.top) / rect.height) * 100, 0, 96);
      appState.customFieldBorders[appState.selectedFieldNumber] = {
        left: Number(startX.toFixed(2)),
        top: Number(startY.toFixed(2)),
        width: 8,
        height: 10
      };
      renderMapFieldBorders();
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDraggingBorder || !appState.drawBorderMode) return;
      const rect = mapCanvas.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      const curX = clip(((e.clientX - rect.left) / rect.width) * 100, 0, 100);
      const curY = clip(((e.clientY - rect.top) / rect.height) * 100, 0, 100);
      const left = Math.min(startX, curX);
      const top = Math.min(startY, curY);
      const width = Math.max(5, Math.abs(curX - startX));
      const height = Math.max(6, Math.abs(curY - startY));
      appState.customFieldBorders[appState.selectedFieldNumber] = {
        left: Number(left.toFixed(2)),
        top: Number(top.toFixed(2)),
        width: Number(Math.min(100 - left, width).toFixed(2)),
        height: Number(Math.min(100 - top, height).toFixed(2))
      };
      renderMapFieldBorders();
    });

    window.addEventListener('mouseup', () => {
      if (!isDraggingBorder) return;
      isDraggingBorder = false;
      appState.drawBorderMode = false;
      renderMapFieldBorders();
    });
  }

  // Dashboard sidebar dropdown 2: Priority profile
  const profileTrigger = document.getElementById('sidebar-profile-trigger');
  if (profileTrigger) {
    profileTrigger.addEventListener('click', (e) => {
      toggleDropdown('sidebar-profile-menu', 'sidebar-profile-trigger', e);
    });
  }

  document.querySelectorAll('[data-profile-option]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      appState.selectedProfile = btn.dataset.profileOption;
      appState.selectedRankIndex = 0;
      closeAllDropdowns();
      renderDashboard();
    });
  });

  // Dashboard sidebar dropdown 3: Crops (multi-select)
  const equipTrigger = document.getElementById('sidebar-equip-trigger');
  const equipMenu = document.getElementById('sidebar-equip-menu');
  if (equipTrigger) {
    equipTrigger.addEventListener('click', (e) => {
      toggleDropdown('sidebar-equip-menu', 'sidebar-equip-trigger', e);
    });
  }
  if (equipMenu) {
    equipMenu.addEventListener('click', (e) => {
      e.stopPropagation();
    });
  }

  document.querySelectorAll('[data-crop-option]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const cid = btn.dataset.cropOption;
      const idx = appState.selectedCrops.indexOf(cid);
      if (idx >= 0) {
        appState.selectedCrops.splice(idx, 1);
      } else {
        appState.selectedCrops.push(cid);
      }
      appState.selectedRankIndex = 0;
      renderDashboard();
    });
  });

  const cropsClearBtn = document.getElementById('crops-clear-btn');
  if (cropsClearBtn) {
    cropsClearBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      appState.selectedCrops = [];
      appState.selectedRankIndex = 0;
      renderDashboard();
    });
  }

  const cropsDoneBtn = document.getElementById('crops-done-btn');
  if (cropsDoneBtn) {
    cropsDoneBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      closeAllDropdowns();
    });
  }

  // Priority profile intensity sliders (1-100) on both onboarding and dashboard sidebar
  const handleIntensityInput = (e) => {
    appState.profileIntensity = clip(parseInt(e.target.value, 10) || 1, 1, 100);
    appState.selectedRankIndex = 0;
    renderDashboard();
  };
  const sidebarIntensitySlider = document.getElementById('profile-intensity-slider');
  if (sidebarIntensitySlider) {
    sidebarIntensitySlider.addEventListener('input', handleIntensityInput);
  }
  const onboardingIntensitySlider = document.getElementById('onboarding-intensity-slider');
  if (onboardingIntensitySlider) {
    onboardingIntensitySlider.addEventListener('input', handleIntensityInput);
  }

  // Dashboard sidebar Max water demand slider
  const waterSlider = document.getElementById('water-demand-slider');
  if (waterSlider) {
    waterSlider.addEventListener('input', (e) => {
      appState.maxWaterDemand = parseInt(e.target.value, 10);
      appState.selectedRankIndex = 0;
      renderDashboard();
    });
  }

  // Dashboard sidebar Local sensor readings toggle
  const sensorSwitch = document.getElementById('sidebar-sensor-switch');
  if (sensorSwitch) {
    sensorSwitch.addEventListener('click', () => {
      appState.sensorEnabled = !appState.sensorEnabled;
      if (isMmsLive() && appState.mms.latest && appState.mms.latest.probe_mode) {
        appState.probeMode = appState.mms.latest.probe_mode;
      }
      renderDashboard();
    });
  }

  // Dashboard 3 tabs
  document.querySelectorAll('.dash-tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      switchDashboardTab(btn.dataset.tab);
    });
  });

  // Tab 2 clickable field hotspots on the satellite map
  document.querySelectorAll('.field-hotspot').forEach((spot) => {
    spot.addEventListener('click', () => {
      const fid = spot.dataset.field;
      const numFromId = parseInt(fid.replace(/\D/g, ''), 10) || 1;
      if (numFromId > appState.fieldCount) {
        appState.fieldCount = numFromId;
      }
      appState.selectedFieldNumber = numFromId;
      appState.selectedFieldId = fid;
      appState.selectedRankIndex = 0;
      renderDashboard();
    });
  });

  // Tab 3 MMS Mobile Measuring Station Wet / Dry decision buttons
  document.querySelectorAll('.probe-mode-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      // Automatically enable local sensor readings in the sidebar if the user clicks Wet or Dry
      if (!appState.sensorEnabled) {
        appState.sensorEnabled = true;
      }
      // While the MMS is live, the sensor decides Wet or Dry
      if (!isMmsLive()) {
        appState.probeMode = btn.dataset.probe;
      }
      renderDashboard();
    });
  });

  // Top nav Demo & Data sources links, Back buttons, and brand home links
  document.querySelectorAll('[data-nav-target]').forEach((el) => {
    el.addEventListener('click', () => {
      navigateToView(el.dataset.navTarget);
    });
  });

  // Browser Back / Forward navigation across onboarding steps
  window.addEventListener('popstate', (e) => {
    const stateView = e.state && e.state.viewId;
    const hashView = window.location.hash ? window.location.hash.replace('#', '') : 'landing-view';
    const targetView = stateView || hashView || 'landing-view';
    if (document.getElementById(targetView)) {
      navigateToView(targetView, false);
    }
  });

  document.querySelectorAll('.open-sources-modal-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const modal = document.getElementById('data-sources-modal');
      if (modal) modal.classList.add('open');
    });
  });

  const closeModalBtn = document.getElementById('close-sources-modal-btn');
  if (closeModalBtn) {
    closeModalBtn.addEventListener('click', () => {
      const modal = document.getElementById('data-sources-modal');
      if (modal) modal.classList.remove('open');
    });
  }

  // Initialize first view
  renderAll();

  // Allow direct view navigation via URL parameter or hash
  const urlParams = new URLSearchParams(window.location.search);
  const initialView = urlParams.get('view') || (window.location.hash ? window.location.hash.replace('#', '') : null);
  if (initialView && document.getElementById(initialView)) {
    navigateToView(initialView);
  }

  // Start polling Mobile Measurement Station (MMS) telemetry
  pollMms();
  setInterval(pollMms, 2000);
});
