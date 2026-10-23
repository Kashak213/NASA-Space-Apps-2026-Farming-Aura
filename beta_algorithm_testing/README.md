# 🧪 Beta Testing: Crop Rotation Scoring & Sorting Algorithm

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
- **Water Stress Score:** Evaluates historical drought index and root-zone soil moisture (simulating NASA SMAP L4 inputs).
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

---

## Beta Test Findings & Next Iterations
- **Spatial Differentiation Works:** High-health fields (`F007`, `F005`) score ~0.70+ on standard commodity rotations, while degraded/drought-stressed fields (`F006`) drop to ~0.39, flagging the need for regenerative intervention.
- **Observation to Address Next:** Deep-rooted perennial legumes (`Alfalfa → Corn → Alfalfa`) currently score highest across several profiles due to high yield + 0.90 nitrogen fixation. In future iterations, we plan to add **equipment/feasibility filters** and **sequence transition penalties** (e.g., penalizing back-to-back monoculture).

