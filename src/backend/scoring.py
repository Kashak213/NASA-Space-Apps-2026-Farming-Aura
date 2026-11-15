"""
Crop rotation scoring for the Farming Aura backend.
This is the same math the dashboard runs in app.js, moved into Python so the server is the source of truth.
Crop traits and field soil numbers are read from data/crops.json and data/ny_regions.json.
"""

import json
from functools import cmp_to_key
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

_crop_file = json.loads((DATA_DIR / "crops.json").read_text(encoding="utf-8"))
_region_file = json.loads((DATA_DIR / "ny_regions.json").read_text(encoding="utf-8"))

CROPS = _crop_file["crops"]
CANDIDATE_SEQUENCES = _crop_file["candidate_sequences"]
PRIORITY_PROFILES = _crop_file["priority_profiles"]
FIELDS = _region_file["fields"]
CITIES = _region_file["cities"]

# crops grouped the same way the dashboard groups them when it has to suggest partners
PERENNIAL_PARTNERS = ["C04", "C05", "C06", "C07", "C08"]
LEGUMES = ["C03", "C01", "C12"]
CASH_CROPS = ["C02", "C11", "C13", "C09", "C10"]


def clip(val, lo, hi):
    return max(lo, min(hi, val))


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def field_baseline_soil(field):
    """Score the field's starting soil from organic carbon, pH, bulk density, CEC and texture."""
    oc_score = clip((field["oc"] - 1.0) / 4.0, 0, 1)
    ph_score = 1.0 - min(abs(field["ph"] - 6.5) / 2.0, 1.0)
    bd_score = clip((1.7 - field["bd"]) / 0.6, 0, 1)
    cec_score = clip(field["cec"] / 40.0, 0, 1)
    texture_score = 1.0 - clip((abs(field["sand"] - 40.0) + abs(field["clay"] - 25.0)) / 60.0, 0, 1)
    return 0.25 * oc_score + 0.20 * ph_score + 0.25 * bd_score + 0.15 * cec_score + 0.15 * texture_score


def profile_weights(profile_name, intensity):
    """Blend the Balanced weights toward the chosen profile, stronger as the intensity slider goes up."""
    base = PRIORITY_PROFILES["Balanced"]
    target = PRIORITY_PROFILES.get(profile_name, base)
    intensity_norm = clip((intensity - 1) / 99, 0, 1)
    # 50 on the slider lands close to the profile's normal weights
    power_scale = 0.25 + intensity_norm * 1.75
    raw = {k: base[k] + (target[k] - base[k]) * power_scale for k in base}
    weight_sum = sum(max(0.01, v) for v in raw.values())
    return {k: max(0.01, v) / weight_sum for k, v in raw.items()}


def score_sequence(seq_ids, field, profile_name="Balanced", intensity=50, dry_probe=False):
    """Score one rotation (a list of crop ids in planting order) on one field."""
    crops = [CROPS[cid] for cid in seq_ids if cid in CROPS]
    n = len(crops)
    s_base = field_baseline_soil(field)
    # compacted soil (high bulk density) gets more out of deep roots
    compaction_need = clip((field["bd"] - 1.15) / 0.45, 0.2, 1.0)

    regen_scores = []
    for c in crops:
        root_norm = clip(c["rootM"] / 2.5, 0, 1)
        regen_scores.append(
            0.65 * c["build"] + 0.35 * (root_norm * compaction_need + c["build"] * (1.0 - compaction_need))
        )
    soil_health = clip(0.65 * s_base + 0.35 * mean(regen_scores), 0, 1)

    # a dry probe reading means the ground is drier than the satellite thinks
    if dry_probe:
        effective_moisture = max(0.14, field["moistureAvg"] - 0.11)
        effective_drought = min(0.68, field["drought2024"] + 0.18)
    else:
        effective_moisture = field["moistureAvg"]
        effective_drought = field["drought2024"]
    drought_trend = effective_drought - field["drought2023"]
    drought_score = 1.0 - clip(effective_drought, 0, 1)
    moisture_score = clip(effective_moisture / 0.5, 0, 1)
    trend_penalty = clip(drought_trend * 1.2, 0.0, 0.2)
    supply = clip((drought_score + moisture_score) / 2.0 - trend_penalty, 0, 1)

    # average growing season rain across 2023 and 2024
    annual_precip = (
        field["spring2024Precip"] + field["summer2024Precip"]
        + field["spring2023Precip"] + field["summer2023Precip"]
    ) / 2.0

    water_scores = []
    for c in crops:
        demand_norm = clip((c["water"] - 150) / 450.0, 0, 1)
        base_stress = 1.0 - (1.0 - supply) * demand_norm
        precip_adequacy = clip(annual_precip / max(c["water"] * 1.15, 1.0), 0, 1)
        water_scores.append(clip(0.75 * base_stress + 0.25 * precip_adequacy, 0, 1))
    water_safety = mean(water_scores)

    anom_score = clip((field["anom2024"] + 40) / 60.0, 0, 1)
    ndvi_score = clip(field["ndvi2024"] / 0.9, 0, 1)
    anom_trend = field["anom2024"] - field["anom2023"]
    anom_trend_pen = clip(-anom_trend / 40.0, 0, 0.25)
    heat_pen = clip((field["tempSummer"] - 24.5) / 8.0, 0, 0.15)
    c_base = clip((anom_score + ndvi_score) / 2.0 - 0.5 * (anom_trend_pen + heat_pen), 0, 1)

    unique_types = len({c["type"] for c in crops})
    diversity_score = clip(unique_types / min(n, 3), 0, 1)
    drought_hedge = mean(c["droughtTol"] for c in crops)
    resilience = clip(0.65 * c_base + 0.35 * (0.55 * diversity_score + 0.45 * drought_hedge), 0, 1)

    # walk the rotation as a loop so year 3 going back into year 1 counts too
    repeat_count = 0
    same_type_count = 0
    n_synergy = 0.0
    root_alt = 0.0
    for i in range(n):
        curr = crops[i]
        nxt = crops[(i + 1) % n]
        step_w = 1.0 - 0.06 * i
        if curr["id"] == nxt["id"]:
            repeat_count += 1
        elif curr["type"] == nxt["type"]:
            same_type_count += 1
        # a legume leaves nitrogen behind for a hungry crop that can't fix its own
        if curr["nFix"] >= 0.5 and nxt["nFix"] == 0.0:
            demand_w = clip(nxt["yieldT"] / 10.5, 0.3, 1.0)
            n_synergy += curr["nFix"] * demand_w * step_w
        root_alt += clip(abs(curr["rootM"] - nxt["rootM"]) / 1.5, 0, 1) * step_w

    oc_deficit = clip((3.0 - field["oc"]) / 2.0, 0, 1)
    year1_bonus = 0.04 * (crops[0]["nFix"] + crops[0]["build"]) * (0.5 + 0.5 * oc_deficit)
    n_carry_bonus = clip(n_synergy / n + year1_bonus, 0, 0.25)
    penalty_mult = clip(1.0 - 0.35 * (repeat_count / n) - 0.08 * (same_type_count / n), 0.65, 1.0)
    trans_score = clip(
        (0.5 * clip(root_alt / n, 0, 1) + 0.5 * clip(n_synergy / max(n * 0.5, 1.0), 0, 1)) * penalty_mult, 0, 1
    )

    n_fix_avg = clip(0.85 * mean(c["nFix"] for c in crops) + 0.6 * n_carry_bonus, 0, 1)
    yield_avg = mean(clip(c["yieldT"] / 12.0, 0, 1) for c in crops)

    # how well each crop's preferred pH and clay range matches this field
    compat_scores = []
    for c in crops:
        ph_center = (c["phMax"] + c["phMin"]) / 2.0
        ph_half = (c["phMax"] - c["phMin"]) / 2.0 + 0.5
        ph_s = max(0, 1.0 - abs(field["ph"] - ph_center) / ph_half)
        clay_center = (c["clayMax"] + c["clayMin"]) / 2.0
        clay_half = (c["clayMax"] - c["clayMin"]) / 2.0 + 5.0
        clay_s = max(0, 1.0 - abs(field["clay"] - clay_center) / clay_half)
        compat_scores.append((ph_s + clay_s) / 2.0)
    soil_compat = clip(0.8 * mean(compat_scores) + 0.2 * trans_score, 0, 1)

    w = profile_weights(profile_name, intensity)
    raw_total = (
        w["soil_health"] * soil_health
        + w["water_stress"] * water_safety
        + w["climate_res"] * resilience
        + w["nitrogen_fix"] * n_fix_avg
        + w["yield"] * yield_avg
        + w["drought_tol"] * drought_hedge
        + w["soil_compat"] * soil_compat
    )
    total_score = clip(raw_total * penalty_mult, 0, 1)

    return {
        "seqIds": list(seq_ids),
        "label": " → ".join(c["name"] for c in crops),
        "totalScore": total_score,
        "soilHealth": soil_health,
        "waterSafety": water_safety,
        "resilience": resilience,
        "yieldPotential": clip(yield_avg + 0.28, 0.35, 0.94),
        "nFixAvg": n_fix_avg,
    }


def is_good_three_crop_selection(selected_ids):
    """True when the 3 picked crops already make a sensible rotation without swapping anything."""
    if len(selected_ids) != 3:
        return False
    crops = [CROPS[cid] for cid in selected_ids if cid in CROPS]
    if len(crops) != 3:
        return False

    has_perennial = any(c["isPerennial"] for c in crops)
    all_perennial = all(c["isPerennial"] for c in crops)
    # you can't rotate an orchard through a corn field
    if has_perennial and not all_perennial:
        return False

    unique_types = len({c["type"] for c in crops})
    if all_perennial:
        return unique_types >= 2

    # annual rotations need a legume to put nitrogen back and 2+ families to break pest cycles
    has_legume = any(c["nFix"] >= 0.5 for c in crops)
    return has_legume and unique_types >= 2


def build_candidate_pool(selected_ids):
    """Start from our preset rotations and add ones built around the crops the farmer picked."""
    pool = [list(seq) for seq in CANDIDATE_SEQUENCES]
    seen = {"-".join(seq) for seq in pool}

    def add_seq(seq):
        key = "-".join(seq)
        if key not in seen and len(set(seq)) == 3:
            seen.add(key)
            pool.append(list(seq))

    count = len(selected_ids)
    if count == 1:
        c1 = selected_ids[0]
        if CROPS[c1]["isPerennial"]:
            partners = [cid for cid in PERENNIAL_PARTNERS if cid != c1]
            add_seq([c1, partners[0], partners[1]])
            add_seq([partners[0], c1, partners[1]])
        else:
            legumes = [cid for cid in LEGUMES if cid != c1]
            cash = [cid for cid in CASH_CROPS if cid != c1]
            add_seq([legumes[0], c1, cash[0]])
            add_seq([c1, legumes[0], cash[1]])
            add_seq([legumes[1], c1, cash[0]])
    elif count == 2:
        c1, c2 = selected_ids
        both_perennial = CROPS[c1]["isPerennial"] and CROPS[c2]["isPerennial"]
        if both_perennial:
            third_options = ["C04", "C05", "C07", "C08", "C06"]
        else:
            third_options = ["C03", "C01", "C12", "C02", "C13", "C11", "C09"]
        for c3 in third_options:
            if c3 != c1 and c3 != c2:
                add_seq([c1, c2, c3])
                add_seq([c3, c1, c2])
                add_seq([c1, c3, c2])
    elif count == 3:
        a, b, c = selected_ids
        if is_good_three_crop_selection(selected_ids):
            for seq in ([a, b, c], [b, c, a], [c, a, b], [a, c, b], [b, a, c], [c, b, a]):
                add_seq(seq)
        else:
            # keep 2 of their picks and swap a legume in for the third
            for leg in ["C03", "C12", "C01"]:
                add_seq([leg, a, b])
                add_seq([leg, a, c])
                add_seq([leg, b, c])
    elif count >= 4:
        # too many crops for one 3 year plan, so try every balanced group of 3
        for i in range(count):
            for j in range(i + 1, count):
                for k in range(j + 1, count):
                    sub = [selected_ids[i], selected_ids[j], selected_ids[k]]
                    if is_good_three_crop_selection(sub):
                        add_seq(sub)
                        add_seq([sub[1], sub[0], sub[2]])
        annual_picks = [cid for cid in selected_ids if not CROPS[cid]["isPerennial"]]
        if len(annual_picks) >= 2:
            add_seq(["C03", annual_picks[0], annual_picks[1]])
            add_seq(["C12", annual_picks[0], annual_picks[1]])

    return pool


def _compare_rotations(a, b):
    # best sort score first, then total score, then water safety, then nitrogen
    for key in ("sortScore", "totalScore", "waterSafety"):
        if abs(b[key] - a[key]) > 0.0001:
            return 1 if b[key] > a[key] else -1
    if b["nFixAvg"] > a["nFixAvg"]:
        return 1
    if b["nFixAvg"] < a["nFixAvg"]:
        return -1
    return 0


def rank_rotations(
    field,
    selected_crops,
    profile_name="Balanced",
    intensity=50,
    previous_crop_id=None,
    max_water=550,
    dry_probe=False,
):
    """Build every candidate rotation for this farmer, score each one and return them best first."""
    selected_ids = [cid for cid in selected_crops if cid in CROPS]
    pool = build_candidate_pool(selected_ids)

    # drop rotations with a crop that needs more water than the farmer allows
    filtered = [seq for seq in pool if all(CROPS[cid]["water"] <= max_water for cid in seq)]
    if len(filtered) < 3:
        filtered = pool

    good_three_pick = is_good_three_crop_selection(selected_ids)
    prev_crop = CROPS.get(previous_crop_id) if previous_crop_id else None

    scored = []
    for seq in filtered:
        base = score_sequence(seq, field, profile_name, intensity, dry_probe)
        match_count = sum(1 for cid in seq if cid in selected_ids)

        # rotations that use the farmer's own crops get a boost in the ordering
        selection_bonus = 0.0
        if len(selected_ids) == 3 and good_three_pick:
            selection_bonus = 0.18 if match_count == 3 else match_count * 0.03
        elif 1 <= len(selected_ids) <= 3:
            selection_bonus = min(match_count, 2) * 0.07
        elif len(selected_ids) >= 4:
            selection_bonus = match_count * 0.05

        # year 1 should not repeat what was just grown, and a legume after a hungry crop is a plus
        year1_crop = CROPS[seq[0]]
        prev_delta = 0.0
        if prev_crop is not None:
            if prev_crop["id"] == year1_crop["id"]:
                prev_delta = -0.08
            elif prev_crop["nFix"] == 0.0 and year1_crop["nFix"] >= 0.5:
                prev_delta = 0.04
            elif prev_crop["type"] != year1_crop["type"]:
                prev_delta = 0.02

        adjusted_total = clip(base["totalScore"] + prev_delta * 0.5, 0, 1)
        base["totalScore"] = adjusted_total
        base["matchCount"] = match_count
        base["sortScore"] = adjusted_total + selection_bonus + prev_delta
        scored.append(base)

    scored.sort(key=cmp_to_key(_compare_rotations))
    return scored


if __name__ == "__main__":
    # quick check on field F001 with the default crop picks
    top = rank_rotations(FIELDS["F001"], ["C01", "C02", "C03"], previous_crop_id="C02")[:3]
    for row in top:
        print(round(row["totalScore"], 3), row["label"])
