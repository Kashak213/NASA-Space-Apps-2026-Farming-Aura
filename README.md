# Field Shift: Adapting Farms with NASA Data

**Event:** NASA Space Apps Challenge 2026  
**Team:** Farming Aura  
**Challenge:** Field Shift: Adapting Farms with NASA Data  

---

## Project Overview
Field Shift is a crop rotation decision-support system built for farmers adapting to shifting rainfall, summer heat stress, and soil health challenges. Given a farm's GPS coordinates, crop choices, and management priorities, the system pulls satellite agroclimatology metrics from NASA POWER and root-zone soil survey horizons from USDA NRCS SSURGO to recommend multi-year crop rotation sequences.

Our model separates annual field and vegetable rotations from long-term woody perennial crops (such as apple orchards, grape vineyards, berries, and sugar maple stands) so that annual sequences stay biologically realistic while still scoring perennial site suitability.

---

## Key Features
- **Live NASA POWER Agroclimatology Pipeline (`src/backend/nasa_client.py`):** Queries surface shortwave downward solar irradiance (`ALLSKY_SFC_SW_DWN`), 2-meter wind speed (`WS2M`), corrected precipitation (`PRECTOTCORR`), 2-meter air temperature (`T2M`), and satellite-assimilated root-zone soil wetness (`GWETROOT`). Separates May-September growing-season conditions from winter snow months and calculates year-over-year climate trends.
- **USDA NRCS SSURGO Root-Zone Soil Pipeline (`src/backend/fetch_soil.py`):** Queries the USDA Soil Data Access Tabular API by latitude and longitude, aggregates topsoil and subsoil horizons using horizon-thickness depth weighting, and tracks organic carbon, pH, clay/silt/sand texture, cation exchange capacity (CEC), available water capacity (AWC), drainage class, and subsoil hardpan bulk density.
- **17 New York Crop Groups & Perennial Separation (`src/backend/crops.py`):** Covers field corn, soybeans, small grains (wheat, oats, barley), hay and alfalfa, snap beans and green peas, sweet corn, cabbage and brassicas, potatoes, onions, beets and carrots, squash and pumpkins, winter cover crop mixes (rye and crimson clover), and perennial orchard/vineyard/agroforestry systems.
- **Multi-Factor Agronomic Scoring Engine (`src/backend/scoring.py`):** Evaluates candidate rotations across 7 weighted sub-scores (`soil_health`, `water_stress`, `climate_res`, `nitrogen_fix`, `yield`, `drought_tol`, and `soil_compat`) with 5 preset farmer priority profiles (`Balanced`, `Max Yield`, `Water Conservation`, `Soil Health First`, and `Climate Resilient`) plus custom slider weights.
- **Disease Spacing, Nutrient Balance & Transition Logic:** Rewards legume-to-grain nitrogen carry-over and alternating root depths while penalizing monoculture repeats, 2-year root/brassica disease host repeats, and back-to-back heavy phosphorus and potassium feeders.
- **Ground-Truth Sensor Overrides (`src/backend/main.py` & `src/backend/mms_sensor.py`):** Accepts live USB serial telemetry from the in-field **Mobile Measurement Station (MMS)** (capacitive soil moisture, soil temperature, air temperature/humidity, and surface rain detection) or optional sensor overrides to refine satellite estimates.

---

## Repository Structure
- `src/backend/main.py` - Main backend pipeline and FastAPI REST server (`/analyze`, `/crops`, `/regions`, `/profiles`, `/health`).
- `src/backend/scoring.py` - Seven-factor crop rotation scoring engine, drainage and thermal compatibility math, and sequence transition analysis.
- `src/backend/nasa_client.py` - NASA POWER REST client with growing-season aggregation, `GWETROOT` soil moisture, and local offline caching.
- `src/backend/fetch_soil.py` - USDA NRCS Soil Data Access (SSURGO) spatial T-SQL client with depth-weighted horizon aggregation and offline caching.
- `src/backend/crops.py` - Crop catalog loader, constraint filter, and combinatorial N-year rotation generator.
- `src/backend/test_model.py` - Interactive terminal testing tool for running coordinates, crop selections, and priority profiles.
- `src/backend/data/` - Crop catalog (`crops.json`), New York agricultural region baselines (`ny_regions.json`), and offline NASA/USDA cache files.
- `data/` and `beta_algorithm_testing/` - Pre-hackathon algorithm math verification script (`data/sample_data_test.py`) and synthetic CSV test files.

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Backend Pipeline Test
```bash
python src/backend/main.py
```

### 3. Run the Interactive Terminal Model Tester
```bash
python src/backend/test_model.py
```

### 4. Start the FastAPI Server
```bash
uvicorn src.backend.main:app --reload --port 8000
```

### 5. Run the Pre-Hackathon Algorithm Verification Suite
```bash
python data/sample_data_test.py
```

---

## Data Sources & Citations
- **NASA POWER (Prediction Of Worldwide Energy Resources):** NASA Langley Research Center Agroclimatology Community REST API (`ALLSKY_SFC_SW_DWN`, `WS2M`, `PRECTOTCORR`, `T2M`, `GWETROOT`). https://power.larc.nasa.gov/
- **USDA NRCS Soil Data Access (SDA) / SSURGO:** United States Department of Agriculture Natural Resources Conservation Service Tabular Spatial API. https://sdmdataaccess.sc.egov.usda.gov/
- **Agronomic Reference Ranges:** Cornell Cooperative Extension New York Field Crops and Vegetable Guidelines and USDA NRCS Cover Crop Termination and Rotation Guides.
- **Pre-Hackathon Prototype Disclosure:** `data/sample_data_test.py`, `data/sample/mock_*.csv`, and `beta_algorithm_testing/README.md` were created prior to the hackathon weekend to validate sorting and transition math on synthetic data before connecting live NASA POWER and USDA SSURGO APIs in `src/backend/`.
