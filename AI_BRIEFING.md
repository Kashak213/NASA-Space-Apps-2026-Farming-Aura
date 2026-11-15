# AI Assistant Briefing & Project Context (`AI_BRIEFING.md`)

> **Instructions for AI Assistants (Claude Code, Cursor, Antigravity, Copilot, etc.):**  
> Read this file first to get full context on our project, architecture, rules compliance, writing style, and current state when switching between laptop/desktop environments or across team members.

---

## 1. Project Overview
- **Event:** NASA Space Apps Challenge 2026 (Nov 14–15, 2026)
- **Team Repo:** `nasa space apps project teamfarming aura`
- **Challenge:** *"Field Shift: Adapting Farms with NASA Data"*
- **Objective:** Build a decision-support tool that combines NASA Earth observations (SMAP, MODIS, GPM, NASA POWER), local soil metrics (SoilGrids/USDA SSURGO), crop characteristics, and optional local hardware sensor inputs from our **Mobile Measurement Station (MMS)** to recommend optimal crop rotation strategies tailored to farmer priorities.

---

## 2. Tone, Voice & Writing Style Guidelines (IMPORTANT FOR ALL AGENTS)
- **Target Voice for Code Comments, READMEs, and UI Text:**
  - Write like smart, capable high school students who have taken AP Biology, AP Environmental Science, and AP Computer Science, and spent about a month before the competition researching NASA datasets and crop rotation basics.
  - Do **not** sound like an AI assistant or a PhD agronomist. Use grounded biology/env-sci concepts (e.g., nitrogen fixation via legume root nodules, organic carbon, soil compaction and root depth, transpiration and drought stress, pest cycles when repeating crops) rather than academic jargon ("autotoxicity", "pedological horizonation", "canonical deduplication", "synergistic paradigm").
- **Strict Anti-AI Formatting Rules for Comments & Docs (excluding `AI_BRIEFING.md`):**
  - **Minimize or eliminate emojis** in code, terminal output, and markdown docs.
  - **Never use semicolons (`;`)** in prose, READMEs, or code comments. Break sentences with periods, commas, or conjunctions instead.
  - **No bulleted or numbered lists inside code docstrings/comments.** Keep docstrings as short, plain-English sentences.
  - **Avoid common AI tells and vocabulary:** Do not use words like *delve, comprehensive, crucial, moreover, furthermore, utilize, leverage, holistic, synergy, paradigm, multifaceted, seamlessly, robust, overarching, underscore*. Avoid overusing em-dashes (`—`) or decorative Unicode box-drawing borders (`─────`) in comments.
  - **Difference between Comments and READMEs:**
    - **Code comments:** Casual, practical, and easy to skim. Explain what each block of code, math formula, or API step is doing and why so that any human teammate reading the file understands it right away without confusion, while keeping the code clean and readable.
    - **READMEs:** Same authentic student background, but slightly more technical, structured, and concise than code comments so it is clear we put real time and care into documenting our work.
- **Hardware Naming Rule (CRITICAL):** Always refer to the physical sensor hardware unit as the **Mobile Measurement Station (MMS)** (or **MMS** for short). **Never** call it "Elegoo Uno", "Elegoo", or "Arduino" in UI text, documentation, presentation materials, comments, or API payloads.
- **Exception for `AI_BRIEFING.md`:**
  - Keep `AI_BRIEFING.md` as technical, dense, and precise as needed. Do not dumb down `AI_BRIEFING.md` so that AI agents transferring work between computers or sessions retain full comprehension and save context tokens.

---

## 3. NASA Space Apps Compliance & Hackathon Status
- **Current Phase:** **LIVE HACKATHON BUILD (Nov 14–15, 2026 — Hackathon Officially Started).**
- **Status & Scope:** All pre-hackathon restrictions on building `src/`, live NASA API ingestion pipelines, the Streamlit UI, and hardware sensor integration are now lifted. Full production development is active.
- **Submission Window:** Opens Saturday, Nov 14 at 9:00 AM and closes Sunday, Nov 15 at 11:59 PM (local time).
- **Mandatory Citations (for final submission):**
  - Pre-hackathon prototype disclosure: Disclose `data/sample_data_test.py` and `data/sample/*.csv` as pre-hackathon algorithm validation on synthetic data.
  - Open-source Python libraries (`pandas`, `numpy`, `scikit-learn`, `streamlit`, `plotly`, `folium`, `earthaccess`, `geopandas`, `rasterio`, `xarray`, `requests`, `scipy`, `pydantic`)
  - NASA Datasets: SMAP (Soil Moisture), MODIS (NDVI/EVI), GPM (Precipitation), NASA POWER (Agroclimatology)
  - Soil/Ag Datasets: ISRIC SoilGrids, USDA NASS / SSURGO
  - AI Coding Assistants: Google Antigravity / Anthropic Claude Code

---

## 4. Core Architecture & Decisions Made
1. **Frontend / UI & Hosting (`GitHub Pages` + `src/ui/`):**
   - **Primary Web Deployment Target:** **GitHub Pages** (static HTML/CSS/JS or static SPA build) for public web hosting, paired with pre-computed/live JSON endpoints or optional Streamlit dashboard (`src/ui/`).
   - **Interactive Map Stack (Zero-Key Default + Optional Google Maps):**
     - **Default (No API Key Required):** **Leaflet.js** in the browser (or `folium` in Python) using **Esri World Imagery** satellite tiles, **OpenStreetMap** base tiles, and **NASA GIBS WMTS** satellite overlays (MODIS NDVI, SMAP Soil Moisture).
     - **Optional Google Maps Integration:** Supported via `GOOGLE_MAPS_API_KEY` loaded from `.env` / `src/config.py` locally, or injected at build time via GitHub Actions Secrets and locked down with Google Cloud HTTP Referrer restrictions (see Section 7 for exact Frontend AI instructions).
   - **Judge-Friendly Onboarding & No Auth Gate:** Never add a login/sign-up wall (violates NASA Space Apps public-access rules). If using an onboarding/walkthrough flow (farm location, farm/harvest goals, main crops), **always include a 1-step "Skip / Load Sample Farm" button** (and pre-filled defaults/clickable chips) so judges can jump straight into the live dashboard in one click.
   - **No Frontend Code Built Yet:** The frontend team is building the UI separately using Section 7 of this briefing as their AI context handoff.
2. **Backend / Recommendation Engine:**
   - Multi-criteria weighted scoring & sequence transition formula that ranks candidate multi-year crop rotation sequences:
     ```
     rotation_score = penalty_multiplier * (
         w1 * soil_health_score      +  # Field OC%, pH, BD, CEC, sand/clay + crop soil_building & root_depth relief
         w2 * water_stress_score     +  # Field water supply & drought trend vs. crop demand & annual precip
         w3 * climate_resilience     +  # Precip anomaly, NDVI, 2023->2024 trend & summer heat + crop_type diversity
         w4 * nitrogen_fixation      +  # Legume/cover N-fixation + N carry-over bonus to following grain crop
         w5 * yield_potential        +  # Normalized crop yield potential
         w6 * drought_tolerance      +  # Crop drought tolerance rating
         w7 * soil_compatibility        # Crop optimal pH/clay match + consecutive root-depth alternation
     )
     ```
   - **5 Preset Farmer Priority Profiles (`PROFILES` in `src/backend/scoring.py`):**
     - `Balanced`: `soil_health=0.20, water_stress=0.20, climate_res=0.15, nitrogen_fix=0.15, yield=0.15, drought_tol=0.10, soil_compat=0.05`
     - `Max Yield`: `soil_health=0.10, water_stress=0.15, climate_res=0.10, nitrogen_fix=0.10, yield=0.40, drought_tol=0.10, soil_compat=0.05`
     - `Water Conservation`: `soil_health=0.10, water_stress=0.35, climate_res=0.15, nitrogen_fix=0.10, yield=0.10, drought_tol=0.15, soil_compat=0.05`
     - `Soil Health First`: `soil_health=0.30, water_stress=0.10, climate_res=0.10, nitrogen_fix=0.25, yield=0.10, drought_tol=0.10, soil_compat=0.05`
     - `Climate Resilient`: `soil_health=0.15, water_stress=0.20, climate_res=0.25, nitrogen_fix=0.10, yield=0.10, drought_tol=0.15, soil_compat=0.05`
   - **Sequence Transition & Constraint Engine:**
     - Cyclic transition analysis (`sequence_transition_analysis`) penalizes back-to-back and wrap-around monoculture repeats (`seq[i] == seq[(i+1)%n]`) and consecutive same-family (`crop_type`) transitions, while rewarding legume-to-grain nitrogen carry-over and root-depth alternation.
     - Equipment/feasibility filtering (`filter_rotations_by_constraints`) and algorithmic N-year sequence generation (`generate_candidate_rotations`).
   - **Multi-key Sorting Strategy:**
     1. Primary: `total_score` (Descending)
     2. Secondary: `water_stress` (Descending — breaks ties in favor of drought resilience)
     3. Tertiary: `nitrogen_fixation` (Descending — breaks ties in favor of soil-building legumes)
3. **Mobile Measurement Station (MMS) Hardware Integration (Bonus Differentiator):**
   - Decoupled **Mobile Measurement Station (MMS)** 4-sensor field unit reading localized capacitive soil moisture (`A0`), waterproof soil temperature (`D2`), ambient air temperature & relative humidity (`D3`), and surface rain detection (`A1`) over USB Serial (`9600` baud JSON stream) / HTTP as a ground-truth safety layer compared against satellite forecasts. Always display and refer to this unit as **Mobile Measurement Station (MMS)** (never "Elegoo Uno" or "Arduino").

---

## 5. Current Repository Structure
```text
.
├── AI_BRIEFING.md                 # This context file for seamless multi-machine AI handoff
├── .env.example                   # Template for local API keys (copy to .env locally; never commit .env)
├── requirements.txt               # Target Python dependencies for the hackathon build
├── beta_algorithm_testing/        # Dedicated folder for pre-hackathon beta algorithm tests
│   └── README.md                  # Explains the beta testing scope, mock datasets, and findings
├── data/
│   ├── sample_data_test.py        # Zero-dependency (stdlib) test runner for scoring & sorting (single copy; includes 10 assertion checks)
│   └── sample/
│       ├── mock_soil.csv          # 8 sample fields with OC%, pH, clay%, sand%, bulk density, CEC
│       ├── mock_climate.csv       # Seasonal temp, precip, drought index, soil moisture, NDVI (2023-2024)
│       └── mock_crops.csv         # 12 crops (grains, legumes, oilseeds, covers) & traits
├── notebooks/                     # Data exploration & API prototyping
└── src/                           # Active hackathon production build (Nov 14-15)
    ├── config.py                  # Secret & API key loader (.env, env vars, Streamlit secrets, with Leaflet fallback)
    ├── backend/                   # Python FastAPI backend & NASA POWER integration
    │   ├── main.py                # FastAPI routes (/analyze, CORS setup)
    │   ├── nasa_client.py         # NASA POWER API client (ALLSKY_SFC_SW_DWN, WS2M, PRECTOTCORR, T2M) + -999 stripping & offline cache
    │   ├── scoring.py             # Crop suitability, 5 preset priority profiles, 7 weights & wind/sunlight sub-scores
    │   ├── crops.py               # Crop catalog loader, lookup helpers, constraint filtering & N-year rotation generator
    │   ├── requirements.txt       # Backend dependencies (fastapi, uvicorn, requests)
    │   └── data/                  # Static & cached JSON files
    │       ├── ny_regions.json    # Static NY soil texture, pH & coordinates lookup
    │       ├── crops.json         # 12 farm crops (grains, legumes, oilseeds, covers) & agronomic thresholds
    │       └── nasa_cache/        # Saved NASA POWER JSONs for offline demo backup
    ├── pipeline/                  # Live NASA POWER, SMAP, MODIS, GPM, and SoilGrids data fetchers
    ├── engine/                    # Production crop rotation scoring, transition penalties, and ML ranking
    └── ui/                        # Frontend UI / dashboard (to be built by Frontend Team)
```

---

## 6. Next Steps / Active Hackathon Build Roadmap (Nov 14–15)
- **To run the baseline algorithm validation suite:**
  ```bash
  python data/sample_data_test.py
  ```
  Exits non-zero with an `AssertionError` if any check in Test 5 fails.
- **To test the NASA POWER API client (`src/backend/nasa_client.py`):**
  ```bash
  python src/backend/nasa_client.py
  ```
  Fetches `ALLSKY_SFC_SW_DWN` (All Sky Surface Shortwave Downward Irradiance), `WS2M` (Wind Speed at 2 Meters), `PRECTOTCORR` (Precipitation Corrected), and `T2M` (Temperature at 2 Meters) from NASA POWER (`community=AG`), strips `-999` fill values and `YYYY13` annual summary keys, caches raw responses in `src/backend/data/nasa_cache/`, and returns cleaned series plus a summary dictionary.

### Change Log
- **Nov 14, 2026 — Maps & Secret Hygiene Setup + Frontend AI Handoff (Google Antigravity):**
  - Updated `.gitignore` to block `.env.*`, `.streamlit/secrets.toml`, `*.pem`, and `*.key` while allowing `.env.example`.
  - Added `.env.example` and `src/config.py` (`get_secret`, `get_google_maps_api_key`) for safe key loading across local dev and deployment.
  - Added Section 7 below with dedicated instructions for the Frontend Team's AI assistants on building the interactive map for **GitHub Pages** (Leaflet + Esri/NASA GIBS zero-key stack vs. domain-restricted Google Maps JS API).
- **Nov 14, 2026 — Crop Catalog & Rotation Generator in `src/backend/crops.py` (Google Antigravity):**
  - Added `src/backend/crops.py` and populated `src/backend/data/crops.json` with all 12 crops (`C01`–`C12`: grains, legumes, oilseeds, and cover crops).
  - Implemented `load_crops()`, `get_crop_by_id()`, `get_crop_by_name()`, `resolve_sequence_crops()`, `filter_rotations_by_constraints()`, and `generate_candidate_rotations()` with step-by-step plain-English comments.
- **Nov 14, 2026 — 5 Preset Priority Profiles, Wind & Sunlight Sub-Score Integration & Inline Comments in `src/backend/scoring.py` (Google Antigravity):**
  - Implemented `src/backend/scoring.py` with `PROFILES` (`Balanced`, `Max Yield`, `Water Conservation`, `Soil Health First`, `Climate Resilient`), each mapping the 7 factor weights (`soil_health`, `water_stress`, `climate_res`, `nitrogen_fix`, `yield`, `drought_tol`, `soil_compat`) to sum to `1.00`.
  - Integrated NASA POWER 2m wind speed (`WS2M` / `ws2m_avg_m_s`) into `wind_stress_score()`, `soil_health_score()` (sandy topsoil wind erosion risk), `field_water_supply_score()` & `water_stress_score()` (wind-driven evaporation and leaf transpiration bump), and `climate_resilience_score()` (stalk lodging penalty and crop wind buffer).
  - Integrated NASA POWER shortwave solar irradiance (`ALLSKY_SFC_SW_DWN` / `allsky_sfc_sw_dwn_avg`, in `MJ/m^2/day`) into `sunlight_suitability_score()`, `yield_potential_score()` (photosynthesis multiplier), `field_water_supply_score()` & `water_stress_score()` (solar evaporation and leaf heating bump when irradiance exceeds `18.0 MJ/m^2/day`), and `climate_resilience_score()`.
  - Added the 7 sub-score functions, `sequence_transition_analysis()`, `score_rotation()`, `sort_rotations()`, and `compare_profiles_for_rotation()` with step-by-step plain-English comments explaining every block of code.
- **Nov 14, 2026 — NASA POWER Client & Backend Structure (Google Antigravity):**
  - Created `src/backend/` structure (`main.py`, `nasa_client.py`, `scoring.py`, `requirements.txt`, `data/ny_regions.json`, `data/crops.json`, `data/nasa_cache/`).
  - Implemented `src/backend/nasa_client.py` connecting to NASA POWER (`daily` and `monthly` Agroclimatology endpoints) for `ALLSKY_SFC_SW_DWN`, `WS2M`, `PRECTOTCORR`, and `T2M` with `-999` fill-value stripping, `urllib`/`requests` support, and automatic JSON caching in `src/backend/data/nasa_cache/`.
  - Added clear step-by-step inline comments across `src/backend/nasa_client.py` (and updated Section 2 comment guidelines) so teammates can follow every function and API step without confusion.
- **Nov 14, 2026 — Official Hackathon Kickoff (Google Antigravity):**
  - Updated project status from Pre-Hackathon Preparation to **LIVE HACKATHON BUILD**.
  - Lifted pre-hackathon guardrails on `src/`, live NASA API ingestion, Streamlit UI, and hardware sensor integration.
- **Oct 25, 2026 — Data analysis, sequence modeling & style guidelines (Google Antigravity):**
  - **Added Temporal & Seasonal Climate Analysis:** `get_field_climate_agg` now computes seasonal splits (`spring_precip_mm`, `summer_precip_mm`, `annual_precip_mm`, `summer_temp_c`, `summer_drought`) and year-over-year climate trends (`2023 → 2024` `drought_trend`, `precip_anom_trend`, `ndvi_trend`).
  - **Made Soil Health & Climate Resilience Rotation-Responsive:** `soil_health_score` now integrates `sand_pct`, `soil_building_score`, and `root_depth_m` compaction relief; `climate_resilience_score` integrates 2023→2024 precip trends, summer heat stress, and functional `crop_type` diversity. Both now differentiate rotations on the same field as well as ranking fields.
  - **Added Sequence Transition & Order Engine (`sequence_transition_analysis`):** Penalizes back-to-back and cycle wrap-around crop repeats (`Alfalfa → Corn → Alfalfa` no longer dominates `Balanced` or `Soil Health First`), rewards N carry-over from legumes to subsequent non-fixing crops, rewards root-depth alternation, and differentiates sequence starting order (`Soy → Cover → Corn` vs. `Corn → Soy → Cover`).
  - **Added Equipment Constraints & Algorithmic Sequence Generator:** Added `filter_rotations_by_constraints` (e.g., `row_crop_only=True` to exclude forage hay `C05`) and `generate_candidate_rotations` (combinatorial N-year sequence generator with agronomic pruning).
  - **Added Tone/Style Guidelines & Cleaned Comments/README:** Added Section 2 in `AI_BRIEFING.md` specifying the AP Bio/EnvSci high-school student voice, no semicolons, minimal emojis, and no AI-cliché phrasing across code comments and READMEs (while keeping `AI_BRIEFING.md` technical for agent handoffs).
- **Oct 23, 2026 — Review & fixes (Claude Code):**
  - **Fixed:** `water_stress` was field-level only; updated to combine field water supply with each crop's `water_demand_mm`.
  - **Added:** initial assertion checks (Test 5) and removed duplicate `beta_algorithm_testing/sample_data_test.py`.

### Active Hackathon Build Priorities (Nov 14–15)
1. **Phase 1 — Live Data Ingestion (`src/pipeline/`):**
   - Build NASA POWER REST API client (fetch daily/seasonal temperature, precipitation, and solar radiation by `lat`/`lon`).
   - Build SoilGrids REST API client (or fallback local soil lookup) for OC%, pH, clay%, sand%, bulk density, and CEC.
   - Integrate SMAP soil moisture and MODIS NDVI layers (via `earthaccess` / AppEEARS or cached regional rasters/CSVs for instant UI responsiveness).
2. **Phase 2 — Production Scoring Engine (`src/engine/`):**
   - Port and modularize the validated scoring, constraint filtering, and cyclic transition engine from `data/sample_data_test.py` into `src/engine/`.
   - Add ground-truth **Mobile Measurement Station (MMS)** sensor delta adjustments (allowing local MMS soil temperature, soil moisture, air temperature/humidity, and rain readings to override/adjust satellite anomaly scores when connected, with automatic fallback to NASA/USDA data when the MMS is unplugged).
3. **Phase 3 — Interactive Web UI & Map (`GitHub Pages` / `src/ui/`):**
   - Optional walkthrough/onboarding (farm location, farm/harvest goals, main crops) with **no login wall** and a **1-step "Skip / Load Sample Farm" button** so judges can bypass setup in one click.
   - Interactive map selector (Leaflet.js + Esri Satellite/NASA GIBS or Google Maps JS API, or `folium` in Streamlit) to pick a farm location or sample field.
   - Farmer priority weight sliders (`Balanced`, `Max Yield`, `Water Conservation`, `Soil Health First`, `Climate Resilient`, plus custom sliders) and equipment constraint toggles (`row_crop_only`).
   - Ranked crop rotation cards with multi-year sequence breakdown, component score radar/bar charts, and historical climate/NDVI trend visualizations.
4. **Phase 4 — Verification, Demo Video & Submission:**
   - Verify end-to-end flow with live coordinates and fallback offline mode.
   - Compile complete citations list for the Space Apps submission form.

---

## 7. Frontend Team AI Instructions (Maps, GitHub Pages, & API Key Security)

> **Instructions for Frontend Team AI Assistants:**  
> We are deploying the public web frontend on **GitHub Pages** (static hosting). Follow these rules and specifications when building the interactive map and UI so our API keys never leak and our map works both locally and in production. Also remember to follow **Section 2 (Tone, Voice & Writing Style Guidelines)** in all frontend code comments and UI copy.

### 7.1 Crucial Constraint of GitHub Pages
- GitHub Pages only serves static files (`HTML`, `CSS`, `JS`, `JSON`). It cannot run a Python server directly.
- Any API key embedded in client-side JS/HTML is visible in browser DevTools (`Network` / `Elements`).
- Therefore:
  1. **Never commit raw API keys to the git repo.** Keep local keys in `.env` (already ignored by `.gitignore`, template in `.env.example`).
  2. **Default to our Zero-Key Leaflet Satellite stack** unless a specific Google Maps feature is required, or support both seamlessly.

### 7.2 Primary Map Stack (Zero API Key — Recommended for GitHub Pages)
Use **Leaflet.js** (`https://unpkg.com/leaflet@1.9.4/dist/leaflet.js`) with a layer switcher combining free satellite, street, and NASA Earth observation tiles:

1. **Satellite Base Layer (Esri World Imagery — No API Key Required):**
   - Tile URL: `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`
   - Attribution: `Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community`
2. **Street / Reference Base Layer (OpenStreetMap — No API Key Required):**
   - Tile URL: `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`
   - Attribution: `&copy; OpenStreetMap contributors`
3. **NASA GIBS Satellite Overlays (WMTS — No API Key Required):**
   - Base template: `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/{layer}/default/{date}/{tileMatrixSet}/{z}/{y}/{x}.{format}`
   - Useful agriculture layers:
     - **MODIS Terra NDVI (8-Day):** `MODIS_Terra_NDVI_8Day` (`tileMatrixSet`: `GoogleMapsCompatible_Level9`, `format`: `png`)
     - **SMAP L4 Root Zone Soil Moisture:** `SMAP_L4_Analyzed_Root_Zone_Soil_Moisture` (`tileMatrixSet`: `GoogleMapsCompatible_Level6`, `format`: `png`)

### 7.3 Optional Google Maps JS API Integration (How to Keep Keys Safe)
If the frontend team builds a Google Maps view (`Maps JavaScript API`) or uses Google Places Autocomplete:
1. **Local Development:**
   - Copy `.env.example` to `.env` and set `GOOGLE_MAPS_API_KEY=...`.
   - For Python scripts/backends, import `get_google_maps_api_key()` from `src/config.py` (returns `None` if unconfigured so the app can automatically fall back to Leaflet).
   - For Vite/React/static JS builds, read `import.meta.env.VITE_GOOGLE_MAPS_API_KEY` (or `process.env.GOOGLE_MAPS_API_KEY`) from `.env` and automatically fall back to the Leaflet map if the key is missing or set to the placeholder string.
2. **GitHub Pages Deployment (GitHub Actions Injection):**
   - Store the real key in **GitHub Repository Settings → Secrets and variables → Actions → `GOOGLE_MAPS_API_KEY`**.
   - During the GitHub Pages build workflow (`.github/workflows/deploy.yml`), pass `GOOGLE_MAPS_API_KEY: ${{ secrets.GOOGLE_MAPS_API_KEY }}` as an environment variable to the build step so the key is never committed to git history.
3. **Mandatory Google Cloud Console Restrictions (Protects the Key in Production):**
   - Because browser keys are visible in DevTools on static sites, the key **must** be locked in **Google Cloud Console → APIs & Services → Credentials**:
     - **Application restrictions:** Select **Websites (HTTP referrers)** and whitelist only:
       - `https://<github-username-or-org>.github.io/<repo-name>/*`
       - `http://localhost:*` and `http://127.0.0.1:*`
     - **API restrictions:** Restrict the key strictly to **Maps JavaScript API** (and **Places API** if using search).
     - **Quota & Billing:** Set a daily map-load quota cap and budget alert.

### 7.4 Frontend-to-Data & Scoring Engine Integration Contract
Whether the frontend runs purely client-side on GitHub Pages or talks to the Python backend (`src/`), keep the data interface consistent with `data/sample_data_test.py`:
1. **Direct Client-Side NASA API Calls (CORS-Enabled, No Key Needed):**
   - **NASA POWER Agroclimatology API** can be queried directly from browser `fetch()` on GitHub Pages with no API key:
     ```text
     https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN&community=AG&longitude={lon}&latitude={lat}&start=20230101&end=20241231&format=JSON
     ```
   - **ISRIC SoilGrids REST API** (`https://rest.isric.org/soilgrids/v2.0/properties/query?lon={lon}&lat={lat}`) for soil OC%, pH, clay%, sand%, bulk density, and CEC (always keep `data/sample/mock_soil.csv` and `mock_climate.csv` bundled as an instant offline/demo fallback if an external API rate-limits or times out during judging).
2. **User Inputs from UI to Scoring Engine:**
   - Selected coordinates (`lat`, `lon`) or preset sample field ID (`F01`–`F08` from `data/sample/mock_soil.csv`).
   - Priority preset (`Balanced`, `Max Yield`, `Water Conservation`, `Soil Health First`, `Climate Resilient`) or custom weight sliders for the 7 criteria:
     `soil_health`, `water_stress`, `climate_resilience`, `nitrogen_fixation`, `yield_potential`, `drought_tolerance`, `soil_compatibility`.
   - Equipment constraint toggle: `row_crop_only` (`boolean`, excludes forage hay `C05` Alfalfa when `true`).
   - Sequence length: `years` (`3` or `4` year crop rotation cycle).
3. **Output Displayed in UI:**
   - Top-ranked multi-year crop rotation sequences (e.g., `Soybean -> Winter Wheat -> Corn`) sorted by `(total_score, water_stress, nitrogen_fixation)` descending.
   - Per-criterion score breakdown (0–100 scale), `penalty_multiplier`, and plain-English agronomic reasoning (e.g., legume nitrogen carry-over, root-depth compaction relief, drought trend resilience).

---

## 8. Mobile Measurement Station (MMS) Hardware Specification & Integration

> **Naming Rule:** Always refer to the physical sensor hardware unit as the **Mobile Measurement Station (MMS)** (or **MMS**). Never refer to it as "Elegoo Uno" or "Arduino" in any UI labels, documentation, code comments, or API responses.

1. **Sensors & Pin Mapping on the Mobile Measurement Station (MMS):**
   - `A0`: Capacitive Soil Moisture Sensor v1.2 (`soil_moisture_pct`: `0–100%`, `soil_moisture_raw`: calibrated `520` dry air to `280` submerged)
   - `D2`: DS18B20 Waterproof Stainless-Steel Soil Temperature Probe (`soil_temp_c`: `°C`, via 1-Wire adapter with built-in `4.7 kΩ` pull-up resistor)
   - `D3`: DHT11 Ambient Air Temperature & Relative Humidity Sensor (`air_temp_c`: `°C`, `air_humidity_pct`: `% RH`)
   - `A1`: Surface Rain Detection Sensor (`rain_intensity_pct`: `0–100%`, `rain_raw`: calibrated `60` dry to `270` wet, `is_raining`: `boolean`)
2. **USB Serial Telemetry Stream (`9600` baud on `/dev/ttyACM0` / `/dev/ttyUSB0`):**
   - Emits a single-line JSON packet every 2 seconds from `weather_box_firmware/weather_box_firmware.ino`:
     ```json
     {"soil_moisture_pct":16,"soil_moisture_raw":480,"soil_temp_c":21.69,"air_temp_c":22.0,"air_humidity_pct":49.0,"rain_intensity_pct":0,"rain_raw":22,"is_raining":false}
     ```
3. **Graceful Fallback Contract:**
   - When the **Mobile Measurement Station (MMS)** is plugged in (`connected: true`), its live readings populate the frontend KPI cards and "Live sensor readings" tab and adjust field moisture/drought/temperature in the rotation scoring engine.
   - When the **Mobile Measurement Station (MMS)** is unplugged (`connected: false`), the backend and frontend automatically fall back to NASA POWER + USDA SSURGO satellite/soil data and manual Wet/Dry simulation with zero errors.
4. **Running Everything Together (one command, one port):**
   ```bash
   python3 -m venv .venv && .venv/bin/pip install -r src/backend/requirements.txt
   .venv/bin/uvicorn --app-dir src/backend main:app --host 127.0.0.1 --port 8000
   ```
   Then open `http://localhost:8000`. The backend serves `src/front end/` and exposes `GET /mms/latest` (also `/sensor/latest`). The frontend (`pollMms()` in `app.js`) polls it every 2 seconds. On Linux the user needs serial permission (`sudo usermod -aG dialout $USER` or `sudo chmod a+rw /dev/ttyACM0`).
5. **Frontend Wiring (`src/front end/app.js`, `appState.mms`):**
   - Live MMS values replace the demo numbers in the Root-zone moisture and Soil temperature KPI cards and the "Mobile Measurement Station readings" card on the Live sensor tab (moisture, soil temp, air humidity, rain).
   - While live, the MMS moisture reading decides Wet or Dry (`probe_mode`, wet when moisture is 35% or higher or it is raining), so the manual Wet/Dry buttons are ignored and the rotation ranking updates automatically.
   - The sidebar toggle reads `Live · MMS connected` when plugged in and `Enabled · demo (MMS offline)` otherwise. Layout and CSS are unchanged.
