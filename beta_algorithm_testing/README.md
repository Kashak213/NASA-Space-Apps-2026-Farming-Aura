#  Beta Testing: Crop Rotation Scoring & Sorting Algorithm

> **Status:** Pre-Hackathon Algorithm Beta & Mock Data Validation  
> **Project:** NASA Space Apps 2026 — *Team Farming Aura*  
> **Challenge:** Field Shift: Adapting Farms with NASA Data

---

## Overview
This folder documents the **beta testing phase** of our crop rotation sorting and recommendation math prior to the official hackathon build. All tests currently run against synthetic/mock datasets (`../data/sample/`) to verify that our multi-criteria decision analysis (MCDA) scoring and tie-breaking sort logic behave predictably across diverse farm conditions and farmer priority profiles.

---

## What Is Being Beta Tested

### 1. Multi-Criteria Scoring Engine
Each candidate crop rotation sequence (e.g., `Corn → Soybean → Winter Wheat` or `Sorghum → Field Pea → Corn`) is evaluated against 7 normalized (0.0 to 1.0) sub-scores:
- **Soil Health Score:** Evaluates Organic Carbon %, pH balance (ideal 6.0–7.0), Bulk Density, and Cation Exchange Capacity (CEC).
- **Water Stress Score:** Combines field water supply (historical drought index + root-zone soil moisture, simulating NASA SMAP L4 inputs) with each crop's water demand: `1 - (1 - supply) × demand_norm`. Wet fields score high for any crop; dry fields penalize thirsty crops. This makes the score rotation-specific so it can actually break ties in the sort.
- **Climate Resilience Score:** Evaluates precipitation anomalies (simulating NASA GPM / POWER) and vegetative health (MODIS NDVI).
- **Nitrogen Fixation Bonus:** Rewards sequences incorporating legumes and cover crops.
- **Yield Potential:** Normalized expected productivity per hectare.
- **Drought Tolerance:** Intrinsic crop resilience to dry spells.
- **Soil Compatibility:** Matches crop-specific optimal pH and clay percentage ranges against the target field's soil profile.

### 2. Farmer Priority Profiles (Sensitivity Testing)
We test 5 distinct weight distributions representing different farmer goals:
1. **Balanced** — Equal emphasis on soil health (20%), water stress (20%), climate resilience (15%), N-fixation (15%), and yield (15%).
2. **Max Yield** — Heavy weighting on productivity (40% yield).
3. **Water Conservation** — Heavy weighting on water stress (35%) and drought tolerance (15%).
4. **Soil Health First** — Heavy weighting on soil health (30%) and nitrogen fixation (25%).
5. **Climate Resilient** — Heavy weighting on climate anomaly stability (25%) and water stress (20%).

### 3. Deterministic Multi-Key Sorting
Rotations are sorted using a 3-tier hierarchy:
1. `total_score` (Descending)
2. `water_stress` (Descending — tie-breaker favoring water conservation)
3. `nitrogen_fixation` (Descending — tie-breaker favoring soil regeneration)

---

## How to Run the Beta Test Suite
From the repository root, run:

```bash
python3 data/sample_data_test.py
```

*(Uses Python's standard library `csv` and `statistics` modules so any collaborator can run it immediately on their laptop or desktop without environment setup issues.)*

The script ends with **assertion checks** (Test 5). If anything breaks, it exits with an `AssertionError` instead of silently printing output. It checks that:
- profile weights sum to 1.0
- all scores stay in [0, 1]
- water stress varies across rotations on a dry field
- dry fields penalize thirsty rotations
- the ranking order and tiebreakers are correct
- results are deterministic

---

## Beta Test Findings & Next Iterations
- **Spatial Differentiation Works:** High-health fields (`F007`, `F005`) score ~0.66–0.70 on `Corn → Soybean → Winter Wheat`, while the degraded, drought-stressed field `F006` drops to ~0.43. That gap flags the need for regenerative intervention.
- **Water-Aware Ranking (fixed Oct 23):** Water stress used to be field-level only, so it was identical for every rotation on a field. That made the secondary sort key useless. It now uses crop `water_demand_mm`. As a result, the `Water Conservation` and `Climate Resilient` profiles now pick `Sorghum → Soybean` over `Alfalfa → Corn → Alfalfa`.
- **Known Limitation — Field-Level Offset:** Soil health and climate resilience are still field-level, so they shift all rotations on a field equally. They differentiate *fields*, not *rotations*.
- **Observation to Address Next:** `Alfalfa → Corn → Alfalfa` still ranks #1 under the Balanced, Max Yield and Soil Health First profiles, because of its high yield and 0.90 nitrogen fixation. Planned next: **sequence transition penalties** (this rotation repeats Alfalfa when the cycle wraps around) and **equipment/feasibility filters**.
- **Unused Crop Traits:** `soil_building_score` and `root_depth_m` in `mock_crops.csv` are not yet used in scoring.
