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
    - **Code comments:** Casual, practical, and easy to skim. Only explain what the math or logic is doing and why, without sacrificing code readability or functionality.
    - **READMEs:** Same authentic student background, but slightly more technical, structured, and concise than code comments so it is clear we put real time and care into documenting our work.
- **Exception for `AI_BRIEFING.md`:**
  - Keep `AI_BRIEFING.md` as technical, dense, and precise as needed. Do not dumb down `AI_BRIEFING.md` so that AI agents transferring work between computers or sessions retain full comprehension and save context tokens.

---

## 3. NASA Space Apps Compliance & Pre-Hackathon Rules
- **Current Phase:** Pre-Hackathon Preparation & Algorithm Beta Testing (Before Nov 14, 2026).
- **Rules Constraint:** All final application code and UI must be built during the official hackathon window (Nov 14–15). Everything currently in the repo is **pre-hackathon dataset exploration, mock data validation, and beta testing of sorting/scoring mathematics**.
- **Mandatory Citations (for final submission):**
  - Open-source Python libraries (`pandas`, `numpy`, `scikit-learn`, `streamlit`, `plotly`, `folium`, `earthaccess`, `geopandas`, `rasterio`, `xarray`)
  - NASA Datasets: SMAP (Soil Moisture), MODIS (NDVI/EVI), GPM (Precipitation), NASA POWER (Agroclimatology)
  - Soil/Ag Datasets: ISRIC SoilGrids, USDA NASS / SSURGO
  - AI Coding Assistants: Google Antigravity / Anthropic Claude Code

---

## 4. Core Architecture & Decisions Made
1. **Frontend / UI (To be built Nov 14–15):**
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
├── notebooks/                     # For data exploration (held until hackathon)
└── src/                           # Reserved for official hackathon build on Nov 14-15
```

---

## 6. Next Steps / How to Pick Up Work
- **To run the current algorithm beta test:**
  ```bash
  python data/sample_data_test.py
  ```
  Exits non-zero with an `AssertionError` if any check in Test 5 fails.

### Change Log
- **Oct 25, 2026 — Data analysis, sequence modeling & style guidelines (Google Antigravity):**
  - **Added Temporal & Seasonal Climate Analysis:** `get_field_climate_agg` now computes seasonal splits (`spring_precip_mm`, `summer_precip_mm`, `annual_precip_mm`, `summer_temp_c`, `summer_drought`) and year-over-year climate trends (`2023 → 2024` `drought_trend`, `precip_anom_trend`, `ndvi_trend`).
  - **Made Soil Health & Climate Resilience Rotation-Responsive:** `soil_health_score` now integrates `sand_pct`, `soil_building_score`, and `root_depth_m` compaction relief; `climate_resilience_score` integrates 2023→2024 precip trends, summer heat stress, and functional `crop_type` diversity. Both now differentiate rotations on the same field as well as ranking fields.
  - **Added Sequence Transition & Order Engine (`sequence_transition_analysis`):** Penalizes back-to-back and cycle wrap-around crop repeats (`Alfalfa → Corn → Alfalfa` no longer dominates `Balanced` or `Soil Health First`), rewards N carry-over from legumes to subsequent non-fixing crops, rewards root-depth alternation, and differentiates sequence starting order (`Soy → Cover → Corn` vs. `Corn → Soy → Cover`).
  - **Added Equipment Constraints & Algorithmic Sequence Generator:** Added `filter_rotations_by_constraints` (e.g., `row_crop_only=True` to exclude forage hay `C05`) and `generate_candidate_rotations` (combinatorial N-year sequence generator with agronomic pruning).
  - **Added Tone/Style Guidelines & Cleaned Comments/README:** Added Section 2 in `AI_BRIEFING.md` specifying the AP Bio/EnvSci high-school student voice, no semicolons, minimal emojis, and no AI-cliché phrasing across code comments and READMEs (while keeping `AI_BRIEFING.md` technical for agent handoffs).
- **Oct 23, 2026 — Review & fixes (Claude Code):**
  - **Fixed:** `water_stress` was field-level only; updated to combine field water supply with each crop's `water_demand_mm`.
  - **Added:** initial assertion checks (Test 5) and removed duplicate `beta_algorithm_testing/sample_data_test.py`.

### Pre-Hackathon Guardrails (read before doing new work)
- ✅ **Allowed now:** mock-data math refinements, assertions/tests, design notes, and dataset research (reading NASA dataset docs, inspecting a sample response by hand).
- ⚠️ **Keep minimal:** NASA POWER API exploration. Fetching one sample response to learn the JSON shape is fine. Do **not** build an API client or ingestion pipeline before Nov 14.
- ⛔ **Hold until Nov 14–15:**
  - any code in `src/`
  - the Streamlit UI and folium maps
  - real SMAP/MODIS/GPM ingestion
  - Arduino integration
- 📝 In the final submission, disclose this scoring engine as **pre-hackathon prototype work on mock data**.

### Open Pre-Hackathon Explorations (mock data & docs only)
- Inspect a single sample NASA POWER / SMAP / MODIS response payload by hand to document exact JSON/GeoTIFF field names for Nov 14 mapping.
- Define mock ground-truth vs. satellite anomaly delta math (how local soil moisture/temperature sensor offsets adjust `field_water_supply_score` on Nov 14).
