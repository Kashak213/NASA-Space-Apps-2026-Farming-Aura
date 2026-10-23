"""
NASA Space Apps 2026 — "Field Shift: Adapting Farms with NASA Data"
==================================================================
Pre-Hackathon Algorithm Testing Script (stdlib-only version)

Uses ONLY Python standard library (csv, json, statistics) so it runs
in any Python 3.x environment without any installs.

The hackathon version will use pandas + scikit-learn (see requirements.txt).

ALGORITHM: Multi-Criteria Weighted Scoring for Crop Rotation Candidates

Formula:
  rotation_score = (
      w1 * soil_health_score      +  # Soil quality metric
      w2 * water_stress_score     +  # Field water supply vs. crop water demand
      w3 * climate_resilience     +  # Historical stability
      w4 * nitrogen_fixation      +  # Soil-building legume bonus
      w5 * yield_potential        +  # Expected productivity
      w6 * drought_tolerance      +  # Future climate risk hedge
      w7 * soil_compatibility        # Crop ↔ soil match
  )

Sorting Strategy:
  1. Primary:   total_score (descending)   — overall best fit
  2. Secondary: water_stress (descending)  — drought resilience tiebreak
  3. Tertiary:  nitrogen_fixation (desc)   — soil building tiebreak
"""

import csv
import math
import statistics
from pathlib import Path

BASE_DIR = Path(__file__).parent
SAMPLE_DIR = BASE_DIR / "sample"


# ─────────────────────────────────────────────────────────────────────────────
# 1. LOAD CSV DATA (stdlib only)
# ─────────────────────────────────────────────────────────────────────────────

def load_csv(filepath: Path) -> list[dict]:
    """Load a CSV file into a list of dicts with auto type conversion."""
    rows = []
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            converted = {}
            for k, v in row.items():
                try:
                    converted[k] = float(v)
                except ValueError:
                    converted[k] = v
            rows.append(converted)
    return rows


def load_all():
    soil = load_csv(SAMPLE_DIR / "mock_soil.csv")
    climate = load_csv(SAMPLE_DIR / "mock_climate.csv")
    crops = load_csv(SAMPLE_DIR / "mock_crops.csv")
    print(f"✅ Loaded: {len(soil)} fields, {len(climate)} climate records, {len(crops)} crop types")
    return soil, climate, crops


def get_field_soil(soil: list, field_id: str) -> dict:
    return next(r for r in soil if r["field_id"] == field_id)


def get_field_climate_agg(climate: list, field_id: str) -> dict:
    """Aggregate climate records for a field (mean across all seasons/years)."""
    field_rows = [r for r in climate if r["field_id"] == field_id]
    keys = [k for k in field_rows[0] if k not in ("field_id", "year", "season")]
    agg = {}
    for k in keys:
        vals = [r[k] for r in field_rows if isinstance(r[k], float)]
        agg[k] = statistics.mean(vals) if vals else 0.0
    return agg


def get_crop(crops: list, crop_id: str) -> dict:
    return next((c for c in crops if c["crop_id"] == crop_id), None)


# ─────────────────────────────────────────────────────────────────────────────
# 2. COMPONENT SCORE FUNCTIONS (all return float in [0, 1])
# ─────────────────────────────────────────────────────────────────────────────

def clip(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def soil_health_score(soil: dict) -> float:
    """
    Higher organic carbon (ideal 3-5%), optimal pH 6.0-7.0,
    lower bulk density, higher CEC = better.
    """
    oc = soil["organic_carbon_pct"]
    oc_score = clip((oc - 1.0) / 4.0, 0, 1)           # 1%→0, 5%→1

    ph = soil["ph"]
    ph_score = 1.0 - min(abs(ph - 6.5) / 2.0, 1.0)    # 6.5→1, far off→0

    bd = soil["bulk_density"]
    bd_score = clip((1.7 - bd) / 0.6, 0, 1)            # 1.1→1, 1.7→0

    cec = soil["cec"]
    cec_score = clip(cec / 40.0, 0, 1)                 # 40+→1

    return (oc_score + ph_score + bd_score + cec_score) / 4.0


def field_water_supply_score(climate: dict) -> float:
    """Field-level water availability. Low drought + high moisture = 1."""
    drought_score = 1.0 - clip(climate["drought_index"], 0, 1)
    moisture_score = clip(climate["soil_moisture_avg"] / 0.5, 0, 1)
    return (drought_score + moisture_score) / 2.0


def crop_water_demand_norm(crop: dict) -> float:
    """Normalize crop water demand: 150mm→0 (thrifty), 600mm→1 (thirsty)."""
    return clip((crop["water_demand_mm"] - 150) / 450.0, 0, 1)


def water_stress_score(supply: float, demand_norm: float) -> float:
    """
    Inverse of water stress risk for a crop on a field.
    Water shortfall (1 - supply) only hurts in proportion to crop demand:
    a wet field scores ~1 for any crop; a dry field penalizes thirsty crops.
    """
    return 1.0 - (1.0 - supply) * demand_norm


def climate_resilience_score(climate: dict) -> float:
    """Positive precip anomaly + high NDVI = more resilient baseline."""
    anomaly = climate["anomaly_precip_pct"]
    anomaly_score = clip((anomaly + 40) / 60.0, 0, 1)  # [-40, +20] → [0, 1]
    ndvi_score = clip(climate["ndvi_avg"] / 0.9, 0, 1)
    return (anomaly_score + ndvi_score) / 2.0


def soil_compatibility_score(soil: dict, crop: dict) -> float:
    """How well does this crop's optimal ranges fit this field's soil?"""
    ph = soil["ph"]
    ph_center = (crop["optimal_ph_max"] + crop["optimal_ph_min"]) / 2
    ph_half = (crop["optimal_ph_max"] - crop["optimal_ph_min"]) / 2 + 0.5
    ph_score = max(0, 1 - abs(ph - ph_center) / ph_half)

    clay = soil["clay_pct"]
    clay_center = (crop["optimal_clay_max"] + crop["optimal_clay_min"]) / 2
    clay_half = (crop["optimal_clay_max"] - crop["optimal_clay_min"]) / 2 + 5
    clay_score = max(0, 1 - abs(clay - clay_center) / clay_half)

    return (ph_score + clay_score) / 2.0


def yield_potential_score(crop: dict) -> float:
    """Normalize against max dataset yield (12 t/ha)."""
    return clip(crop["typical_yield_t_ha"] / 12.0, 0, 1)


# ─────────────────────────────────────────────────────────────────────────────
# 3. ROTATION SCORING
# ─────────────────────────────────────────────────────────────────────────────

def score_rotation(seq: list[str], soil: dict, climate_agg: dict,
                   crops: list, weights: dict) -> dict:
    """Score a crop rotation sequence for a given field."""
    crop_rows = [get_crop(crops, cid) for cid in seq]
    crop_rows = [c for c in crop_rows if c is not None]

    # Field-level scores: identical for every rotation on the same field
    s_health   = soil_health_score(soil)
    supply     = field_water_supply_score(climate_agg)
    c_res      = climate_resilience_score(climate_agg)

    # Rotation-level scores: depend on the crops in the sequence
    w_stress         = statistics.mean([water_stress_score(supply, crop_water_demand_norm(c))
                                        for c in crop_rows])

    n_fix_avg        = statistics.mean([c["nitrogen_fixation"] for c in crop_rows])
    drought_tol_avg  = statistics.mean([c["drought_tolerance"] for c in crop_rows])
    yield_avg        = statistics.mean([yield_potential_score(c) for c in crop_rows])
    soil_compat_avg  = statistics.mean([soil_compatibility_score(soil, c) for c in crop_rows])

    total = (
        weights["soil_health"]       * s_health
        + weights["water_stress"]    * w_stress
        + weights["climate_res"]     * c_res
        + weights["nitrogen_fix"]    * n_fix_avg
        + weights["yield"]           * yield_avg
        + weights["drought_tol"]     * drought_tol_avg
        + weights["soil_compat"]     * soil_compat_avg
    )

    return {
        "seq_ids":           " → ".join(seq),
        "total_score":       round(total, 4),
        "soil_health":       round(s_health, 3),
        "water_stress":      round(w_stress, 3),
        "climate_res":       round(c_res, 3),
        "nitrogen_fixation": round(n_fix_avg, 3),
        "yield_potential":   round(yield_avg, 3),
        "drought_tolerance": round(drought_tol_avg, 3),
        "soil_compatibility":round(soil_compat_avg, 3),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. MULTI-KEY SORT
# ─────────────────────────────────────────────────────────────────────────────

def sort_rotations(results: list[dict]) -> list[dict]:
    """
    Sort by:
      1. total_score      (desc) — primary
      2. water_stress     (desc) — tiebreak: drought resilience
      3. nitrogen_fixation(desc) — tiebreak: soil building
    """
    return sorted(
        results,
        key=lambda r: (r["total_score"], r["water_stress"], r["nitrogen_fixation"]),
        reverse=True
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. CANDIDATE ROTATIONS & PRIORITY PROFILES
# ─────────────────────────────────────────────────────────────────────────────

CANDIDATE_ROTATIONS = [
    ["C01", "C02"],               # Corn → Soybean
    ["C01", "C02", "C03"],        # Corn → Soybean → Winter Wheat
    ["C02", "C01", "C02"],        # Soybean-heavy
    ["C01", "C02", "C06"],        # + Cover crop
    ["C02", "C06", "C01"],        # Cover crop mid-rotation
    ["C12", "C01", "C02"],        # Clover → Corn → Soy
    ["C10", "C01", "C03"],        # Field Pea → Corn → Wheat
    ["C07", "C02"],               # Sorghum → Soy (low water)
    ["C07", "C10", "C01"],        # Sorghum → Pea → Corn
    ["C08", "C02", "C07"],        # Sunflower → Soy → Sorghum
    ["C05", "C01", "C05"],        # Alfalfa-heavy
    ["C06", "C02", "C11", "C01"], # Cover → Soy → Rye → Corn
]

PROFILES = {
    "Balanced": {
        "soil_health": 0.20, "water_stress": 0.20, "climate_res": 0.15,
        "nitrogen_fix": 0.15, "yield": 0.15, "drought_tol": 0.10, "soil_compat": 0.05
    },
    "Max Yield": {
        "soil_health": 0.10, "water_stress": 0.15, "climate_res": 0.10,
        "nitrogen_fix": 0.10, "yield": 0.40, "drought_tol": 0.10, "soil_compat": 0.05
    },
    "Water Conservation": {
        "soil_health": 0.10, "water_stress": 0.35, "climate_res": 0.15,
        "nitrogen_fix": 0.10, "yield": 0.10, "drought_tol": 0.15, "soil_compat": 0.05
    },
    "Soil Health First": {
        "soil_health": 0.30, "water_stress": 0.10, "climate_res": 0.10,
        "nitrogen_fix": 0.25, "yield": 0.10, "drought_tol": 0.10, "soil_compat": 0.05
    },
    "Climate Resilient": {
        "soil_health": 0.15, "water_stress": 0.20, "climate_res": 0.25,
        "nitrogen_fix": 0.10, "yield": 0.10, "drought_tol": 0.15, "soil_compat": 0.05
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# 6. TEST RUNNERS
# ─────────────────────────────────────────────────────────────────────────────

def seq_label(seq_ids_str: str, crops: list) -> str:
    """Convert 'C01 → C02' to 'Corn → Soybean'."""
    parts = seq_ids_str.split(" → ")
    names = []
    for cid in parts:
        c = get_crop(crops, cid.strip())
        names.append(c["crop_name"] if c else cid)
    return " → ".join(names)


def test_single_field(field_id: str, soil: list, climate: list, crops: list,
                      profile_name: str = "Balanced"):
    print(f"\n{'='*70}")
    print(f"  FIELD: {field_id}   |   PROFILE: {profile_name}")
    print(f"{'='*70}")

    s = get_field_soil(soil, field_id)
    c = get_field_climate_agg(climate, field_id)

    print(f"  Soil : OC={s['organic_carbon_pct']}%, pH={s['ph']}, "
          f"Clay={s['clay_pct']}%, BD={s['bulk_density']}")
    print(f"  Clim : Drought={c['drought_index']:.2f}, "
          f"NDVI={c['ndvi_avg']:.2f}, Moisture={c['soil_moisture_avg']:.2f}, "
          f"PrecipAnom={c['anomaly_precip_pct']:.1f}%")

    w = PROFILES[profile_name]
    results = [score_rotation(seq, s, c, crops, w) for seq in CANDIDATE_ROTATIONS]
    ranked = sort_rotations(results)

    print(f"\n   Top 5 Recommendations:")
    print(f"  {'Rank':<5} {'Crop Rotation Sequence':<38} {'Score':>6} {'Water':>7} {'N-Fix':>7} {'Yield':>7}")
    print(f"  {'─'*5} {'─'*38} {'─'*6} {'─'*7} {'─'*7} {'─'*7}")
    for i, r in enumerate(ranked[:5], 1):
        label = seq_label(r["seq_ids"], crops)[:37]
        print(f"  {i:<5} {label:<38} {r['total_score']:>6.4f} "
              f"{r['water_stress']:>7.3f} {r['nitrogen_fixation']:>7.3f} {r['yield_potential']:>7.3f}")
    return ranked


def test_cross_field(seq: list, soil: list, climate: list, crops: list,
                     profile_name: str = "Balanced"):
    label = seq_label(" → ".join(seq), crops)
    print(f"\n{'='*70}")
    print(f"  CROSS-FIELD: '{label}'   |   {profile_name}")
    print(f"{'='*70}")
    w = PROFILES[profile_name]
    results = []
    for s in soil:
        fid = s["field_id"]
        c = get_field_climate_agg(climate, fid)
        r = score_rotation(seq, s, c, crops, w)
        r["field_id"] = fid
        results.append(r)
    ranked = sorted(results, key=lambda r: r["total_score"], reverse=True)
    print(f"\n  {'Rank':<5} {'Field':<8} {'Score':>7} {'SoilH':>7} {'Water':>7} {'Climate':>8}")
    print(f"  {'─'*5} {'─'*8} {'─'*7} {'─'*7} {'─'*7} {'─'*8}")
    for i, r in enumerate(ranked, 1):
        print(f"  {i:<5} {r['field_id']:<8} {r['total_score']:>7.4f} "
              f"{r['soil_health']:>7.3f} {r['water_stress']:>7.3f} {r['climate_res']:>8.3f}")


def test_sensitivity(field_id: str, soil: list, climate: list, crops: list):
    print(f"\n{'='*70}")
    print(f"  SENSITIVITY TEST — Field {field_id} across all priority profiles")
    print(f"  (Same field, different farmer goals → different #1 pick)")
    print(f"{'='*70}")
    s = get_field_soil(soil, field_id)
    c = get_field_climate_agg(climate, field_id)

    print(f"\n  {'Profile':<22} {'#1 Recommended Rotation':<40} {'Score':>6}")
    print(f"  {'─'*22} {'─'*40} {'─'*6}")
    for pname, w in PROFILES.items():
        results = [score_rotation(seq, s, c, crops, w) for seq in CANDIDATE_ROTATIONS]
        ranked = sort_rotations(results)
        top = ranked[0]
        label = seq_label(top["seq_ids"], crops)[:39]
        print(f"  {pname:<22} {label:<40} {top['total_score']:>6.4f}")


# ─────────────────────────────────────────────────────────────────────────────
# 7. ASSERTION CHECKS (fail loudly instead of just printing)
# ─────────────────────────────────────────────────────────────────────────────

def run_assertions(soil: list, climate: list, crops: list) -> None:
    print(f"\n{'='*70}")
    print("  ASSERTION CHECKS")
    print(f"{'='*70}")

    # Every profile's weights must sum to 1 so total_score stays in [0, 1]
    for pname, w in PROFILES.items():
        assert math.isclose(sum(w.values()), 1.0), f"{pname} weights sum to {sum(w.values())}"
    print("  ✓ Profile weights each sum to 1.0")

    # Every component and total score is within [0, 1] for every field/profile/rotation
    score_keys = ("total_score", "soil_health", "water_stress", "climate_res",
                  "nitrogen_fixation", "yield_potential", "drought_tolerance",
                  "soil_compatibility")
    for s in soil:
        c = get_field_climate_agg(climate, s["field_id"])
        for pname, w in PROFILES.items():
            for seq in CANDIDATE_ROTATIONS:
                r = score_rotation(seq, s, c, crops, w)
                for k in score_keys:
                    assert 0.0 <= r[k] <= 1.0, f"{k}={r[k]} out of range ({s['field_id']}, {pname}, {seq})"
    print("  ✓ All scores within [0, 1]")

    # Water stress must differ between rotations on a dry field, otherwise
    # the secondary sort key can never break a tie
    dry = get_field_soil(soil, "F006")
    dry_c = get_field_climate_agg(climate, "F006")
    water_vals = {score_rotation(seq, dry, dry_c, crops, PROFILES["Balanced"])["water_stress"]
                  for seq in CANDIDATE_ROTATIONS}
    assert len(water_vals) > 1, "water_stress is constant across rotations"
    print(f"  ✓ water_stress varies across rotations on dry field F006 ({len(water_vals)} distinct values)")

    # Thirsty rotation should score worse on water than a thrifty one on a dry field
    thirsty = score_rotation(["C05", "C01", "C05"], dry, dry_c, crops, PROFILES["Balanced"])
    thrifty = score_rotation(["C07", "C02"], dry, dry_c, crops, PROFILES["Balanced"])
    assert thirsty["water_stress"] < thrifty["water_stress"], "dry field should penalize thirsty crops"
    print("  ✓ Dry field penalizes thirsty rotation (Alfalfa/Corn) vs. Sorghum/Soy")

    # Ranked output is non-increasing on total_score
    ranked = sort_rotations([score_rotation(seq, dry, dry_c, crops, PROFILES["Balanced"])
                             for seq in CANDIDATE_ROTATIONS])
    totals = [r["total_score"] for r in ranked]
    assert totals == sorted(totals, reverse=True), "ranking not sorted by total_score"
    print("  ✓ Ranking is sorted by total_score (descending)")

    # Tiebreakers: synthetic rows with equal totals resolve by water, then N-fix
    ties = [
        {"seq_ids": "A", "total_score": 0.5, "water_stress": 0.6, "nitrogen_fixation": 0.1},
        {"seq_ids": "B", "total_score": 0.5, "water_stress": 0.7, "nitrogen_fixation": 0.0},
        {"seq_ids": "C", "total_score": 0.5, "water_stress": 0.6, "nitrogen_fixation": 0.9},
        {"seq_ids": "D", "total_score": 0.6, "water_stress": 0.1, "nitrogen_fixation": 0.0},
    ]
    order = [r["seq_ids"] for r in sort_rotations(ties)]
    assert order == ["D", "B", "C", "A"], f"tiebreak order wrong: {order}"
    print("  ✓ Tiebreakers resolve: total → water_stress → nitrogen_fixation")

    # Deterministic: same inputs produce the same ranking
    again = sort_rotations([score_rotation(seq, dry, dry_c, crops, PROFILES["Balanced"])
                            for seq in CANDIDATE_ROTATIONS])
    assert [r["seq_ids"] for r in again] == [r["seq_ids"] for r in ranked], "ranking not deterministic"
    print("  ✓ Ranking is deterministic across runs")


# ─────────────────────────────────────────────────────────────────────────────
# 8. RUN ALL TESTS
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n  NASA Space Apps 2026 — Crop Rotation Algorithm Test Runner")
    print("    'Field Shift: Adapting Farms with NASA Data'")
    print("    Pre-hackathon algorithm validation with MOCK data only\n")

    soil, climate, crops = load_all()

    print("\n\n TEST 1 — Single Field Analysis (Balanced Profile)")
    test_single_field("F001", soil, climate, crops, "Balanced")   # average field
    test_single_field("F005", soil, climate, crops, "Balanced")   # high quality field
    test_single_field("F006", soil, climate, crops, "Balanced")   # stressed/degraded field

    print("\n\n TEST 2 — Priority Profile Comparison (Field F002)")
    for profile in PROFILES:
        test_single_field("F002", soil, climate, crops, profile)

    print("\n\n  TEST 3 — Cross-Field: Same Rotation Ranked Across All Fields")
    test_cross_field(["C01", "C02", "C03"], soil, climate, crops, "Balanced")
    test_cross_field(["C07", "C10", "C01"], soil, climate, crops, "Water Conservation")

    print("\n\n TEST 4 — Sensitivity: Priority Goals Change the Top Pick")
    test_sensitivity("F003", soil, climate, crops)   # good field
    test_sensitivity("F006", soil, climate, crops)   # stressed field

    print("\n\n TEST 5 — Assertion Checks")
    run_assertions(soil, climate, crops)

    print("\n\n All tests complete — all assertions passed.")
    print("   Algorithm validated on mock data. Ready to plug in live NASA APIs on Nov 14.")
