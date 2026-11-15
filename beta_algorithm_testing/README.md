# Beta Testing: Crop Rotation Scoring and Sorting Algorithm

**Status:** Pre-Hackathon Algorithm Beta and Mock Data Testing  
**Project:** NASA Space Apps 2026 - Team Farming Aura  
**Challenge:** Field Shift: Adapting Farms with NASA Data

## Overview
This folder documents our pre-hackathon testing for the crop rotation scoring and sorting math before the competition weekend. Right now all tests run on small mock CSV files in `../data/sample/` using `../data/sample_data_test.py`. Our goal here was to make sure the scoring formula, crop order rules, and tie-breaking logic give realistic farming results across different soil types and farmer goals before hooking up live NASA feeds.

## How the Scoring Model Works

### 1. Seasonal and Year-over-Year Climate Stats
Instead of averaging every climate row into one flat number, `get_field_climate_agg` splits out seasons and recent trends:
- **Seasonal Breakdown (`spring` vs `summer`):** Adds spring and summer rainfall to get `annual_precip_mm` and tracks `summer_temp_c` and `summer_drought` separately, since mid-summer heat and dry spells hit row crops the hardest.
- **2023 to 2024 Trends:** Calculates `drought_trend`, `precip_anom_trend`, and `ndvi_trend` between the two years in `mock_climate.csv`. If a field is drying out faster or losing plant health (NDVI), the model lowers its starting water supply and climate stability scores.

### 2. Seven Sub-Scores and Crop Order Rules
Each rotation (like `Soybean -> Cover Crop Mix -> Corn` or `Sorghum -> Soybean`) gets 7 sub-scores between `0.0` and `1.0`, plus a crop transition penalty check:
- **Soil Health Score (`soil_health`):** Combines starting field metrics (`organic_carbon_pct`, `ph`, `bulk_density`, `cec`, and how close `sand_pct` and `clay_pct` are to a balanced loam) with how much the crops rebuild soil (`soil_building_score` and `root_depth_m`). On packed clay fields with high bulk density, deep-rooted crops score higher because their roots help break up compaction.
- **Water Stress Score (`water_stress`):** Compares field water supply (drought index, root-zone soil moisture from simulated NASA SMAP data, and the 2023-2024 drought trend) against each crop's `water_demand_mm` and yearly rainfall. Wet fields score high for almost any crop, while dry fields punish thirsty crops with high transpiration like corn or alfalfa.
- **Climate Resilience Score (`climate_res`):** Combines rainfall anomalies, summer heat stress, and MODIS NDVI readings with the number of different crop types (`grain`, `legume`, `oilseed`, `cover`) in the sequence. Mixing different plant families spreads out weather risk.
- **Nitrogen Fixation (`nitrogen_fixation`):** Uses each crop's base nitrogen fixation rating and adds a carry-over bonus when a legume or cover crop is planted right before a non-fixing grain crop. Legumes have *Rhizobium* bacteria in their root nodules that fix nitrogen in the soil for the next year's grain crop.
- **Yield Potential (`yield_potential`):** Average `typical_yield_t_ha` divided by the max yield in our table (`12.0 t/ha`).
- **Drought Tolerance (`drought_tolerance`):** Average drought tolerance rating across the crops in the sequence.
- **Soil Compatibility (`soil_compatibility`):** Checks how closely each crop's preferred pH and clay ranges match the field, blended with how much root depths alternate from year to year (`root_depth_m`).
- **Crop Order and Monoculture Penalty (`sequence_transition_analysis`):** Checks every step in the cycle, including when the last year loops back to Year 1. Planting the exact same crop back to back (like `Alfalfa -> Corn -> Alfalfa` looping from Year 3 back to Year 1) or repeating the same `crop_type` lets crop-specific pests and soil diseases build up, so we multiply the final score by a `penalty_multiplier`.

### 3. Equipment Filters and Sequence Generation
- `filter_rotations_by_constraints`: Drops rotations that don't fit a farmer's equipment or water limits. Setting `row_crop_only=True` skips hay crops like `Alfalfa` (`C05`) when a farmer only has standard grain combine equipment.
- `generate_candidate_rotations`: Builds valid multi-year sequences from `mock_crops.csv` while skipping back-to-back identical crop types, rotations without a nitrogen fixer, or rotations with more than one zero-yield cover crop year.

### 4. Farmer Priority Profiles
We test 5 weight profiles (each adding up to `1.0`) for different farm goals:
1. **Balanced:** `20%` soil health, `20%` water stress, `15%` climate resilience, `15%` N-fixation, `15%` yield, `10%` drought tolerance, `5%` soil compatibility.
2. **Max Yield:** `40%` weight on yield potential.
3. **Water Conservation:** `35%` weight on water stress and `15%` on drought tolerance.
4. **Soil Health First:** `30%` weight on soil health and `25%` on nitrogen fixation.
5. **Climate Resilient:** `25%` weight on climate resilience and `20%` on water stress.

### 5. Multi-Key Sorting Order
Rotations are sorted from highest to lowest using three keys:
1. `total_score` (Primary)
2. `water_stress` (First tiebreaker, picks safer water use)
3. `nitrogen_fixation` (Second tiebreaker, picks better soil nitrogen recovery)

## How to Run the Test Script
From the repository root, run:

```bash
python data/sample_data_test.py
```

The script only uses built-in Python modules (`csv`, `itertools`, `math`, `statistics`, `sys`) so anyone on the team can run it on Windows, macOS, or Linux without setting up a venv first.

Test 5 runs 10 `assert` checks at the end of the script and crashes with an `AssertionError` if any check fails:
- All profile weights add up to `1.0`
- All sub-scores and total scores stay inside `[0.0, 1.0]`
- `water_stress`, `soil_health`, and `climate_res` all change across different rotations on the same field
- Dry fields penalize high-water rotations compared to low-water rotations
- The wrap-around monoculture penalty keeps `Alfalfa -> Corn -> Alfalfa` from winning the `Balanced` profile
- Changing the sequence order (`Soybean -> Cover Crop Mix -> Corn` vs `Corn -> Soybean -> Cover Crop Mix`) gives different scores
- Equipment filtering and dynamic sequence generation return valid rotations
- Output rankings are sorted properly and tiebreakers work in the right order
- Running the script twice gives the exact same ranking

## Current Test Results and Notes
- **Field Conditions Change the Top Pick:** On a healthy, well-watered field (`F003`), the `Balanced` profile picks `Soybean -> Cover Crop Mix -> Corn` (`0.6639`). On the dry, compacted, low-carbon field `F006`, `Balanced` switches to `Sorghum -> Soybean` (`0.4938`) to save water, while `Soil Health First` picks `Soybean -> Cover Crop Mix -> Corn` (`0.4682`) to rebuild organic carbon and loosen packed clay.
- **Wrap-Around Repeat Fix:** Before we added transition penalties, `Alfalfa -> Corn -> Alfalfa` ranked #1 on almost every profile because of its high yield and N-fixation numbers, even though Year 3 loops right back into Year 1 Alfalfa. With `sequence_transition_analysis` in place, it only wins `Max Yield` when forage crops are allowed, and gets filtered out completely when `row_crop_only=True` is turned on.
- **All Mock Columns Used:** Every column in `mock_crops.csv`, `mock_soil.csv`, and `mock_climate.csv` (`soil_building_score`, `root_depth_m`, `crop_type`, `sand_pct`, `avg_temp_c`, `total_precip_mm`, `year`, and `season`) is wired into the scoring math.
