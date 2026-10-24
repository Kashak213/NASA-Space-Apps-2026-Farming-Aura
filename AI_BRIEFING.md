# AI Assistant Briefing & Project Context (`AI_BRIEFING.md`)

> **Instructions for AI Assistants (Claude Code, Cursor, Antigravity, Copilot, etc.):**  
> Read this file first to get full context on our project, architecture, rules compliance, and current state when switching between laptop/desktop environments or across team members.

---

## 1. Project Overview
- **Event:** NASA Space Apps Challenge 2026 (Nov 14–15, 2026)
- **Team Repo:** `nasa space apps project teamfarming aura`
- **Challenge:** *"Field Shift: Adapting Farms with NASA Data"*
- **Objective:** Build a decision-support tool that combines NASA Earth observations (SMAP, MODIS, GPM, NASA POWER), local soil metrics (SoilGrids/USDA SSURGO), crop characteristics, and optional local hardware sensor inputs (Arduino/Raspberry Pi) to recommend optimal crop rotation strategies tailored to farmer priorities.

---

## 2. NASA Space Apps Compliance & Pre-Hackathon Rules
- **Current Phase:** Pre-Hackathon Preparation & Algorithm Beta Testing (Before Nov 14, 2026).
- **Rules Constraint:** All final application code and UI must be built during the official hackathon window (Nov 14–15). Everything currently in the repo is **pre-hackathon dataset exploration, mock data validation, and beta testing of sorting/scoring mathematics**.
- **Mandatory Citations (for final submission):**
  - Open-source Python libraries (`pandas`, `numpy`, `scikit-learn`, `streamlit`, `plotly`, `folium`, `earthaccess`, `geopandas`, `rasterio`, `xarray`)
  - NASA Datasets: SMAP (Soil Moisture), MODIS (NDVI/EVI), GPM (Precipitation), NASA POWER (Agroclimatology)
  - Soil/Ag Datasets: ISRIC SoilGrids, USDA NASS / SSURGO
  - AI Coding Assistants: Google Antigravity / Anthropic Claude Code

---

## 3. Core Architecture & Decisions Made
1. **Frontend / UI (To be built Nov 14–15):**
   - **Streamlit** (desktop-first web dashboard) — fast iteration, interactive maps (`folium`), time-series charts (`plotly`), and farmer priority sliders.
   - No separate mobile codebase or Figma-only mockups; focus 100% on a functional data-driven prototype.
2. **Backend / Recommendation Engine:**
   - Multi-criteria weighted scoring formula that ranks candidate multi-year crop rotation sequences:
     ```
     rotation_score = (
         w1 * soil_health_score      +  # OC%, pH, bulk density, CEC
         w2 * water_stress_score     +  # 1 - (1 - field water supply) × crop water demand (rotation-specific)
         w3 * climate_resilience     +  # Precip anomaly stability + historical NDVI
         w4 * nitrogen_fixation      +  # Legume / cover crop soil-building bonus
         w5 * yield_potential        +  # Normalized crop yield potential
         w6 * drought_tolerance      +  # Crop drought tolerance rating
         w7 * soil_compatibility        # Crop optimal pH and clay % match with field
     )
     ```
   - **Multi-key Sorting Strategy:**
     1. Primary: `total_score` (Descending)
     2. Secondary: `water_stress` (Descending — breaks ties in favor of drought resilience)
     3. Tertiary: `nitrogen_fixation` (Descending — breaks ties in favor of soil-building legumes)
3. **Optional Hardware Integration (Bonus Differentiator):**
   - Decoupled Arduino / microcontroller sensor module reading localized soil temperature, moisture, or air pressure over Serial/HTTP as a ground-truth safety layer compared against satellite forecasts.

---

## 4. Current Repository Structure
```text
.
├── AI_BRIEFING.md                 # This context file for seamless multi-machine AI handoff
├── requirements.txt               # Target Python dependencies for the hackathon build
├── beta_algorithm_testing/        # Dedicated folder for pre-hackathon beta algorithm tests
│   └── README.md                  # Explains the beta testing scope, mock datasets, and findings
├── data/
│   ├── sample_data_test.py        # Zero-dependency (stdlib) test runner for scoring & sorting (single copy; includes assertion checks)
│   └── sample/
│       ├── mock_soil.csv          # 8 sample fields with OC%, pH, clay%, sand%, bulk density, CEC
│       ├── mock_climate.csv       # Seasonal temp, precip, drought index, soil moisture, NDVI
│       └── mock_crops.csv         # 12 crops (grains, legumes, oilseeds, covers) & traits
├── notebooks/                     # For data exploration
└── src/                           # Reserved for official hackathon build on Nov 14-15
```

---

## 5. Next Steps / How to Pick Up Work
- **To run the current algorithm beta test:**
  ```bash
  python3 data/sample_data_test.py
  ```
  Exits non-zero with an `AssertionError` if any check in Test 5 fails.

### Change Log
- **Oct 23, 2026 — Review & fixes (Claude Code):**
  - **Fixed:** `water_stress` was field-level only, so it was identical for every rotation on a field and the secondary sort key could never break a tie. It now combines field water supply with each crop's `water_demand_mm`. Result: the Water Conservation and Climate Resilient profiles now pick `Sorghum → Soybean` instead of Alfalfa.
  - **Added:** assertion checks (Test 5) covering:
    - weights sum to 1
    - all scores in [0, 1]
    - water stress varies across rotations
    - dry fields penalize thirsty crops
    - sort order and tiebreakers are correct
    - results are deterministic

    This replaces the old, unverified "tiebreaks resolve correctly" print.
  - **Removed:** the duplicate `beta_algorithm_testing/sample_data_test.py`. It differed only in path; `data/sample_data_test.py` is the single source.
  - **Known limitations:**
    - Soil health and climate resilience are still field-level, so they rank fields but not rotations.
    - `soil_building_score` and `root_depth_m` are unused.
    - `Alfalfa → Corn → Alfalfa` still wins the Balanced, Max Yield and Soil Health First profiles.

### Pre-Hackathon Guardrails (read before doing new work)
- ✅ **Allowed now:** mock-data math refinements, assertions/tests, design notes, and dataset research (reading NASA dataset docs, inspecting a sample response by hand).
- ⚠️ **Keep minimal:** NASA POWER API exploration. Fetching one sample response to learn the JSON shape is fine. Do **not** build an API client or ingestion pipeline before Nov 14.
- ⛔ **Hold until Nov 14–15:**
  - any code in `src/`
  - the Streamlit UI and folium maps
  - real SMAP/MODIS/GPM ingestion
  - Arduino integration
- 📝 In the final submission, disclose this scoring engine as **pre-hackathon prototype work on mock data**.

### Safe Refinements to Explore Next (mock data only)
- Rotation transition penalties: penalize the same crop back-to-back, including the wrap-around, because of pest and disease pressure.
- Crop availability and equipment constraints, so Alfalfa doesn't dominate when a farmer only has row-crop equipment.
- Decide whether to fold `soil_building_score` and `root_depth_m` into scoring.

