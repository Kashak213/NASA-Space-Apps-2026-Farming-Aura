# AI Assistant Briefing & Project Context (`AI_BRIEFING.md`)

> **Instructions for AI Assistants (Claude Code, Cursor, Antigravity, Copilot, etc.):**  
> Read this file first to get full context on our project, architecture, rules compliance, writing style, and current state when switching between laptop/desktop environments or across team members.

---

## 1. Project Overview
- **Event:** NASA Space Apps Challenge 2026 (Nov 14–15, 2026)
- **Team Repo:** `nasa space apps project teamfarming aura`
- **Challenge:** *"Field Shift: Adapting Farms with NASA Data"*
- **Objective:** Build a decision-support tool that combines NASA Earth observations (SMAP, MODIS, GPM, NASA POWER), local soil metrics (SoilGrids/USDA SSURGO), crop characteristics, and optional local hardware sensor inputs (Arduino/Raspberry Pi) to recommend optimal crop rotation strategies tailored to farmer priorities.

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
1. **Frontend / UI (Active Build in `src/ui/`):**
   - **Streamlit** (desktop-first web dashboard) — fast iteration, interactive maps (`folium`), time-series charts (`plotly`), and farmer priority sliders.
   - No separate mobile codebase or Figma-only mockups; focus 100% on a functional data-driven prototype.
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
   - **Sequence Transition & Constraint Engine:**
     - Cyclic transition analysis (`sequence_transition_analysis`) penalizes back-to-back and wrap-around monoculture repeats (`seq[i] == seq[(i+1)%n]`) and consecutive same-family (`crop_type`) transitions, while rewarding legume-to-grain nitrogen carry-over and root-depth alternation.
     - Equipment/feasibility filtering (`filter_rotations_by_constraints`) and algorithmic N-year sequence generation (`generate_candidate_rotations`).
   - **Multi-key Sorting Strategy:**
     1. Primary: `total_score` (Descending)
     2. Secondary: `water_stress` (Descending — breaks ties in favor of drought resilience)
     3. Tertiary: `nitrogen_fixation` (Descending — breaks ties in favor of soil-building legumes)
3. **Optional Hardware Integration (Bonus Differentiator):**
   - Decoupled Arduino / microcontroller sensor module reading localized soil temperature, moisture, or air pressure over Serial/HTTP as a ground-truth safety layer compared against satellite forecasts.

---

## 5. Current Repository Structure
```text
.
├── AI_BRIEFING.md                 # This context file for seamless multi-machine AI handoff
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
    ├── backend/                   # Python FastAPI backend & NASA POWER integration
    │   ├── main.py                # FastAPI routes (/analyze, CORS setup)
    │   ├── nasa_client.py         # NASA POWER API client (ALLSKY_SFC_SW_DWN, WS2M, PRECTOTCORR, T2M) + -999 stripping & offline cache
    │   ├── scoring.py             # Crop suitability & climate shift alert logic
    │   ├── requirements.txt       # Backend dependencies (fastapi, uvicorn, requests)
    │   └── data/                  # Static & cached JSON files
    │       ├── ny_regions.json    # Static NY soil texture, pH & coordinates lookup
    │       ├── crops.json         # Static 6 flagship NY crops thresholds
    │       └── nasa_cache/        # Saved NASA POWER JSONs for offline demo backup
    ├── pipeline/                  # Live NASA POWER, SMAP, MODIS, GPM, and SoilGrids data fetchers
    ├── engine/                    # Production crop rotation scoring, transition penalties, and ML ranking
    └── ui/                        # Streamlit dashboard, Folium map selector, and Plotly charts
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
   - Add ground-truth hardware sensor delta adjustments (allowing local Arduino/sensor soil temperature, moisture, or pressure readings to override/adjust satellite anomaly scores).
3. **Phase 3 — Interactive Streamlit Dashboard (`src/ui/`):**
   - Interactive `folium` map or coordinate/county selector to pick a farm location.
   - Farmer priority weight sliders (`Balanced`, `Max Yield`, `Water Conservation`, `Soil Health First`, `Climate Resilient`, plus custom sliders) and equipment constraint toggles (`row_crop_only`).
   - Ranked crop rotation cards with multi-year sequence breakdown, component score radar/bar charts (`plotly`), and historical climate/NDVI trend visualizations.
4. **Phase 4 — Verification, Demo Video & Submission:**
   - Verify end-to-end flow with live coordinates and fallback offline mode.
   - Compile complete citations list for the Space Apps submission form.
