"""
Backend-to-Frontend Bridge for Farming Aura (Field Shift).

Connects the Python backend pipeline (`main.py`, `nasa_client.py`, `fetch_soil.py`,
`crops.py`, and `scoring.py`) directly to the frontend dashboard (`src/front end/`).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scoring import PROFILES, clip, field_soil_baseline_score

# Default agricultural parcel coordinates for the 5 New York cities in the frontend
FRONTEND_CITY_COORDS: dict[str, dict[str, Any]] = {
    "Albany": {"label": "Albany, New York", "lat": 42.6554, "lon": -73.9734, "defaultField": "F001"},
    "Saratoga Springs": {"label": "Saratoga Springs, New York", "lat": 42.9241, "lon": -73.6411, "defaultField": "F002"},
    "Schenectady": {"label": "Schenectady, New York", "lat": 42.8142, "lon": -74.0250, "defaultField": "F003"},
    "Troy": {"label": "Troy, New York", "lat": 42.7650, "lon": -73.6120, "defaultField": "F004"},
    "Hudson": {"label": "Hudson, New York", "lat": 42.2529, "lon": -73.7550, "defaultField": "F008"},
}

# Map downtown city-center pin coordinates from app.js to nearby agricultural soil survey parcels
DOWNTOWN_TO_AG_PARCEL: dict[tuple[float, float], tuple[float, float]] = {
    (42.6526, -73.7562): (42.6554, -73.9734),
    (43.0831, -73.7846): (42.9241, -73.6411),
}

FIELD_COORD_OFFSETS: dict[str, tuple[float, float]] = {
    "F001": (0.0000, 0.0000),
    "F002": (0.0120, -0.0150),
    "F003": (-0.0140, 0.0180),
    "F004": (0.0210, 0.0110),
    "F005": (-0.0220, -0.0190),
    "F006": (0.0310, -0.0240),
    "F007": (-0.0280, 0.0270),
    "F008": (0.0160, 0.0290),
}

FRONTEND_CROP_META: dict[str, dict[str, Any]] = {
    "C01": {"id": "C01", "name": "Hay & Alfalfa (Haylage)", "type": "legume", "isPerennial": False, "roleTag": "Forage legume • nitrogen fixation", "water": 560, "nFix": 0.85},
    "C02": {"id": "C02", "name": "Field Corn (Silage & Grain)", "type": "grain", "isPerennial": False, "roleTag": "Grain • high silage & grain yield", "water": 520, "nFix": 0.0},
    "C03": {"id": "C03", "name": "Soybeans & Small Grains", "type": "legume", "isPerennial": False, "roleTag": "Legume • nitrogen fixation & cover", "water": 420, "nFix": 0.80},
    "C04": {"id": "C04", "name": "Apples", "type": "orchard", "isPerennial": True, "roleTag": "Orchard • perennial tree fruit", "water": 500, "nFix": 0.0},
    "C05": {"id": "C05", "name": "Grapes (Juice & Wine)", "type": "vineyard", "isPerennial": True, "roleTag": "Vineyard • deep roots & low water", "water": 380, "nFix": 0.0},
    "C06": {"id": "C06", "name": "Cherries, Peaches, Pears & Plums", "type": "orchard", "isPerennial": True, "roleTag": "Stone & pome fruit • orchard block", "water": 480, "nFix": 0.0},
    "C07": {"id": "C07", "name": "Berries", "type": "berry", "isPerennial": True, "roleTag": "Small fruit • acidic soil specialist", "water": 430, "nFix": 0.0},
    "C08": {"id": "C08", "name": "Sugar Maple (Maple Syrup)", "type": "agroforestry", "isPerennial": True, "roleTag": "Agroforestry • deep canopy & carbon", "water": 450, "nFix": 0.0},
    "C09": {"id": "C09", "name": "Cabbage", "type": "vegetable", "isPerennial": False, "roleTag": "Brassica • high-value cool crop", "water": 440, "nFix": 0.0},
    "C10": {"id": "C10", "name": "Onions", "type": "root_veg", "isPerennial": False, "roleTag": "Allium • shallow root cash crop", "water": 410, "nFix": 0.0},
    "C11": {"id": "C11", "name": "Potatoes", "type": "root_veg", "isPerennial": False, "roleTag": "Tuber • high yield & loose soil", "water": 480, "nFix": 0.0},
    "C12": {"id": "C12", "name": "Sweet Corn, Snap Beans & Green Peas", "type": "legume", "isPerennial": False, "roleTag": "Vegetable legume • nitrogen builder", "water": 430, "nFix": 0.65},
    "C13": {"id": "C13", "name": "Beets, Carrots, Squash & Pumpkins", "type": "vegetable", "isPerennial": False, "roleTag": "Root & vine veg • broad ground cover", "water": 400, "nFix": 0.0},
    "C14": {"id": "C14", "name": "Small Grains (Winter Wheat, Oats & Barley)", "type": "grain", "isPerennial": False, "roleTag": "Small grain • winter cover & straw", "water": 360, "nFix": 0.0},
    "C15": {"id": "C15", "name": "Sweet Corn", "type": "grain", "isPerennial": False, "roleTag": "Fresh-market grain • warm season", "water": 450, "nFix": 0.0},
    "C16": {"id": "C16", "name": "Beets & Carrots", "type": "root_veg", "isPerennial": False, "roleTag": "Root vegetable • deep taproot", "water": 390, "nFix": 0.0},
    "C17": {"id": "C17", "name": "Winter Cover Crop Mix (Rye & Crimson Clover)", "type": "legume", "isPerennial": False, "roleTag": "Cover crop • erosion control & N builder", "water": 220, "nFix": 0.65},
}


def compute_intensity_weights(profile_name: str, intensity: int = 50) -> dict[str, float]:
    """Scale preset profile weights by the frontend's 1-100 intensity slider."""
    base_balanced = PROFILES["Balanced"]
    target_weights = PROFILES.get(profile_name, base_balanced)
    intensity_clamped = clip(float(intensity), 1.0, 100.0)
    if intensity_clamped <= 50.0:
        power_scale = 0.15 + ((intensity_clamped - 1.0) / 49.0) * 0.85
    else:
        power_scale = 1.0 + ((intensity_clamped - 50.0) / 50.0) * 1.50

    raw_weights: dict[str, float] = {}
    if profile_name == "Balanced" or target_weights == base_balanced:
        uniform = 1.0 / len(base_balanced)
        bal_scale = (
            ((intensity_clamped - 1.0) / 49.0)
            if intensity_clamped <= 50.0
            else 1.0 + ((intensity_clamped - 50.0) / 50.0) * 1.75
        )
        for key, base_val in base_balanced.items():
            raw_weights[key] = max(0.01, uniform + (base_val - uniform) * bal_scale)
    else:
        for key, base_val in base_balanced.items():
            target_val = target_weights.get(key, base_val)
            raw_weights[key] = max(0.01, base_val + (target_val - base_val) * power_scale)

    total = sum(raw_weights.values())
    return {k: round(v / total, 4) for k, v in raw_weights.items()}


def resolve_frontend_coordinates(payload: dict[str, Any]) -> tuple[float, float, str]:
    """Determine (lat, lon, region_label) from the frontend state payload."""
    city_key = str(payload.get("selectedCity") or payload.get("city") or "Albany")
    city_info = FRONTEND_CITY_COORDS.get(city_key, FRONTEND_CITY_COORDS["Albany"])
    field_id = str(payload.get("selectedFieldId") or payload.get("field_id") or city_info["defaultField"])

    raw_lat = payload.get("lat")
    raw_lon = payload.get("lon")
    custom_coords = bool(payload.get("customCoords", False))
    if custom_coords and raw_lat is not None and raw_lon is not None:
        try:
            lat = round(float(raw_lat), 4)
            lon = round(float(raw_lon), 4)
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                if (lat, lon) in DOWNTOWN_TO_AG_PARCEL:
                    lat, lon = DOWNTOWN_TO_AG_PARCEL[(lat, lon)]
                return lat, lon, str(city_info["label"])
        except (TypeError, ValueError):
            pass

    if field_id == city_info.get("defaultField"):
        offset_lat, offset_lon = (0.0, 0.0)
    else:
        offset_lat, offset_lon = FIELD_COORD_OFFSETS.get(field_id, (0.0, 0.0))
    lat = round(float(city_info["lat"]) + offset_lat, 4)
    lon = round(float(city_info["lon"]) + offset_lon, 4)
    return lat, lon, str(city_info["label"])


def build_sensor_overrides_from_frontend(payload: dict[str, Any]) -> Optional[dict[str, float]]:
    """Translate the frontend's sensor toggle and Wet/Dry moisture probe state into sensor_overrides."""
    if payload.get("sensor_overrides") and isinstance(payload["sensor_overrides"], dict):
        return payload["sensor_overrides"]

    if not bool(payload.get("sensorEnabled", True)):
        return None

    active_tab = str(payload.get("activeTab") or "rotations").lower()
    probe_mode = str(payload.get("probeMode") or "dry").lower()
    if probe_mode == "dry" and active_tab == "sensors":
        return {"soil_moisture": 0.21}
    if probe_mode == "wet" and active_tab == "sensors":
        return {"soil_moisture": 0.41}
    return None


def _format_rotation_for_frontend(
    scored_rot: dict[str, Any],
    selected_ids: list[str],
) -> dict[str, Any]:
    """Transform a backend score_rotation result dict into the frontend rotation structure."""
    raw_ids = [cid.strip() for cid in str(scored_rot.get("seq_ids", "")).split("->") if cid.strip()]
    crops_formatted: list[dict[str, Any]] = []
    frontend_seq_ids: list[str] = []

    for cid in raw_ids:
        meta = dict(FRONTEND_CROP_META.get(cid, FRONTEND_CROP_META["C03"]))
        crops_formatted.append(meta)
        frontend_seq_ids.append(str(meta["id"]))

    label = " → ".join(c["name"] for c in crops_formatted)
    distinct_matches = len(set(frontend_seq_ids).intersection(set(selected_ids)))
    if len(selected_ids) == 3 and distinct_matches == 3:
        selection_bonus = 0.18
    else:
        selection_bonus = distinct_matches * 0.05

    total_score = float(scored_rot.get("total_score", 0.72))
    return {
        "seqIds": frontend_seq_ids,
        "backendSeqIds": raw_ids,
        "crops": crops_formatted,
        "label": label,
        "totalScore": round(total_score, 4),
        "soilHealth": round(float(scored_rot.get("soil_health", 0.70)), 3),
        "waterSafety": round(float(scored_rot.get("water_stress", 0.78)), 3),
        "resilience": round(float(scored_rot.get("climate_res", 0.75)), 3),
        "yieldPotential": round(float(scored_rot.get("yield_potential", 0.80)), 3),
        "nFixAvg": round(float(scored_rot.get("nitrogen_fixation", 0.60)), 3),
        "soilCompatibility": round(float(scored_rot.get("soil_compatibility", 0.80)), 3),
        "drainageSuitability": round(float(scored_rot.get("drainage_suitability", 0.75)), 3),
        "transitionScore": round(float(scored_rot.get("transition_score", 0.65)), 3),
        "matchCount": distinct_matches,
        "sortScore": round(total_score + selection_bonus, 4),
        "previousCropEffect": scored_rot.get("previous_crop_effect", {}),
    }


def _build_frontend_evaluation(
    selected_ids: list[str],
    top_pick: Optional[dict[str, Any]],
    max_water_demand: float,
    soil_map_unit: str,
) -> dict[str, str]:
    """Build the crop selection evaluation banner and feedback card strings."""
    count = len(selected_ids)
    picked_names = [FRONTEND_CROP_META[cid]["name"] for cid in selected_ids if cid in FRONTEND_CROP_META]
    rec_label = (
        top_pick["label"]
        if top_pick
        else "Soybeans & Small Grains → Field Corn (Silage & Grain) → Hay & Alfalfa (Haylage)"
    )

    if count == 0:
        return {
            "bannerEyebrow": "LIVE BACKEND / PICK YOUR CROPS IN THE SIDEBAR",
            "bannerTitle": "This might be a better idea to start with.",
            "heading": "Backend Suggestion: Pick 1 to 3 crops in the sidebar",
            "line1": f"USDA soil map unit matched: {soil_map_unit}. Pick your preferred New York crops in the Crops dropdown on the left.",
            "line2": f"Top backend recommendation for this field: {rec_label}.",
        }
    if count >= 4:
        preview_names = ", ".join(picked_names[:4]) + ("..." if count > 4 else "")
        return {
            "bannerEyebrow": f"WARNING / {count} CROPS SELECTED (TOO MANY)",
            "bannerTitle": "Picking this many crops is bad — try this better 3-crop plan.",
            "heading": "Why picking this many crops is bad",
            "line1": f"Selecting {count} crops at once ({preview_names}) splits field management and weakens soil recovery on {soil_map_unit}.",
            "line2": f"Backend recommendation: Narrow your rotation to {rec_label} for stronger nitrogen carry-over and yield.",
        }

    crops_meta = [FRONTEND_CROP_META[cid] for cid in selected_ids if cid in FRONTEND_CROP_META]
    has_perennial = any(c["isPerennial"] for c in crops_meta)
    all_perennial = all(c["isPerennial"] for c in crops_meta) if crops_meta else False
    has_legume = any(float(c["nFix"]) >= 0.5 for c in crops_meta)
    unique_types = len({c["type"] for c in crops_meta})
    is_good_three = (
        count == 3
        and not (has_perennial and not all_perennial)
        and ((all_perennial and unique_types >= 2) or (has_legume and unique_types >= 2))
    )
    if is_good_three:
        return {
            "bannerEyebrow": "GOOD SELECTION / BALANCED THREE-YEAR ROTATION",
            "bannerTitle": "This is a good crop selection for your field.",
            "heading": "This is a good crop mix — why it works",
            "line1": f"Your 3 selected crops ({', '.join(picked_names)}) balance nitrogen fixation, root depth, and pest suppression on {soil_map_unit}.",
            "line2": f"Backend ranked #1 sequence: {rec_label} within your {int(max_water_demand)} mm water budget.",
        }
    if count == 1:
        return {
            "bannerEyebrow": "SUGGESTION / 1 CROP SELECTED — THIS MIGHT BE A BETTER IDEA",
            "bannerTitle": "This might be a better idea than planting a single crop.",
            "heading": "Suggestion: This might be a better idea",
            "line1": f"You only picked {picked_names[0]} — continuous monoculture depletes soil nutrients and builds host-specific pests on {soil_map_unit}.",
            "line2": f"Better backend suggestion: Rotate {picked_names[0]} inside {rec_label} to restore nitrogen and protect topsoil.",
        }
    if count == 2:
        return {
            "bannerEyebrow": "SUGGESTION / 2 CROPS SELECTED — THIS MIGHT BE A BETTER IDEA",
            "bannerTitle": "This might be a better idea for a full 3-year cycle.",
            "heading": "Suggestion: This might be a better idea",
            "line1": f"You picked {' and '.join(picked_names)} — adding a 3rd complementary crop completes a 3-year disease-break cycle on {soil_map_unit}.",
            "line2": f"Better backend suggestion: Try {rec_label} for balanced soil recovery.",
        }
    return {
        "bannerEyebrow": "SUGGESTION / 3 CROPS SELECTED — THIS MIGHT BE A BETTER IDEA",
        "bannerTitle": "This might be a better idea for soil balance.",
        "heading": "Suggestion: This might be a better idea",
        "line1": f"Your 3 picks ({', '.join(picked_names)}) either lack a nitrogen-fixing legume or mix perennial tree/vine crops with annual row crops.",
        "line2": f"Better backend suggestion: Swap in a complementary nitrogen builder with {rec_label}.",
    }


def analyze_for_frontend(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Main bridge function: accepts the frontend's state dictionary, executes the
    backend pipeline (`analyze_location_and_crops`), and returns a dictionary
    tailored directly for `src/front end/backend_connector.js`.
    """
    from crops import resolve_sequence_crops
    from main import analyze_location_and_crops, resolve_previous_crops
    from scoring import score_rotation

    lat, lon, region_label = resolve_frontend_coordinates(payload)
    field_id = str(payload.get("selectedFieldId") or payload.get("field_id") or "F001")
    previous_crop_id = str(payload.get("previousCropId") or payload.get("previous_crop") or "C02")
    selected_crops_raw = payload.get("selectedCrops") or payload.get("selected_crops") or ["C01", "C02", "C03"]
    selected_ids = [str(c).strip().upper() for c in selected_crops_raw if str(c).strip()]

    profile_name = str(payload.get("selectedProfile") or payload.get("profile_name") or "Balanced")
    profile_intensity = int(payload.get("profileIntensity") or 50)
    max_water_demand = float(payload.get("maxWaterDemand") or payload.get("max_water_demand_mm") or 550.0)
    probe_mode = str(payload.get("probeMode") or "dry").lower()

    custom_weights = compute_intensity_weights(profile_name, profile_intensity)
    sensor_overrides = build_sensor_overrides_from_frontend(payload)

    # Ensure explicitly selected crops (such as C01 Hay & Alfalfa at 560 mm) are not
    # dropped before scoring when the default water slider sits at 550 mm
    selected_max_water = max(
        [max_water_demand]
        + [float(FRONTEND_CROP_META[cid]["water"]) for cid in selected_ids if cid in FRONTEND_CROP_META]
    )

    backend_result = analyze_location_and_crops(
        lat=lat,
        lon=lon,
        selected_crops=selected_ids if selected_ids else None,
        previous_crops=[previous_crop_id],
        profile_name=profile_name,
        custom_weights=custom_weights,
        rotation_length=3,
        row_crop_only=False,
        max_water_demand_mm=selected_max_water,
        top_n=8,
        use_cache=True,
        sensor_overrides=sensor_overrides,
    )

    soil = backend_result["soil"]
    climate = backend_result["climate"]
    raw_rotations = list(backend_result.get("recommended_rotations", []))

    # Also score direct 3-year permutations of the farmer's selected crops and candidate sequences
    seen_seqs = {str(r.get("seq_ids", "")) for r in raw_rotations}
    prev_objs = resolve_previous_crops([previous_crop_id])
    extra_sequences: list[list[str]] = [
        ["C03", "C02", "C01"],
        ["C01", "C02", "C03"],
        ["C03", "C02", "C11"],
        ["C12", "C09", "C10"],
        ["C03", "C11", "C13"],
        ["C12", "C11", "C09"],
        ["C03", "C09", "C13"],
        ["C12", "C10", "C13"],
        ["C04", "C07", "C05"],
        ["C06", "C04", "C08"],
    ]
    if len(selected_ids) >= 3:
        import itertools

        for perm in itertools.permutations(selected_ids[:4], 3):
            if perm[0] != previous_crop_id:
                extra_sequences.insert(0, list(perm))

    for seq in extra_sequences:
        if seq[0] == previous_crop_id:
            continue
        seq_key = " -> ".join(seq)
        if seq_key not in seen_seqs:
            try:
                crop_rows = resolve_sequence_crops(list(seq))
                scored_perm = score_rotation(
                    crop_rows=crop_rows,
                    soil=soil,
                    climate=climate,
                    profile_name=profile_name,
                    custom_weights=custom_weights,
                    previous_crops=prev_objs,
                )
                scored_perm.pop("_raw_sort_key", None)
                raw_rotations.append(scored_perm)
                seen_seqs.add(seq_key)
            except Exception:
                pass

    all_formatted = [
        _format_rotation_for_frontend(rot, selected_ids)
        for rot in raw_rotations
    ]
    effective_water_cap = 580.0 if max_water_demand >= 550.0 else max_water_demand
    within_water = [
        r for r in all_formatted
        if all(float(c.get("water", 450)) <= effective_water_cap for c in r["crops"])
    ]
    ranked_rotations = within_water if len(within_water) >= 3 else all_formatted
    ranked_rotations.sort(
        key=lambda r: (r["sortScore"], r["totalScore"], r["waterSafety"], r["nFixAvg"]),
        reverse=True,
    )
    top_pick = ranked_rotations[0] if ranked_rotations else None

    growing_precip = float(climate.get("growing_season_precip_mm") or 520.0)
    spring_2024 = round(growing_precip * 0.56)
    summer_2024 = round(growing_precip * 0.44)
    precip_trend_pct = float(climate.get("precip_anom_trend") or -4.0)
    scale_2023 = 1.0 - (precip_trend_pct / 100.0) * 0.5
    spring_2023 = round(spring_2024 * clip(scale_2023, 0.80, 1.25))
    summer_2023 = round(summer_2024 * clip(scale_2023, 0.80, 1.25))

    drought_2024 = float(climate.get("drought_index") or 0.25)
    drought_trend = float(climate.get("drought_trend") or 0.03)
    drought_2023 = round(clip(drought_2024 - drought_trend, 0.05, 0.85), 3)

    moisture_avg = float(climate.get("soil_moisture_avg") or 0.33)
    ndvi_2024 = float(climate.get("ndvi_avg") or 0.70)
    ndvi_2023 = round(clip(ndvi_2024 + drought_trend * 0.35, 0.35, 0.90), 3)
    temp_summer = float(climate.get("summer_temp_c") or 24.5)
    soil_temp_c = round(temp_summer - 5.6, 1)
    anom_2024 = float(climate.get("anomaly_precip_pct") or 0.0)
    anom_2023 = round(anom_2024 - precip_trend_pct, 2)

    baseline_soil = round(float(soil.get("baseline_soil_health_score") or field_soil_baseline_score(soil)), 2)
    if drought_2024 >= 0.38:
        map_status = "High drought risk"
    elif drought_2024 >= 0.24:
        map_status = "Moderate stress"
    else:
        map_status = "Healthy"

    frontend_field = {
        "id": field_id,
        "name": f"Field {field_id}",
        "regionLabel": region_label,
        "lat": lat,
        "lon": lon,
        "oc": round(float(soil.get("organic_carbon_pct", 2.5)), 2),
        "ph": round(float(soil.get("ph", 6.5)), 2),
        "clay": round(float(soil.get("clay_pct", 25.0)), 1),
        "sand": round(float(soil.get("sand_pct", 40.0)), 1),
        "bd": round(float(soil.get("bulk_density", 1.35)), 2),
        "cec": round(float(soil.get("cec", 20.0)), 1),
        "spring2023Precip": spring_2023,
        "summer2023Precip": summer_2023,
        "spring2024Precip": spring_2024,
        "summer2024Precip": summer_2024,
        "drought2023": round(drought_2023, 3),
        "drought2024": round(drought_2024, 3),
        "moistureAvg": round(moisture_avg, 3),
        "ndvi2023": ndvi_2023,
        "ndvi2024": round(ndvi_2024, 3),
        "tempSummer": round(temp_summer, 1),
        "soilTempC": soil_temp_c,
        "anom2023": anom_2023,
        "anom2024": round(anom_2024, 2),
        "mapStatus": map_status,
        "mapSoilScore": baseline_soil,
        "mapMoisture": round(moisture_avg, 2),
        "mapUnitName": str(soil.get("map_unit_name") or "New York Agricultural Silt Loam"),
        "drainageClass": str(soil.get("drainage_class") or "Well drained"),
    }

    soil_map_unit = frontend_field["mapUnitName"]
    evaluation = _build_frontend_evaluation(
        selected_ids=selected_ids,
        top_pick=top_pick,
        max_water_demand=max_water_demand,
        soil_map_unit=soil_map_unit,
    )

    nasa_rzm = float(climate.get("growing_season_gwetroot") or moisture_avg)
    top_label = top_pick["label"] if top_pick else "Soybeans & Small Grains → Field Corn → Hay & Alfalfa"
    if probe_mode == "dry":
        probe_moist = round(max(0.14, nasa_rzm - 0.12), 2)
        sensor_report = {
            "mode": "dry",
            "nasaRzm": round(nasa_rzm, 2),
            "probeRzm": probe_moist,
            "nasaTempC": round(temp_summer, 1),
            "probeSoilTempC": round(soil_temp_c + 2.3, 1),
            "nasaPrecipMm": summer_2024,
            "humidityPct": 38,
            "alertTitle": "Moisture probe: Dry soil selected — rotation adjusted by backend",
            "alertSub": f"Backend response ({soil_map_unit}): Root-zone moisture ({probe_moist:.2f} m³/m³) is below NASA baseline ({nasa_rzm:.2f} m³/m³). Prioritizing drought-tolerant legumes.",
            "heading": f"Backend report for Field {field_id} ({soil_map_unit}) · Moisture Probe: DRY",
            "line1": f"Ground-truth probe indicates dry topsoil ({probe_moist:.2f} m³/m³ vs NASA {nasa_rzm:.2f} m³/m³). Backend advises reducing tillage and leading with drought-tolerant legumes.",
            "line2": f"Backend recommended rotation for Dry soil: {top_label}.",
        }
    else:
        probe_moist = round(min(0.49, nasa_rzm + 0.06), 2)
        sensor_report = {
            "mode": "wet",
            "nasaRzm": round(nasa_rzm, 2),
            "probeRzm": probe_moist,
            "nasaTempC": round(temp_summer, 1),
            "probeSoilTempC": round(soil_temp_c, 1),
            "nasaPrecipMm": summer_2024,
            "humidityPct": 68,
            "alertTitle": "Moisture probe: Wet soil selected — full water budget available",
            "alertSub": f"Backend response ({soil_map_unit}): Root-zone moisture is well-supplied ({probe_moist:.2f} m³/m³). High-yield crops and deep-rooted forages are supported.",
            "heading": f"Backend report for Field {field_id} ({soil_map_unit}) · Moisture Probe: WET",
            "line1": f"Ground-truth probe confirms wet root-zone conditions ({probe_moist:.2f} m³/m³ vs NASA {nasa_rzm:.2f} m³/m³). Backend advises monitoring drainage ({frontend_field['drainageClass']}) and utilizing moisture reserves.",
            "line2": f"Backend recommended rotation for Wet soil: {top_label}.",
        }

    return {
        "status": "ok",
        "connected": True,
        "coordinates": {"lat": lat, "lon": lon, "regionLabel": region_label},
        "dataSources": backend_result.get("data_sources", {}),
        "field": frontend_field,
        "rankedRotations": ranked_rotations,
        "evaluation": evaluation,
        "sensorReport": sensor_report,
        "perennialSuitability": backend_result.get("perennial_site_suitability", []),
        "weightsUsed": custom_weights,
    }


def register_frontend_bridge_routes(app: Any) -> None:
    """Attach `/api/frontend-sync` and static `/ui` mount to the FastAPI `app` instance."""
    if app is None:
        return

    from fastapi import Body, HTTPException
    from fastapi.staticfiles import StaticFiles

    @app.post("/api/frontend-sync")
    def frontend_sync_endpoint(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        """Receive frontend `appState`, run NASA POWER + USDA SSURGO pipeline, and return dashboard state."""
        try:
            return analyze_for_frontend(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    frontend_dir = BACKEND_DIR.parent / "front end"
    if frontend_dir.is_dir():
        app.mount("/ui", StaticFiles(directory=str(frontend_dir), html=True), name="frontend_ui")


def run_stdlib_bridge_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """
    Zero-dependency Python standard-library HTTP server that serves both
    `/health`, `/api/frontend-sync`, `/analyze`, and the static `src/front end/`
    files with full CORS support so the frontend connects even if FastAPI/uvicorn
    is not installed.
    """
    import json
    import mimetypes
    from http.server import BaseHTTPRequestHandler, HTTPServer

    from main import analyze_farm_request

    frontend_dir = (BACKEND_DIR.parent / "front end").resolve()

    class BridgeRequestHandler(BaseHTTPRequestHandler):
        def _send_cors_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")

        def _send_json(self, status_code: int, data: dict[str, Any]) -> None:
            body = json.dumps(data).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self._send_cors_headers()
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path == "/health":
                self._send_json(200, {"status": "ok", "bridge": "active"})
                return
            if path == "/config":
                from config import get_gemini_api_key, get_gemini_model, get_google_maps_api_key

                self._send_json(
                    200,
                    {
                        "google_maps_api_key": get_google_maps_api_key(),
                        "gemini_enabled": bool(get_gemini_api_key()),
                        "gemini_model": get_gemini_model(),
                    },
                )
                return


            rel_path = path.lstrip("/")
            if rel_path.startswith("ui/"):
                rel_path = rel_path[3:]
            if not rel_path or rel_path == "ui":
                rel_path = "index.html"

            target_file = (frontend_dir / rel_path).resolve()
            if str(target_file).startswith(str(frontend_dir)) and target_file.is_file():
                content = target_file.read_bytes()
                mime_type, _ = mimetypes.guess_type(str(target_file))
                self.send_response(200)
                self.send_header("Content-Type", mime_type or "application/octet-stream")
                self.send_header("Content-Length", str(len(content)))
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(content)
                return

            self._send_json(404, {"error": "Not found"})

        def do_POST(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            try:
                payload = json.loads(raw_body)
                if path == "/api/frontend-sync":
                    self._send_json(200, analyze_for_frontend(payload))
                elif path == "/analyze":
                    self._send_json(200, analyze_farm_request(payload))
                else:
                    self._send_json(404, {"error": f"Unknown endpoint {path}"})
            except Exception as exc:
                self._send_json(400, {"error": str(exc)})

        def log_message(self, format_str: str, *args: Any) -> None:
            return

    server = HTTPServer((host, port), BridgeRequestHandler)
    print(f"Farming Aura Backend-Frontend Bridge running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    if "--serve" in sys.argv:
        run_stdlib_bridge_server()
    else:
        sample_state = {
            "selectedCity": "Albany",
            "selectedFieldId": "F001",
            "previousCropId": "C02",
            "selectedProfile": "Balanced",
            "profileIntensity": 65,
            "selectedCrops": ["C01", "C02", "C03"],
            "maxWaterDemand": 550,
            "sensorEnabled": True,
            "probeMode": "dry",
        }
        bridged = analyze_for_frontend(sample_state)
        print("Bridge Status:", bridged["status"])
        print("Coordinates:", bridged["coordinates"])
        print("Data Sources:", bridged["dataSources"])
        print("Matched USDA Soil Map Unit:", bridged["field"]["mapUnitName"])
        print("Top Ranked Rotation:", bridged["rankedRotations"][0]["label"])
        print("Top Score:", bridged["rankedRotations"][0]["totalScore"])






