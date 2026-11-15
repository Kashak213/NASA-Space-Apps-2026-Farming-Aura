// Client-side state, rotation scoring engine, and UI interactions for Farming Aura

const FIELDS_DATA = {
  F001: {
    id: 'F001',
    name: 'Field F001',
    regionLabel: 'Albany, New York',
    lat: 41.5,
    lon: -93.6,
    oc: 2.8,
    ph: 6.5,
    clay: 28.0,
    sand: 42.0,
    bd: 1.35,
    cec: 22.5,
    spring2023Precip: 340,
    summer2023Precip: 280,
    spring2024Precip: 310,
    summer2024Precip: 220,
    drought2023: 0.16,
    drought2024: 0.265,
    moistureAvg: 0.35,
    ndvi2023: 0.725,
    ndvi2024: 0.685,
    tempSummer: 24.8,
    soilTempC: 18.6,
    anom2023: 3.3,
    anom2024: -13.35,
    mapStatus: 'Healthy',
    mapSoilScore: 0.76,
    mapMoisture: 0.42
  },
  F002: {
    id: 'F002',
    name: 'Field F002',
    regionLabel: 'Saratoga Springs, New York',
    lat: 41.7,
    lon: -93.4,
    oc: 1.9,
    ph: 7.1,
    clay: 35.0,
    sand: 30.0,
    bd: 1.45,
    cec: 18.2,
    spring2023Precip: 320,
    summer2023Precip: 260,
    spring2024Precip: 290,
    summer2024Precip: 195,
    drought2023: 0.24,
    drought2024: 0.365,
    moistureAvg: 0.27,
    ndvi2023: 0.685,
    ndvi2024: 0.63,
    tempSummer: 25.1,
    soilTempC: 19.4,
    anom2023: -3.15,
    anom2024: -21.0,
    mapStatus: 'Moderate stress',
    mapSoilScore: 0.64,
    mapMoisture: 0.24
  },
  F003: {
    id: 'F003',
    name: 'Field F003',
    regionLabel: 'Schenectady, New York',
    lat: 40.8,
    lon: -95.2,
    oc: 3.2,
    ph: 6.2,
    clay: 22.0,
    sand: 55.0,
    bd: 1.25,
    cec: 26.8,
    spring2023Precip: 340,
    summer2023Precip: 295,
    spring2024Precip: 350,
    summer2024Precip: 310,
    drought2023: 0.15,
    drought2024: 0.13,
    moistureAvg: 0.41,
    ndvi2023: 0.765,
    ndvi2024: 0.78,
    tempSummer: 25.5,
    soilTempC: 18.9,
    anom2023: 6.15,
    anom2024: 10.3,
    mapStatus: 'Healthy',
    mapSoilScore: 0.82,
    mapMoisture: 0.51
  },
  F004: {
    id: 'F004',
    name: 'Field F004',
    regionLabel: 'Troy, New York',
    lat: 42.1,
    lon: -92.8,
    oc: 2.1,
    ph: 7.4,
    clay: 40.0,
    sand: 25.0,
    bd: 1.5,
    cec: 15.6,
    spring2023Precip: 310,
    summer2023Precip: 240,
    spring2024Precip: 275,
    summer2024Precip: 180,
    drought2023: 0.3,
    drought2024: 0.435,
    moistureAvg: 0.24,
    ndvi2023: 0.64,
    ndvi2024: 0.57,
    tempSummer: 25.8,
    soilTempC: 20.2,
    anom2023: -8.45,
    anom2024: -25.3,
    mapStatus: 'High drought risk',
    mapSoilScore: 0.58,
    mapMoisture: 0.19
  },
  F005: {
    id: 'F005',
    name: 'Field F005',
    regionLabel: 'Hudson, New York',
    lat: 41.3,
    lon: -94.1,
    oc: 3.8,
    ph: 5.9,
    clay: 18.0,
    sand: 62.0,
    bd: 1.2,
    cec: 31.2,
    spring2023Precip: 360,
    summer2023Precip: 310,
    spring2024Precip: 380,
    summer2024Precip: 330,
    drought2023: 0.115,
    drought2024: 0.085,
    moistureAvg: 0.46,
    ndvi2023: 0.815,
    ndvi2024: 0.835,
    tempSummer: 26.0,
    soilTempC: 19.1,
    anom2023: 11.6,
    anom2024: 18.35,
    mapStatus: 'Moderate stress',
    mapSoilScore: 0.71,
    mapMoisture: 0.36
  },
  F006: {
    id: 'F006',
    name: 'Field F006',
    regionLabel: 'Albany, New York',
    lat: 40.5,
    lon: -96.0,
    oc: 1.5,
    ph: 7.8,
    clay: 45.0,
    sand: 20.0,
    bd: 1.55,
    cec: 12.4,
    spring2023Precip: 280,
    summer2023Precip: 210,
    spring2024Precip: 250,
    summer2024Precip: 165,
    drought2023: 0.425,
    drought2024: 0.52,
    moistureAvg: 0.21,
    ndvi2023: 0.59,
    ndvi2024: 0.53,
    tempSummer: 26.2,
    soilTempC: 21.0,
    anom2023: -18.8,
    anom2024: -31.85,
    mapStatus: 'Healthy',
    mapSoilScore: 0.88,
    mapMoisture: 0.57
  },
  F007: {
    id: 'F007',
    name: 'Field F007',
    regionLabel: 'Saratoga Springs, New York',
    lat: 42.5,
    lon: -91.5,
    oc: 4.2,
    ph: 6.0,
    clay: 20.0,
    sand: 58.0,
    bd: 1.18,
    cec: 35.1,
    spring2023Precip: 385,
    summer2023Precip: 340,
    spring2024Precip: 400,
    summer2024Precip: 360,
    drought2023: 0.075,
    drought2024: 0.055,
    moistureAvg: 0.51,
    ndvi2023: 0.86,
    ndvi2024: 0.875,
    tempSummer: 26.5,
    soilTempC: 18.2,
    anom2023: 20.95,
    anom2024: 26.9,
    mapStatus: 'Moderate stress',
    mapSoilScore: 0.69,
    mapMoisture: 0.28
  },
  F008: {
    id: 'F008',
    name: 'Field F008',
    regionLabel: 'Hudson, New York',
    lat: 41.0,
    lon: -94.8,
    oc: 2.5,
    ph: 6.8,
    clay: 32.0,
    sand: 38.0,
    bd: 1.38,
    cec: 20.3,
    spring2023Precip: 320,
    summer2023Precip: 255,
    spring2024Precip: 295,
    summer2024Precip: 210,
    drought2023: 0.265,
    drought2024: 0.35,
    moistureAvg: 0.31,
    ndvi2023: 0.685,
    ndvi2024: 0.635,
    tempSummer: 25.0,
    soilTempC: 19.0,
    anom2023: -4.4,
    anom2024: -16.75,
    mapStatus: 'Healthy',
    mapSoilScore: 0.79,
    mapMoisture: 0.45
  }
};

const CITY_LOCATIONS = {
  Albany: {
    cityKey: 'Albany',
    label: 'Albany, New York',
    displayCoords: '27.00101, 280.1',
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
  C01: { id: 'C01', name: 'Corn', type: 'grain', roleTag: 'Grain • yield potential', water: 550, nFix: 0.0, droughtTol: 0.3, phMin: 5.8, phMax: 7.0, clayMin: 20, clayMax: 40, yieldT: 10.5, rootM: 1.2, build: 0.2 },
  C02: { id: 'C02', name: 'Soybean', type: 'legume', roleTag: 'Legume • nitrogen fixation', water: 450, nFix: 0.8, droughtTol: 0.5, phMin: 6.0, phMax: 7.0, clayMin: 20, clayMax: 45, yieldT: 3.4, rootM: 1.5, build: 0.9 },
  C03: { id: 'C03', name: 'Winter Wheat', type: 'grain', roleTag: 'Grain • winter cover & yield', water: 350, nFix: 0.0, droughtTol: 0.7, phMin: 5.5, phMax: 7.5, clayMin: 15, clayMax: 45, yieldT: 5.2, rootM: 1.0, build: 0.4 },
  C04: { id: 'C04', name: 'Oats', type: 'grain', roleTag: 'Grain • fast spring nurse crop', water: 400, nFix: 0.0, droughtTol: 0.5, phMin: 5.5, phMax: 7.0, clayMin: 15, clayMax: 40, yieldT: 3.8, rootM: 0.8, build: 0.3 },
  C05: { id: 'C05', name: 'Alfalfa', type: 'legume', roleTag: 'Forage legume • deep roots', water: 600, nFix: 0.9, droughtTol: 0.4, phMin: 6.5, phMax: 7.5, clayMin: 20, clayMax: 40, yieldT: 9.0, rootM: 3.0, build: 1.0 },
  C06: { id: 'C06', name: 'Cover crop mix', type: 'cover', roleTag: 'Soil building', water: 200, nFix: 0.6, droughtTol: 0.8, phMin: 5.0, phMax: 8.0, clayMin: 10, clayMax: 50, yieldT: 0.0, rootM: 0.5, build: 1.0 },
  C07: { id: 'C07', name: 'Sorghum', type: 'grain', roleTag: 'Grain • drought tolerant', water: 300, nFix: 0.0, droughtTol: 0.9, phMin: 5.5, phMax: 7.5, clayMin: 15, clayMax: 45, yieldT: 5.0, rootM: 1.5, build: 0.3 },
  C08: { id: 'C08', name: 'Sunflower', type: 'oilseed', roleTag: 'Oilseed • deep taproot', water: 350, nFix: 0.0, droughtTol: 0.8, phMin: 6.0, phMax: 7.5, clayMin: 15, clayMax: 40, yieldT: 2.2, rootM: 1.8, build: 0.2 },
  C10: { id: 'C10', name: 'Field Pea', type: 'legume', roleTag: 'Legume • low water N-fixer', water: 350, nFix: 0.7, droughtTol: 0.6, phMin: 6.0, phMax: 7.5, clayMin: 20, clayMax: 40, yieldT: 3.0, rootM: 1.0, build: 0.8 },
  C11: { id: 'C11', name: 'Rye', type: 'cover', roleTag: 'Cover • erosion & moisture guard', water: 180, nFix: 0.0, droughtTol: 0.9, phMin: 4.5, phMax: 8.0, clayMin: 10, clayMax: 50, yieldT: 0.0, rootM: 0.8, build: 0.9 },
  C12: { id: 'C12', name: 'Clover', type: 'legume', roleTag: 'Legume • organic nitrogen builder', water: 280, nFix: 0.85, droughtTol: 0.6, phMin: 6.0, phMax: 7.0, clayMin: 15, clayMax: 45, yieldT: 0.0, rootM: 0.6, build: 0.95 }
};

const CANDIDATE_SEQUENCES = [
  ['C02', 'C06', 'C01'], // Soybean -> Cover crop mix -> Corn
  ['C07', 'C02', 'C11'], // Sorghum -> Soybean -> Rye
  ['C01', 'C02', 'C06'], // Corn -> Soybean -> Cover crop mix
  ['C01', 'C02', 'C03'], // Corn -> Soybean -> Winter Wheat
  ['C12', 'C01', 'C02'], // Clover -> Corn -> Soybean
  ['C10', 'C01', 'C03'], // Field Pea -> Corn -> Winter Wheat
  ['C07', 'C10', 'C01'], // Sorghum -> Field Pea -> Corn
  ['C08', 'C02', 'C07'], // Sunflower -> Soybean -> Sorghum
  ['C05', 'C01', 'C02']  // Alfalfa -> Corn -> Soybean (requires all crop types equipment)
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
  selectedFieldId: 'F001',
  selectedProfile: 'Balanced',
  selectedEquipment: 'Row-crop only',
  maxWaterDemand: 550,
  sensorEnabled: true,
  probeMode: 'dry', // 'template' | 'wet' | 'dry'
  mapZoom: 1.0,
  selectedRankIndex: 0
};

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

  const w = PRIORITY_PROFILES[profileName] || PRIORITY_PROFILES.Balanced;
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

function getRankedRotations() {
  const field = FIELDS_DATA[appState.selectedFieldId] || FIELDS_DATA.F001;
  const rowOnly = appState.selectedEquipment === 'Row-crop only';
  const maxWater = appState.maxWaterDemand;
  const dryProbeActive = appState.sensorEnabled && appState.probeMode === 'dry' && appState.activeTab === 'sensors';

  let filtered = CANDIDATE_SEQUENCES.filter((seq) => {
    if (rowOnly && seq.includes('C05')) return false;
    const withinWater = seq.every((cid) => CROPS_DATA[cid].water <= maxWater);
    return withinWater;
  });

  if (filtered.length < 3) {
    filtered = CANDIDATE_SEQUENCES.filter((seq) => !rowOnly || !seq.includes('C05'));
  }

  const scored = filtered.map((seq) => scoreSequenceForField(seq, field, appState.selectedProfile, dryProbeActive));

  scored.sort((a, b) => {
    if (Math.abs(b.totalScore - a.totalScore) > 0.0001) return b.totalScore - a.totalScore;
    if (Math.abs(b.waterSafety - a.waterSafety) > 0.0001) return b.waterSafety - a.waterSafety;
    return b.nFixAvg - a.nFixAvg;
  });

  return scored;
}

// Switch between top-level views with smooth fade transitions
function navigateToView(viewId) {
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
    });
  });

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
        });
      });
    }
  });

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

// Update the Dashboard UI with current field, profile, equipment, water slider, and sensor state
function renderDashboard() {
  const field = FIELDS_DATA[appState.selectedFieldId] || FIELDS_DATA.F001;
  const ranked = getRankedRotations();
  const topPick = ranked[appState.selectedRankIndex] || ranked[0];

  // Sidebar trigger labels
  const fieldTrigLabel = document.getElementById('sidebar-field-label');
  const profileTrigLabel = document.getElementById('sidebar-profile-label');
  const equipTrigLabel = document.getElementById('sidebar-equip-label');
  if (fieldTrigLabel) fieldTrigLabel.textContent = field.name;
  if (profileTrigLabel) profileTrigLabel.textContent = appState.selectedProfile;
  if (equipTrigLabel) equipTrigLabel.textContent = appState.selectedEquipment;

  // Highlight active items inside sidebar dropdowns
  document.querySelectorAll('.field-option-btn').forEach((btn) => {
    btn.classList.toggle('selected-field', btn.dataset.field === field.id);
  });
  document.querySelectorAll('[data-profile-option]').forEach((btn) => {
    btn.classList.toggle('active-option', btn.dataset.profileOption === appState.selectedProfile);
  });
  document.querySelectorAll('[data-equip-option]').forEach((btn) => {
    btn.classList.toggle('active-option', btn.dataset.equipOption === appState.selectedEquipment);
  });

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
    sensorStatus.textContent = appState.sensorEnabled ? 'Enabled · demo' : 'Disabled · satellite only';
  }

  // Header eyebrow, title, and subtitles
  const dashEyebrow = document.getElementById('dash-eyebrow-text');
  const dashMainTitle = document.getElementById('dash-main-title');
  const dashSubLeft = document.getElementById('dash-subtitle-left');
  const dashSubRight = document.getElementById('dash-subtitle-right');
  if (dashEyebrow) dashEyebrow.textContent = `FIELD ${field.id} / DEMO DATA`;
  if (dashMainTitle) dashMainTitle.textContent = field.name;
  if (dashSubLeft) dashSubLeft.textContent = `Demo data • ${appState.selectedProfile} priority profile`;
  if (dashSubRight) {
    dashSubRight.textContent =
      appState.selectedEquipment === 'Row-crop only'
        ? 'Equipment constraint: row crops only'
        : 'Equipment constraint: all crop types';
  }

  // Top 4 KPI cards
  const annualRain = Math.round(field.spring2024Precip + field.summer2024Precip);
  const kpiSoilVal = document.getElementById('kpi-soil-val');
  const kpiSoilSub = document.getElementById('kpi-soil-sub');
  const kpiRainVal = document.getElementById('kpi-rain-val');
  const kpiMoistureVal = document.getElementById('kpi-moisture-val');
  const kpiTempVal = document.getElementById('kpi-temp-val');

  if (kpiSoilVal) kpiSoilVal.textContent = `${topPick.soilHealth.toFixed(2)} SH`;
  if (kpiSoilSub) kpiSoilSub.textContent = `OC ${field.oc.toFixed(1)}% · pH ${field.ph.toFixed(1)}`;
  if (kpiRainVal) kpiRainVal.textContent = `${annualRain} mm`;
  if (kpiMoistureVal) kpiMoistureVal.textContent = `${field.moistureAvg.toFixed(2)} RZM`;
  if (kpiTempVal) kpiTempVal.textContent = `${field.soilTempC.toFixed(1)}°C`;

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

  // Why this rotation won
  const whyLine1 = document.getElementById('why-won-line-1');
  const whyLine2 = document.getElementById('why-won-line-2');
  if (whyLine1 && whyLine2 && topPick) {
    const hasLegume = topPick.crops.some((c) => c.nFix >= 0.5);
    const hasCover = topPick.crops.some((c) => c.type === 'cover');
    whyLine1.textContent = hasLegume
      ? 'Legume rotation supports soil nitrogen via root nodules before grain crops.'
      : 'Alternating crop families breaks pest cycles and balances root depth.';
    whyLine2.textContent = hasCover
      ? 'Cover crops protect topsoil between seasons and hold organic carbon.'
      : `Matches ${appState.selectedProfile.toLowerCase()} goals within your ${appState.maxWaterDemand} mm water budget.`;
  }

  // Rotation score breakdown bars
  const barSoil = document.getElementById('bar-soil-health');
  const barWater = document.getElementById('bar-water-safety');
  const barRes = document.getElementById('bar-resilience');
  const barYield = document.getElementById('bar-yield-potential');
  if (barSoil && topPick) barSoil.style.width = `${Math.round(topPick.soilHealth * 100)}%`;
  if (barWater && topPick) barWater.style.width = `${Math.round(topPick.waterSafety * 100)}%`;
  if (barRes && topPick) barRes.style.width = `${Math.round(topPick.resilience * 100)}%`;
  if (barYield && topPick) barYield.style.width = `${Math.round(topPick.yieldPotential * 100)}%`;

  // Ranked alternatives table
  const tbody = document.getElementById('ranked-alternatives-tbody');
  if (tbody) {
    tbody.innerHTML = '';
    ranked.slice(0, 5).forEach((item, idx) => {
      const tr = document.createElement('tr');
      tr.className = `ranked-row ${idx === appState.selectedRankIndex ? 'selected-rank-row' : ''}`;
      const rankNum = String(idx + 1).padStart(2, '0');
      tr.innerHTML = `
        <td>${rankNum}</td>
        <td>${item.label}</td>
        <td>${item.totalScore.toFixed(2)}</td>
        <td>${item.waterSafety.toFixed(2)}</td>
      `;
      tr.addEventListener('click', () => {
        appState.selectedRankIndex = idx;
        renderDashboard();
      });
      tbody.appendChild(tr);
    });
  }

  // Tab 2: Field health map hotspots & meta text
  document.querySelectorAll('.field-hotspot').forEach((spot) => {
    spot.classList.toggle('active-hotspot', spot.dataset.field === field.id);
  });
  const mapSelectedMeta = document.getElementById('map-selected-field-meta');
  const mapRotationMeta = document.getElementById('map-rotation-preview-meta');
  if (mapSelectedMeta) {
    mapSelectedMeta.textContent = `Selected field: ${field.id} • simulated field readings (Soil ${field.mapSoilScore.toFixed(2)} · Moisture ${field.mapMoisture.toFixed(2)})`;
  }
  if (mapRotationMeta && topPick) {
    mapRotationMeta.textContent = `Rotation preview: ${topPick.label}`;
  }

  // Tab 2: Crop water demand bars
  const rainSub = document.getElementById('crop-water-rain-sub');
  if (rainSub) rainSub.textContent = `Annual rainfall: ${annualRain} mm`;
  const demandCrops = [
    { name: 'Rye', water: 180 },
    { name: 'Sorghum', water: 300 },
    { name: 'Soybean', water: 450 },
    { name: 'Corn', water: 550 },
    { name: 'Alfalfa', water: 600 }
  ];
  demandCrops.forEach((dc) => {
    const barEl = document.getElementById(`water-bar-${dc.name.toLowerCase()}`);
    if (barEl) {
      const exceeds = dc.water > annualRain || dc.water > appState.maxWaterDemand;
      barEl.classList.toggle('exceeds-rain', exceeds);
    }
  });

  // Tab 2: Seasonal shifts 2023 vs 2024 bars
  const barsData = [
    { id: 'season-bar-0', h: Math.round((field.spring2023Precip / 420) * 120), tip: `2023 Spring Precip: ${field.spring2023Precip} mm` },
    { id: 'season-bar-1', h: Math.round((field.spring2024Precip / 420) * 135), tip: `2024 Spring Precip: ${field.spring2024Precip} mm` },
    { id: 'season-bar-2', h: Math.round((field.summer2023Precip / 420) * 125), tip: `2023 Summer Precip: ${field.summer2023Precip} mm` },
    { id: 'season-bar-3', h: Math.round((field.summer2024Precip / 420) * 100), tip: `2024 Summer Precip: ${field.summer2024Precip} mm` },
    { id: 'season-bar-4', h: Math.round(field.ndvi2023 * 120), tip: `2023 Spring NDVI: ${field.ndvi2023.toFixed(2)}` },
    { id: 'season-bar-5', h: Math.round(field.ndvi2024 * 100), tip: `2024 Spring NDVI: ${field.ndvi2024.toFixed(2)}` },
    { id: 'season-bar-6', h: Math.round((1 - field.drought2023) * 108), tip: `2023 Moisture Index: ${(1 - field.drought2023).toFixed(2)}` },
    { id: 'season-bar-7', h: Math.round((1 - field.drought2024) * 86), tip: `2024 Moisture Index: ${(1 - field.drought2024).toFixed(2)}` }
  ];
  barsData.forEach((b) => {
    const el = document.getElementById(b.id);
    if (el) {
      el.style.height = `${clip(b.h, 36, 138)}px`;
      el.title = b.tip;
    }
  });

  // Tab 3: Live sensor readings
  const nasaRzm = document.getElementById('sensor-nasa-rzm');
  const nasaTemp = document.getElementById('sensor-nasa-temp');
  const nasaPrecip = document.getElementById('sensor-nasa-precip');
  const devRzm = document.getElementById('sensor-dev-rzm');
  const devSt = document.getElementById('sensor-dev-st');
  const devAh = document.getElementById('sensor-dev-ah');
  const alertTitle = document.getElementById('sensor-alert-title');
  const alertSub = document.getElementById('sensor-alert-sub');

  if (appState.probeMode === 'template') {
    if (nasaRzm) nasaRzm.textContent = 'NASA_RZM';
    if (nasaTemp) nasaTemp.textContent = 'NASA_TEMP';
    if (nasaPrecip) nasaPrecip.textContent = 'NASA_PRECIP';
    if (devRzm) devRzm.textContent = 'DEV_RZM';
    if (devSt) devSt.textContent = 'DEV_ST';
    if (devAh) devAh.textContent = 'DEV_AH';
    if (alertTitle) alertTitle.textContent = 'Dry soil detected — rotation adjusted';
    if (alertSub) alertSub.textContent = 'Demo: consider Sorghum → Soybean for water resilience.';
  } else if (appState.probeMode === 'dry') {
    const localMoist = Math.max(0.14, field.moistureAvg - 0.13);
    if (nasaRzm) nasaRzm.textContent = `${field.moistureAvg.toFixed(2)} m³/m³`;
    if (nasaTemp) nasaTemp.textContent = `${field.tempSummer.toFixed(1)} °C`;
    if (nasaPrecip) nasaPrecip.textContent = `${field.summer2024Precip} mm`;
    if (devRzm) devRzm.textContent = `${localMoist.toFixed(2)} m³/m³ (Dry)`;
    if (devSt) devSt.textContent = `${(field.soilTempC + 2.3).toFixed(1)} °C`;
    if (devAh) devAh.textContent = '38 % RH';
    if (alertTitle) alertTitle.textContent = 'Dry soil detected — rotation adjusted';
    if (alertSub) alertSub.textContent = 'Demo: consider Sorghum → Soybean for water resilience.';
  } else {
    const localMoist = Math.min(0.49, field.moistureAvg + 0.06);
    if (nasaRzm) nasaRzm.textContent = `${field.moistureAvg.toFixed(2)} m³/m³`;
    if (nasaTemp) nasaTemp.textContent = `${field.tempSummer.toFixed(1)} °C`;
    if (nasaPrecip) nasaPrecip.textContent = `${field.summer2024Precip} mm`;
    if (devRzm) devRzm.textContent = `${localMoist.toFixed(2)} m³/m³ (Optimal)`;
    if (devSt) devSt.textContent = `${field.soilTempC.toFixed(1)} °C`;
    if (devAh) devAh.textContent = '64 % RH';
    if (alertTitle) alertTitle.textContent = 'Soil moisture optimal — satellite estimate confirmed';
    if (alertSub) alertSub.textContent = `Recommended rotation for ${field.id}: ${topPick ? topPick.label : 'Soybean → Cover crop mix → Corn'}.`;
  }

  document.querySelectorAll('.probe-mode-btn').forEach((btn) => {
    btn.classList.toggle('active-probe-mode', btn.dataset.probe === appState.probeMode);
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

  // Login form submission -> transitions to Screen 2: Select your location
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', (e) => {
      e.preventDefault();
      navigateToView('location-view');
    });
  }

  // Step 1 map city pins
  document.querySelectorAll('.city-pin').forEach((pin) => {
    pin.addEventListener('click', () => {
      selectCityLocation(pin.dataset.city);
    });
  });

  // Step 1 search input filters cities on the map
  const mapSearch = document.getElementById('step1-map-search');
  if (mapSearch) {
    mapSearch.addEventListener('input', (e) => {
      const q = e.target.value.trim().toLowerCase();
      if (!q) return;
      const matchKey = Object.keys(CITY_LOCATIONS).find((k) => k.toLowerCase().includes(q));
      if (matchKey) selectCityLocation(matchKey);
    });
  }

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

  // Dashboard sidebar dropdown 1: Field
  const fieldTrigger = document.getElementById('sidebar-field-trigger');
  if (fieldTrigger) {
    fieldTrigger.addEventListener('click', (e) => {
      toggleDropdown('sidebar-field-menu', 'sidebar-field-trigger', e);
    });
  }

  document.querySelectorAll('.field-option-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      appState.selectedFieldId = btn.dataset.field;
      appState.selectedRankIndex = 0;
      closeAllDropdowns();
      renderDashboard();
    });
  });

  const customMapBtn = document.getElementById('field-custom-map-btn');
  if (customMapBtn) {
    customMapBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      closeAllDropdowns();
      navigateToView('location-view');
    });
  }

  const fieldCloseBtn = document.getElementById('field-menu-close-btn');
  if (fieldCloseBtn) {
    fieldCloseBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      closeAllDropdowns();
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

  // Dashboard sidebar dropdown 3: Equipment
  const equipTrigger = document.getElementById('sidebar-equip-trigger');
  if (equipTrigger) {
    equipTrigger.addEventListener('click', (e) => {
      toggleDropdown('sidebar-equip-menu', 'sidebar-equip-trigger', e);
    });
  }

  document.querySelectorAll('[data-equip-option]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      appState.selectedEquipment = btn.dataset.equipOption;
      appState.selectedRankIndex = 0;
      closeAllDropdowns();
      renderDashboard();
    });
  });

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
      appState.selectedFieldId = spot.dataset.field;
      appState.selectedRankIndex = 0;
      renderDashboard();
    });
  });

  // Tab 3 capacitive probe simulator mode buttons
  document.querySelectorAll('.probe-mode-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      appState.probeMode = btn.dataset.probe;
      renderDashboard();
    });
  });

  // Top nav Demo & Data sources links and brand home links
  document.querySelectorAll('[data-nav-target]').forEach((el) => {
    el.addEventListener('click', () => {
      navigateToView(el.dataset.navTarget);
    });
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
});
