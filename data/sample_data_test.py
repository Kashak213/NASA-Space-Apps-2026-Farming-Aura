"""
NASA Space Apps 2026 - Field Shift: Adapting Farms with NASA Data
Pre-hackathon algorithm test script (stdlib only so nobody needs a venv to test math).

Scores crop rotations from 0.0 to 1.0 across 7 weighted factors, then applies
a penalty multiplier if a rotation repeats the same crop back to back or when
the end of the cycle loops back into Year 1.

  rotation_score = penalty_multiplier * (
      w1 * soil_health_score  +  # starting soil quality + root depth & organic matter build
      w2 * water_stress_score +  # field water supply vs crop water demand
      w3 * climate_resilience +  # rain/NDVI stability + mixing crop types
      w4 * nitrogen_fixation  +  # legume N fixation + bonus when legume comes before grain
      w5 * yield_potential    +  # avg crop yield scaled 0 to 1
      w6 * drought_tolerance  +  # how well the crops handle dry spells
      w7 * soil_compatibility    # pH/clay match + switching root depths
  )

Ties on total_score break on water_stress first, then nitrogen_fixation.
"""

import csv
import itertools
import math
import statistics
import sys
from pathlib import Path

# stop Windows terminals from crashing on arrow characters
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).parent
SAMPLE_DIR = BASE_DIR / "sample"


# --- csv loading & climate stats ---

def load_csv(filepath: Path) -> list[dict]:
    """Load CSV rows as dicts and cast number strings to floats."""
    rows = []
    with open(filepath, newline="", encoding="utf-8") as f:
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
    print(f"[OK] Loaded {len(soil)} fields, {len(climate)} climate rows, and {len(crops)} crops")
    return soil, climate, crops


def get_field_soil(soil: list, field_id: str) -> dict:
    return next(r for r in soil if r["field_id"] == field_id)


def get_field_climate_agg(climate: list, field_id: str) -> dict:
    """Summarize field climate, splitting spring/summer and 2023->2024 trends."""
    field_rows = [r for r in climate if r["field_id"] == field_id]
    keys = [k for k in field_rows[0] if k not in ("field_id", "year", "season")]
    agg = {}
    for k in keys:
        vals = [r[k] for r in field_rows if isinstance(r[k], float)]
        agg[k] = statistics.mean(vals) if vals else 0.0

    # split spring and summer since mid-summer heat and rain matter most for row crops
    spring_rows = [r for r in field_rows if r.get("season") == "spring"]
    summer_rows = [r for r in field_rows if r.get("season") == "summer"]

    agg["spring_precip_mm"] = (
        statistics.mean([r["total_precip_mm"] for r in spring_rows])
        if spring_rows else agg["total_precip_mm"]
    )
    agg["summer_precip_mm"] = (
        statistics.mean([r["total_precip_mm"] for r in summer_rows])
        if summer_rows else agg["total_precip_mm"]
    )
    agg["annual_precip_mm"] = agg["spring_precip_mm"] + agg["summer_precip_mm"]
    agg["summer_temp_c"] = (
        statistics.mean([r["avg_temp_c"] for r in summer_rows])
        if summer_rows else agg["avg_temp_c"]
    )
    agg["summer_drought"] = (
        statistics.mean([r["drought_index"] for r in summer_rows])
        if summer_rows else agg["drought_index"]
    )

    # compare 2023 to 2024 to see if drought or NDVI is getting worse
    years = sorted({int(r["year"]) for r in field_rows if isinstance(r.get("year"), (int, float))})
    if len(years) >= 2:
        y_prev, y_curr = years[-2], years[-1]
        prev_rows = [r for r in field_rows if int(r["year"]) == y_prev]
        curr_rows = [r for r in field_rows if int(r["year"]) == y_curr]

        drought_prev = statistics.mean([r["drought_index"] for r in prev_rows])
        drought_curr = statistics.mean([r["drought_index"] for r in curr_rows])
        agg["drought_trend"] = drought_curr - drought_prev  # > 0 means drying out

        anom_prev = statistics.mean([r["anomaly_precip_pct"] for r in prev_rows])
        anom_curr = statistics.mean([r["anomaly_precip_pct"] for r in curr_rows])
        agg["precip_anom_trend"] = anom_curr - anom_prev    # < 0 means rain dropping

        ndvi_prev = statistics.mean([r["ndvi_avg"] for r in prev_rows])
        ndvi_curr = statistics.mean([r["ndvi_avg"] for r in curr_rows])
        agg["ndvi_trend"] = ndvi_curr - ndvi_prev            # < 0 means less green cover
    else:
        agg["drought_trend"] = 0.0
        agg["precip_anom_trend"] = 0.0
        agg["ndvi_trend"] = 0.0

    return agg


def get_crop(crops: list, crop_id: str) -> dict:
    return next((c for c in crops if c["crop_id"] == crop_id), None)


# --- sub-score functions (all return 0.0 to 1.0) ---

def clip(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def field_soil_baseline_score(soil: dict) -> float:
    """Score starting soil health from organic carbon, pH, bulk density, CEC, and sand/clay."""
    oc = soil["organic_carbon_pct"]
    oc_score = clip((oc - 1.0) / 4.0, 0, 1)  # 1% -> 0, 5% -> 1

    ph = soil["ph"]
    ph_score = 1.0 - min(abs(ph - 6.5) / 2.0, 1.0)  # 6.5 is sweet spot for most crops

    bd = soil["bulk_density"]
    bd_score = clip((1.7 - bd) / 0.6, 0, 1)  # lower bulk density = less packed soil

    cec = soil["cec"]
    cec_score = clip(cec / 40.0, 0, 1)  # higher CEC holds onto nutrients better

    # balanced loam is roughly 40% sand and 25% clay
    sand = soil.get("sand_pct", 40.0)
    clay = soil.get("clay_pct", 25.0)
    texture_score = 1.0 - clip((abs(sand - 40.0) + abs(clay - 25.0)) / 60.0, 0, 1)

    return (
        0.25 * oc_score
        + 0.20 * ph_score
        + 0.25 * bd_score
        + 0.15 * cec_score
        + 0.15 * texture_score
    )


def soil_health_score(soil: dict, crop_rows: list[dict] | None = None) -> float:
    """Blend starting soil score with how much the rotation builds organic matter and breaks compaction."""
    s_base = field_soil_baseline_score(soil)
    if not crop_rows:
        return s_base

    # if bulk density is high (>1.35), deep roots matter more to break up packed clay
    compaction_need = clip((soil["bulk_density"] - 1.15) / 0.45, 0.2, 1.0)
    regen_scores = []
    for c in crop_rows:
        build = c.get("soil_building_score", 0.5)
        root_norm = clip(c.get("root_depth_m", 1.0) / 2.5, 0, 1)
        regen_scores.append(
            0.65 * build + 0.35 * (root_norm * compaction_need + build * (1.0 - compaction_need))
        )

    regen_avg = statistics.mean(regen_scores)
    return clip(0.65 * s_base + 0.35 * regen_avg, 0.0, 1.0)


def field_water_supply_score(climate: dict) -> float:
    """Estimate water supply from drought index, SMAP soil moisture, and 2023->2024 drought trend."""
    drought_score = 1.0 - clip(climate["drought_index"], 0, 1)
    moisture_score = clip(climate["soil_moisture_avg"] / 0.5, 0, 1)
    trend_penalty = clip(climate.get("drought_trend", 0.0) * 1.2, 0.0, 0.20)
    return clip((drought_score + moisture_score) / 2.0 - trend_penalty, 0.0, 1.0)


def crop_water_demand_norm(crop: dict) -> float:
    """Scale water demand from 0.0 (150mm low use) to 1.0 (600mm thirsty crop)."""
    return clip((crop["water_demand_mm"] - 150) / 450.0, 0, 1)


def water_stress_score(supply: float, demand_norm: float,
                       annual_precip_mm: float | None = None,
                       crop_demand_mm: float | None = None) -> float:
    """Compare field water supply and yearly rain against how much water the crop needs."""
    base_stress = 1.0 - (1.0 - supply) * demand_norm
    if annual_precip_mm is None or crop_demand_mm is None:
        return clip(base_stress, 0.0, 1.0)

    # check if annual rain covers crop demand plus a 15% buffer for runoff/evaporation
    precip_adequacy = clip(annual_precip_mm / max(crop_demand_mm * 1.15, 1.0), 0.0, 1.0)
    return clip(0.75 * base_stress + 0.25 * precip_adequacy, 0.0, 1.0)


def climate_resilience_score(climate: dict, crop_rows: list[dict] | None = None) -> float:
    """Score weather stability from rain anomalies, NDVI, heat stress, and crop group mix."""
    anomaly = climate["anomaly_precip_pct"]
    anomaly_score = clip((anomaly + 40) / 60.0, 0, 1)  # maps [-40%, +20%] to [0, 1]
    ndvi_score = clip(climate["ndvi_avg"] / 0.9, 0, 1)

    anom_trend_penalty = clip(-climate.get("precip_anom_trend", 0.0) / 40.0, 0.0, 0.25)
    summer_heat_penalty = clip((climate.get("summer_temp_c", 24.0) - 24.5) / 8.0, 0.0, 0.15)
    c_base = clip(
        (anomaly_score + ndvi_score) / 2.0 - 0.5 * (anom_trend_penalty + summer_heat_penalty),
        0.0,
        1.0,
    )

    if not crop_rows:
        return c_base

    # mixing different crop families (grain, legume, cover) buffers against bad weather years
    unique_types = len({c.get("crop_type", "") for c in crop_rows})
    diversity_score = clip(unique_types / min(len(crop_rows), 3), 0.0, 1.0)
    drought_hedge = statistics.mean([c["drought_tolerance"] for c in crop_rows])
    c_buffer = 0.55 * diversity_score + 0.45 * drought_hedge

    return clip(0.65 * c_base + 0.35 * c_buffer, 0.0, 1.0)


def soil_compatibility_score(soil: dict, crop: dict) -> float:
    """Check how well a crop's preferred pH and clay ranges match the field."""
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
    """Divide typical yield by max yield in our table (12 t/ha)."""
    return clip(crop["typical_yield_t_ha"] / 12.0, 0, 1)


def sequence_transition_analysis(crop_rows: list[dict], soil: dict) -> dict:
    """
    Check year-to-year crop transitions (including wrap-around from last year back to Year 1).
    Penalizes repeating the same crop/family (pest & disease buildup) and rewards planting
    a nitrogen-fixing legume before a grain crop or alternating root depths.
    """
    n = len(crop_rows)
    if n == 0:
        return {"transition_score": 0.0, "n_carryover_bonus": 0.0, "penalty_multiplier": 1.0}
    if n == 1:
        return {"transition_score": 0.3, "n_carryover_bonus": 0.0, "penalty_multiplier": 0.75}

    repeat_crop_count = 0
    same_type_count = 0
    n_bonus_total = 0.0
    root_alt_total = 0.0

    for i in range(n):
        curr = crop_rows[i]
        nxt = crop_rows[(i + 1) % n]
        # slightly higher weight on earlier years in the cycle
        step_weight = 1.0 - 0.06 * i

        if curr["crop_id"] == nxt["crop_id"]:
            repeat_crop_count += 1
        elif curr.get("crop_type") == nxt.get("crop_type"):
            same_type_count += 1

        # legume root nodules leave extra soil N for the next year's grain crop
        if curr["nitrogen_fixation"] >= 0.5 and nxt["nitrogen_fixation"] == 0.0:
            demand_weight = clip(nxt["typical_yield_t_ha"] / 10.5, 0.3, 1.0)
            n_bonus_total += curr["nitrogen_fixation"] * demand_weight * step_weight

        # switching shallow and deep roots pulls from different soil layers
        root_diff = abs(curr.get("root_depth_m", 1.0) - nxt.get("root_depth_m", 1.0))
        root_alt_total += clip(root_diff / 1.5, 0.0, 1.0) * step_weight

    # starting Year 1 with a legume/cover crop helps more when field organic carbon is low
    first_crop = crop_rows[0]
    oc_deficit = clip((3.0 - soil["organic_carbon_pct"]) / 2.0, 0.0, 1.0)
    year1_readiness = (
        0.04 * (first_crop["nitrogen_fixation"] + first_crop.get("soil_building_score", 0.5))
        * (0.5 + 0.5 * oc_deficit)
    )

    n_carryover_bonus = clip(n_bonus_total / n + year1_readiness, 0.0, 0.25)
    root_alt_score = clip(root_alt_total / n, 0.0, 1.0)

    repeat_ratio = repeat_crop_count / n
    same_type_ratio = same_type_count / n
    penalty_multiplier = clip(1.0 - 0.35 * repeat_ratio - 0.08 * same_type_ratio, 0.65, 1.0)

    transition_score = clip(
        (0.50 * root_alt_score + 0.50 * clip(n_bonus_total / max(n * 0.5, 1.0), 0.0, 1.0))
        * penalty_multiplier,
        0.0,
        1.0,
    )

    return {
        "transition_score": transition_score,
        "n_carryover_bonus": n_carryover_bonus,
        "penalty_multiplier": penalty_multiplier,
        "repeat_crop_count": repeat_crop_count,
    }


# --- rotation scoring & constraint filters ---

def score_rotation(seq: list[str], soil: dict, climate_agg: dict,
                   crops: list, weights: dict) -> dict:
    """Compute sub-scores and weighted total score for a candidate rotation."""
    crop_rows = [get_crop(crops, cid) for cid in seq]
    crop_rows = [c for c in crop_rows if c is not None]

    trans = sequence_transition_analysis(crop_rows, soil)

    s_health = soil_health_score(soil, crop_rows)
    supply = field_water_supply_score(climate_agg)
    c_res = climate_resilience_score(climate_agg, crop_rows)

    annual_precip = climate_agg.get("annual_precip_mm")
    w_stress = statistics.mean([
        water_stress_score(supply, crop_water_demand_norm(c), annual_precip, c["water_demand_mm"])
        for c in crop_rows
    ])

    # add legume-to-grain nitrogen carry-over bonus
    n_fix_raw = statistics.mean([c["nitrogen_fixation"] for c in crop_rows])
    n_fix_avg = clip(0.85 * n_fix_raw + 0.60 * trans["n_carryover_bonus"], 0.0, 1.0)

    drought_tol_avg = statistics.mean([c["drought_tolerance"] for c in crop_rows])
    yield_avg = statistics.mean([yield_potential_score(c) for c in crop_rows])

    base_compat = statistics.mean([soil_compatibility_score(soil, c) for c in crop_rows])
    soil_compat_avg = clip(0.80 * base_compat + 0.20 * trans["transition_score"], 0.0, 1.0)

    raw_total = (
        weights["soil_health"] * s_health
        + weights["water_stress"] * w_stress
        + weights["climate_res"] * c_res
        + weights["nitrogen_fix"] * n_fix_avg
        + weights["yield"] * yield_avg
        + weights["drought_tol"] * drought_tol_avg
        + weights["soil_compat"] * soil_compat_avg
    )

    total = clip(raw_total * trans["penalty_multiplier"], 0.0, 1.0)

    return {
        "seq_ids": " → ".join(seq),
        "total_score": round(total, 4),
        "soil_health": round(s_health, 3),
        "water_stress": round(w_stress, 3),
        "climate_res": round(c_res, 3),
        "nitrogen_fixation": round(n_fix_avg, 3),
        "yield_potential": round(yield_avg, 3),
        "drought_tolerance": round(drought_tol_avg, 3),
        "soil_compatibility": round(soil_compat_avg, 3),
        "transition_score": round(trans["transition_score"], 3),
    }


def filter_rotations_by_constraints(
    rotations: list[list[str]],
    crops: list[dict],
    row_crop_only: bool = False,
    max_water_demand_mm: float | None = None,
    excluded_crop_ids: set[str] | None = None,
) -> list[list[str]]:
    """
    Drop rotations that don't fit equipment or water limits.
    row_crop_only=True skips Alfalfa (C05) since hay takes balers/mowers instead of a grain combine.
    """
    excluded = set(excluded_crop_ids or set())
    if row_crop_only:
        excluded.add("C05")

    valid = []
    for seq in rotations:
        if any(cid in excluded for cid in seq):
            continue
        if max_water_demand_mm is not None:
            crop_objs = [get_crop(crops, cid) for cid in seq]
            if any(c and c["water_demand_mm"] > max_water_demand_mm for c in crop_objs):
                continue
        valid.append(seq)
    return valid


def generate_candidate_rotations(
    crops: list[dict],
    length: int = 3,
    row_crop_only: bool = True,
    max_water_demand_mm: float | None = None,
) -> list[list[str]]:
    """Build valid N-year sequences while skipping back-to-back crop types or zero-cash-crop combos."""
    usable_crops = [
        c for c in crops
        if (not row_crop_only or c["crop_id"] != "C05")
        and (max_water_demand_mm is None or c["water_demand_mm"] <= max_water_demand_mm)
    ]
    crop_ids = [c["crop_id"] for c in usable_crops]
    crop_map = {c["crop_id"]: c for c in usable_crops}

    generated = []
    for combo in itertools.product(crop_ids, repeat=length):
        # skip back-to-back repeats (including wrap-around from end back to start)
        if any(combo[i] == combo[(i + 1) % length] for i in range(length)):
            continue
        if any(crop_map[combo[i]]["crop_type"] == crop_map[combo[(i + 1) % length]]["crop_type"]
               for i in range(length)):
            continue

        c_objs = [crop_map[cid] for cid in combo]
        # need at least one nitrogen fixer/cover crop and at least one grain/oilseed cash crop
        if not any(c["nitrogen_fixation"] >= 0.5 or c["crop_type"] == "cover" for c in c_objs):
            continue
        if not any(c["crop_type"] in ("grain", "oilseed") for c in c_objs):
            continue
        # max 1 pure cover crop (0 yield) so the farm still makes money most years
        if sum(1 for c in c_objs if c["typical_yield_t_ha"] == 0.0) > 1:
            continue

        generated.append(list(combo))

    return generated


# --- sorting & preset profiles ---

def sort_rotations(results: list[dict]) -> list[dict]:
    """Sort by total_score desc, breaking ties with water_stress then nitrogen_fixation."""
    return sorted(
        results,
        key=lambda r: (r["total_score"], r["water_stress"], r["nitrogen_fixation"]),
        reverse=True,
    )


CANDIDATE_ROTATIONS = [
    ["C01", "C02"],               # Corn -> Soybean
    ["C01", "C02", "C03"],        # Corn -> Soybean -> Winter Wheat
    ["C02", "C01", "C02"],        # Soybean-heavy (repeats Soy on wrap-around)
    ["C01", "C02", "C06"],        # Corn -> Soy -> Cover crop
    ["C02", "C06", "C01"],        # Soy -> Cover crop -> Corn
    ["C12", "C01", "C02"],        # Clover -> Corn -> Soy
    ["C10", "C01", "C03"],        # Field Pea -> Corn -> Wheat
    ["C07", "C02"],               # Sorghum -> Soy (dry fields)
    ["C07", "C10", "C01"],        # Sorghum -> Pea -> Corn
    ["C08", "C02", "C07"],        # Sunflower -> Soy -> Sorghum
    ["C05", "C01", "C05"],        # Alfalfa -> Corn -> Alfalfa (repeats Alfalfa on wrap-around)
    ["C06", "C02", "C11", "C01"], # Cover -> Soy -> Rye -> Corn
]

PROFILES = {
    "Balanced": {
        "soil_health": 0.20, "water_stress": 0.20, "climate_res": 0.15,
        "nitrogen_fix": 0.15, "yield": 0.15, "drought_tol": 0.10, "soil_compat": 0.05,
    },
    "Max Yield": {
        "soil_health": 0.10, "water_stress": 0.15, "climate_res": 0.10,
        "nitrogen_fix": 0.10, "yield": 0.40, "drought_tol": 0.10, "soil_compat": 0.05,
    },
    "Water Conservation": {
        "soil_health": 0.10, "water_stress": 0.35, "climate_res": 0.15,
        "nitrogen_fix": 0.10, "yield": 0.10, "drought_tol": 0.15, "soil_compat": 0.05,
    },
    "Soil Health First": {
        "soil_health": 0.30, "water_stress": 0.10, "climate_res": 0.10,
        "nitrogen_fix": 0.25, "yield": 0.10, "drought_tol": 0.10, "soil_compat": 0.05,
    },
    "Climate Resilient": {
        "soil_health": 0.15, "water_stress": 0.20, "climate_res": 0.25,
        "nitrogen_fix": 0.10, "yield": 0.10, "drought_tol": 0.15, "soil_compat": 0.05,
    },
}


# --- console test runners ---

def seq_label(seq_ids_str: str, crops: list) -> str:
    """Convert 'C01 -> C02' into 'Corn -> Soybean'."""
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
          f"Clay={s['clay_pct']}%, Sand={s['sand_pct']}%, BD={s['bulk_density']}")
    print(f"  Clim : Drought={c['drought_index']:.2f} (Trend={c['drought_trend']:+.2f}), "
          f"AnnualPrecip={c['annual_precip_mm']:.0f}mm, NDVI={c['ndvi_avg']:.2f}, "
          f"PrecipAnom={c['anomaly_precip_pct']:.1f}%")

    w = PROFILES[profile_name]
    results = [score_rotation(seq, s, c, crops, w) for seq in CANDIDATE_ROTATIONS]
    ranked = sort_rotations(results)

    print("\n   Top 5 Recommendations:")
    print(f"  {'Rank':<5} {'Crop Rotation Sequence':<38} {'Score':>6} {'SoilH':>6} {'Water':>6} {'N-Fix':>6} {'Trans':>6}")
    print(f"  {'-'*5} {'-'*38} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*6}")
    for i, r in enumerate(ranked[:5], 1):
        label = seq_label(r["seq_ids"], crops)[:37]
        print(f"  {i:<5} {label:<38} {r['total_score']:>6.4f} "
              f"{r['soil_health']:>6.3f} {r['water_stress']:>6.3f} "
              f"{r['nitrogen_fixation']:>6.3f} {r['transition_score']:>6.3f}")
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
    print(f"  {'-'*5} {'-'*8} {'-'*7} {'-'*7} {'-'*7} {'-'*8}")
    for i, r in enumerate(ranked, 1):
        print(f"  {i:<5} {r['field_id']:<8} {r['total_score']:>7.4f} "
              f"{r['soil_health']:>7.3f} {r['water_stress']:>7.3f} {r['climate_res']:>8.3f}")


def test_sensitivity(field_id: str, soil: list, climate: list, crops: list):
    print(f"\n{'='*70}")
    print(f"  SENSITIVITY TEST - Field {field_id} across all priority profiles")
    print("  (Same field, different farmer goals -> different #1 pick)")
    print(f"{'='*70}")
    s = get_field_soil(soil, field_id)
    c = get_field_climate_agg(climate, field_id)

    print(f"\n  {'Profile':<22} {'#1 Recommended Rotation':<40} {'Score':>6}")
    print(f"  {'-'*22} {'-'*40} {'-'*6}")
    for pname, w in PROFILES.items():
        results = [score_rotation(seq, s, c, crops, w) for seq in CANDIDATE_ROTATIONS]
        ranked = sort_rotations(results)
        top = ranked[0]
        label = seq_label(top["seq_ids"], crops)[:39]
        print(f"  {pname:<22} {label:<40} {top['total_score']:>6.4f}")


# --- assertion checks ---

def run_assertions(soil: list, climate: list, crops: list) -> None:
    print(f"\n{'='*70}")
    print("  ASSERTION CHECKS")
    print(f"{'='*70}")

    # profile weights have to add up to 1.0 so final score stays in [0, 1]
    for pname, w in PROFILES.items():
        assert math.isclose(sum(w.values()), 1.0), f"{pname} weights sum to {sum(w.values())}"
    print("  [PASS] Profile weights each sum to 1.0")

    # every sub-score and total score must stay between 0.0 and 1.0
    score_keys = ("total_score", "soil_health", "water_stress", "climate_res",
                  "nitrogen_fixation", "yield_potential", "drought_tolerance",
                  "soil_compatibility", "transition_score")
    for s in soil:
        c = get_field_climate_agg(climate, s["field_id"])
        for pname, w in PROFILES.items():
            for seq in CANDIDATE_ROTATIONS:
                r = score_rotation(seq, s, c, crops, w)
                for k in score_keys:
                    assert 0.0 <= r[k] <= 1.0, f"{k}={r[k]} out of range ({s['field_id']}, {pname}, {seq})"
    print("  [PASS] All component and total scores stay within [0, 1]")

    # water stress, soil health, and climate resilience should all change depending on the crops
    dry = get_field_soil(soil, "F006")
    dry_c = get_field_climate_agg(climate, "F006")
    water_vals = {score_rotation(seq, dry, dry_c, crops, PROFILES["Balanced"])["water_stress"]
                  for seq in CANDIDATE_ROTATIONS}
    soil_vals = {score_rotation(seq, dry, dry_c, crops, PROFILES["Balanced"])["soil_health"]
                 for seq in CANDIDATE_ROTATIONS}
    clim_vals = {score_rotation(seq, dry, dry_c, crops, PROFILES["Balanced"])["climate_res"]
                 for seq in CANDIDATE_ROTATIONS}
    assert len(water_vals) > 1, "water_stress is constant across rotations"
    assert len(soil_vals) > 1, "soil_health is constant across rotations"
    assert len(clim_vals) > 1, "climate_res is constant across rotations"
    print(f"  [PASS] Sub-scores change across rotations on F006 "
          f"(water={len(water_vals)}, soil={len(soil_vals)}, climate={len(clim_vals)} values)")

    # thirsty crops should score worse on water stress than low-water crops on a dry field
    thirsty = score_rotation(["C05", "C01", "C05"], dry, dry_c, crops, PROFILES["Balanced"])
    thrifty = score_rotation(["C07", "C02"], dry, dry_c, crops, PROFILES["Balanced"])
    assert thirsty["water_stress"] < thrifty["water_stress"], "dry field should penalize high-water crops"
    print("  [PASS] Dry field penalizes high-water rotation (Alfalfa/Corn) vs Sorghum/Soy")

    # repeating Alfalfa on wrap-around (C05->C01->C05) gets penalized enough not to win Balanced
    f1 = get_field_soil(soil, "F001")
    f1_c = get_field_climate_agg(climate, "F001")
    top_balanced = sort_rotations([score_rotation(seq, f1, f1_c, crops, PROFILES["Balanced"])
                                   for seq in CANDIDATE_ROTATIONS])[0]
    assert top_balanced["seq_ids"] != "C05 → C01 → C05", (
        f"Wrap-around repeat C05->C01->C05 should not rank #1 on Balanced (got {top_balanced['seq_ids']})"
    )
    print(f"  [PASS] Wrap-around repeat penalty keeps C05->C01->C05 from winning Balanced (#1: {top_balanced['seq_ids']})")

    # crop order matters: Soy -> Cover -> Corn scores differently than Corn -> Soy -> Cover
    r_order_a = score_rotation(["C01", "C02", "C06"], dry, dry_c, crops, PROFILES["Balanced"])
    r_order_b = score_rotation(["C02", "C06", "C01"], dry, dry_c, crops, PROFILES["Balanced"])
    assert r_order_a["total_score"] != r_order_b["total_score"], (
        "Sequence order should differentiate C01->C02->C06 from C02->C06->C01"
    )
    print(f"  [PASS] Sequence order changes score ({r_order_a['total_score']} vs {r_order_b['total_score']})")

    # equipment filter and sequence generator work and respect constraints
    row_only = filter_rotations_by_constraints(CANDIDATE_ROTATIONS, crops, row_crop_only=True)
    assert all("C05" not in seq for seq in row_only), "row_crop_only failed to filter C05"
    generated = generate_candidate_rotations(crops, length=3, row_crop_only=True, max_water_demand_mm=450)
    assert len(generated) > 0, "generator returned no rotations"
    assert all("C05" not in seq for seq in generated), "generator included excluded C05"
    print(f"  [PASS] Equipment filter and generator produced {len(generated)} valid 3-year sequences")

    # output list is sorted from highest total_score to lowest
    ranked = sort_rotations([score_rotation(seq, dry, dry_c, crops, PROFILES["Balanced"])
                             for seq in CANDIDATE_ROTATIONS])
    totals = [r["total_score"] for r in ranked]
    assert totals == sorted(totals, reverse=True), "ranking not sorted by total_score"
    print("  [PASS] Ranking is sorted by total_score (descending)")

    # tiebreakers sort by water_stress second and nitrogen_fixation third
    ties = [
        {"seq_ids": "A", "total_score": 0.5, "water_stress": 0.6, "nitrogen_fixation": 0.1},
        {"seq_ids": "B", "total_score": 0.5, "water_stress": 0.7, "nitrogen_fixation": 0.0},
        {"seq_ids": "C", "total_score": 0.5, "water_stress": 0.6, "nitrogen_fixation": 0.9},
        {"seq_ids": "D", "total_score": 0.6, "water_stress": 0.1, "nitrogen_fixation": 0.0},
    ]
    order = [r["seq_ids"] for r in sort_rotations(ties)]
    assert order == ["D", "B", "C", "A"], f"tiebreak order wrong: {order}"
    print("  [PASS] Tiebreakers sort by total_score -> water_stress -> nitrogen_fixation")

    # running the same inputs twice gives the exact same order
    again = sort_rotations([score_rotation(seq, dry, dry_c, crops, PROFILES["Balanced"])
                            for seq in CANDIDATE_ROTATIONS])
    assert [r["seq_ids"] for r in again] == [r["seq_ids"] for r in ranked], "ranking not deterministic"
    print("  [PASS] Ranking is deterministic across runs")


if __name__ == "__main__":
    print("\n  NASA Space Apps 2026 - Crop Rotation Algorithm Test Runner")
    print("  Challenge: Field Shift: Adapting Farms with NASA Data")
    print("  Pre-hackathon math and mock data check\n")

    soil, climate, crops = load_all()

    print("\n\n TEST 1 - Single Field Analysis (Balanced Profile)")
    test_single_field("F001", soil, climate, crops, "Balanced")   # average field
    test_single_field("F005", soil, climate, crops, "Balanced")   # healthy field
    test_single_field("F006", soil, climate, crops, "Balanced")   # dry, degraded field

    print("\n\n TEST 2 - Priority Profile Comparison (Field F002)")
    for profile in PROFILES:
        test_single_field("F002", soil, climate, crops, profile)

    print("\n\n TEST 3 - Cross-Field: Same Rotation Ranked Across All Fields")
    test_cross_field(["C01", "C02", "C03"], soil, climate, crops, "Balanced")
    test_cross_field(["C07", "C10", "C01"], soil, climate, crops, "Water Conservation")

    print("\n\n TEST 4 - Sensitivity: Priority Goals Change the Top Pick")
    test_sensitivity("F003", soil, climate, crops)   # healthy field
    test_sensitivity("F006", soil, climate, crops)   # stressed field

    print("\n\n TEST 5 - Assertion Checks")
    run_assertions(soil, climate, crops)

    print("\n\n All tests finished and all assertions passed.")
    print(" Ready to connect live NASA datasets on Nov 14.")
