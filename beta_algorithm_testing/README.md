# Beta Testing: Crop Rotation Scoring and Sorting Algorithm

**Status:** Pre-Hackathon Algorithm Beta and Mock Data Testing  
**Project:** NASA Space Apps 2026 - Team Farming Aura  
**Challenge:** Field Shift: Adapting Farms with NASA Data

---

## Overview
This folder documents our pre-hackathon testing for the crop rotation scoring and sorting math before the official competition weekend. Right now all tests run on small synthetic CSV files in `../data/sample/` using `../data/sample_data_test.py`. Our goal during this phase is to make sure the multi-variable scoring formula, crop order rules, and tie-breaking logic give realistic agricultural results across different soil types and farmer goals.

---

## How the Scoring Model Works

### 1. Seasonal and Year-over-Year Climate Aggregation
Instead of averaging every climate row into one flat number, `get_field_climate_agg` separates seasonal patterns and recent trends:
- **Seasonal Breakdown (`spring` vs `summer`):** Adds spring and summer rainfall to get `annual_precip_mm` and tracks `summer_temp_c` and `summer_drought` separately, since mid-summer heat and water shortages hit row crops the hardest.
- **2023 to 2024 Trends:** Calculates `drought_trend`, `precip_anom_trend`, and `ndvi_trend` between the two years in `mock_climate.csv`. If a field is drying out faster or losing plant vigor (NDVI), the model lowers its baseline water supply and climate stability scores.

### 2. Seven Sub-Scores and Sequence Transition Rules
Each candidate rotation (such as `Soybean -> Cover Crop Mix -> Corn` or `Sorghum -> Soybean`) gets 7 normalized sub-scores between `0.0` and `1.0`, followed by a sequence penalty check:
- **Soil Health Score (`soil_health`):** Combines the field's starting soil metrics (`organic_carbon_pct`, `ph`, `bulk_density`, `cec`, and how close `sand_pct` and `clay_pct` are to a balanced loam) with the rotation's ability to rebuild soil (`soil_building_score` and `root_depth_m`). On compacted fields with high bulk density, deep-rooted crops score higher because they help open up the soil structure.
- **Water Stress Score (`water_stress`):** Compares field water availability (drought index, root-zone soil moisture from simulated NASA SMAP inputs, and the 2023-2024 drought trend) against each crop's `water_demand_mm` and total annual rainfall. Wet fields score high for almost any crop, while dry fields penalize high-transpiration crops like corn or alfalfa.
- **Climate Resilience Score (`climate_res`):** Combines precipitation anomalies, summer heat stress, and MODIS NDVI readings with the number of distinct crop groups (`grain`, `legume`, `oilseed`, `cover`) in the sequence. Mixing different functional plant groups helps buffer against unpredictable weather.
- **Nitrogen Fixation (`nitrogen_fixation`):** Uses each crop's base nitrogen fixation rating and adds a carry-over bonus when a legume or cover crop is planted right before a non-fixing grain crop. Legumes host *Rhizobium* bacteria in root nodules that replenish soil nitrogen for the next year's grain crop.
- **Yield Potential (`yield_potential`):** Average `typical_yield_t_ha` divided by the dataset maximum (`12.0 t/ha`).
- **Drought Tolerance (`drought_tolerance`):** Average drought tolerance rating across the crops in the sequence.
- **Soil Compatibility (`soil_compatibility`):** Checks how closely each crop's optimal pH and clay ranges match the field, blended with how much root depths alternate from year to year (`root_depth_m`).
- **Crop Order and Monoculture Penalty (`sequence_transition_analysis`):** Checks every step in the cycle, including when the last year loops back to Year 1. Planting the exact same crop back to back (like `Alfalfa -> Corn -> Alfalfa` looping from Year 3 back to Year 1) or repeating the same `crop_type` lets crop-specific pests and soil diseases build up, so the model applies a `penalty_multiplier` to the total score.

### 3. Equipment Filters and Sequence Generation
- `filter_rotations_by_constraints`: Filters candidate rotations by equipment or water limits. For example, `row_crop_only=True` removes perennial hay crops like `Alfalfa` (`C05`) when a farmer only has standard grain combine equipment.
- `generate_candidate_rotations`: Builds valid multi-year sequences from `mock_crops.csv` while filtering out consecutive identical crop types, rotations without a nitrogen fixer, or rotations with too many zero-yield cover years.

### 4. Farmer Priority Profiles
We test 5 weight profiles (each summing to `1.0`) to simulate different farm priorities:
1. **Balanced:** `20%` soil health, `20%` water stress, `15%` climate resilience, `15%` N-fixation, `15%` yield, `10%` drought tolerance, `5%` soil compatibility.
2. **Max Yield:** `40%` weight on yield potential.
3. **Water Conservation:** `35%` weight on water stress and `15%` on drought tolerance.
4. **Soil Health First:** `30%` weight on soil health and `25%` on nitrogen fixation.
5. **Climate Resilient:** `25%` weight on climate resilience and `20%` on water stress.

### 5. Multi-Key Sorting Order
Candidate rotations are ranked in descending order using three keys:
1. `total_score` (Primary)
2. `water_stress` (Secondary tiebreaker favoring lower water risk)
3. `nitrogen_fixation` (Tertiary tiebreaker favoring soil nitrogen recovery)

---

## How to Run the Test Script
From the repository root, run:

```bash
python data/sample_data_test.py
```

The script only imports standard library modules (`csv`, `itertools`, `math`, `statistics`, `sys`) so it runs on Windows, macOS, and Linux without virtual environment setup.

Test 5 runs 10 `assert` checks at the end of the script and exits with an `AssertionError` if any check fails:
- All profile weights sum to `1.0`
- All sub-scores and total scores stay inside `[0.0, 1.0]`
- `water_stress`, `soil_health`, and `climate_res` all vary across different rotations on the same field
- Dry fields penalize high-water rotations compared to low-water rotations
- The wrap-around monoculture penalty keeps `Alfalfa -> Corn -> Alfalfa` from winning the `Balanced` profile
- Changing the sequence order (`Soybean -> Cover Crop Mix -> Corn` vs `Corn -> Soybean -> Cover Crop Mix`) produces different scores
- Equipment filtering and dynamic sequence generation return valid rotations
- Output rankings are sorted properly and tiebreakers resolve in the right order
- Results are deterministic across repeated runs

---

## Current Test Results and Observations
- **Field Conditions Shift the Top Pick:** On a healthy, well-watered field (`F003`), the `Balanced` profile picks `Soybean -> Cover Crop Mix -> Corn` (`0.6639`). On the dry, compacted, low-carbon field `F006`, `Balanced` switches to `Sorghum -> Soybean` (`0.4938`) for drought safety, while `Soil Health First` picks `Soybean -> Cover Crop Mix -> Corn` (`0.4682`) to rebuild organic matter and loosen compacted clay.
- **Wrap-Around Repeat Fix:** Before adding transition penalties, `Alfalfa -> Corn -> Alfalfa` ranked #1 on almost every profile because of its high yield and N-fixation numbers, even though Year 3 loops directly back into Year 1 Alfalfa. With `sequence_transition_analysis` in place, it only wins `Max Yield` when forage crops are allowed, and gets filtered out completely when `row_crop_only=True` is enabled.
- **All Mock Columns Used:** Every trait in `mock_crops.csv`, `mock_soil.csv`, and `mock_climate.csv` (`soil_building_score`, `root_depth_m`, `crop_type`, `sand_pct`, `avg_temp_c`, `total_precip_mm`, `year`, and `season`) is now wired into the scoring functions.
