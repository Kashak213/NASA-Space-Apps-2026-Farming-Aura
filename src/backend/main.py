"""
Backend coordinator and API entry point for the crop rotation planner.

Receives farm coordinates (latitude and longitude) and the farmer's chosen
crops or crop types from the frontend, fetches weather data from NASA POWER
(nasa_client.py) and soil properties from USDA SSURGO (fetch_soil.py), and
runs the rotation scoring engine (scoring.py) to return ranked crop rotation
recommendations.
"""

from __future__ import annotations

# Standard library imports for building crop combinations, path setup, and JSON output
import itertools
import json
import math
import sys
from pathlib import Path
from typing import Any, Optional

# Ensure src/backend is on sys.path so imports work whether main.py is run directly
# or launched from the repository root via `uvicorn src.backend.main:app`
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Import crop lookup helpers and rotation generators from crops.py
from crops import (
    PRESET_ROTATIONS,
    WOODY_PERENNIAL_IDS,
    filter_rotations_by_constraints,
    generate_candidate_rotations,
    get_crop_by_id,
    get_crop_by_name,
    load_crops,
    resolve_sequence_crops,
)

# Import the USDA NRCS Soil Data Access client to get field soil lab metrics
from fetch_soil import fetch_usda_soil

# Import the NASA POWER client to get sunlight, wind speed, rainfall, temperature, and root wetness
from nasa_client import fetch_nasa_power

# Gemini writes the plain-English dashboard explanations, the key stays on the backend only
from gemini_client import explain_dashboard, gemini_is_configured

# Import the Mobile Measurement Station (MMS) serial telemetry reader
try:
    from mms_sensor import get_mms_telemetry, start_mms_reader
except ImportError:
    get_mms_telemetry = lambda auto_start=False: {"connected": False, "latest": {}}
    start_mms_reader = lambda: None

# gemini_client puts src/ on sys.path, so the shared .env reader is importable here
from config import get_google_maps_api_key  # noqa: E402

# Import the 7-weight scoring functions and preset farmer priority profiles from scoring.py
from scoring import (
    PROFILES,
    compare_profiles_for_rotation,
    field_soil_baseline_score,
    score_rotation,
    soil_drainage_score,
    sort_rotations,
)

# Import config helpers for Google Maps and Gemini
SRC_ROOT = BACKEND_DIR.parent
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
from config import get_google_maps_api_key

try:
    from gemini_client import explain_dashboard, gemini_is_configured
except ImportError:
    explain_dashboard = None
    gemini_is_configured = lambda: False

NY_REGIONS_PATH = BACKEND_DIR / "data" / "ny_regions.json"


def load_ny_regions() -> list[dict[str, Any]]:
    """Load New York agricultural region baselines from data/ny_regions.json."""
    if NY_REGIONS_PATH.exists() and NY_REGIONS_PATH.stat().st_size > 0:
        try:
            data = json.loads(NY_REGIONS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def find_nearest_ny_region(lat: float, lon: float) -> Optional[dict[str, Any]]:
    """Find the closest New York agricultural region to the given coordinates."""
    regions = load_ny_regions()
    if not regions:
        return None
    best_region: Optional[dict[str, Any]] = None
    best_dist = float("inf")
    for reg in regions:
        rlat = float(reg.get("center_lat", 42.7))
        rlon = float(reg.get("center_lon", -76.8))
        dist = math.hypot(lat - rlat, (lon - rlon) * math.cos(math.radians(lat)))
        if dist < best_dist:
            best_dist = dist
            best_region = reg
    # Return the matched NY region if the farm is within ~3.5 degrees of a NY region center
    return best_region if best_dist <= 3.5 else None

# Try importing FastAPI and Pydantic so main.py can run as an HTTP web server,
# while still working as a normal Python module for Streamlit or terminal tests
# even when FastAPI is not installed on a teammate's laptop yet
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
except ImportError:
    FastAPI = None
    HTTPException = None
    CORSMiddleware = None
    BaseModel = object
    Field = None


def resolve_farmer_crops(
    selected_crops: Optional[list[str]] = None,
    crop_types: Optional[list[str]] = None,
    catalog: Optional[list[dict[str, Any]]] = None,
) -> list[dict[str, Any]]:
    """
    Match the crop names, crop IDs, or crop family types sent by the frontend
    against our New York crop catalog in crops.py. If the user did not pick
    specific crops, return the full catalog so we can still rank rotations.
    """
    # Load all 17 New York crop groups from data/crops.json if a catalog list was not passed in
    all_crops = catalog if catalog is not None else load_crops()

    # Keep a list of matched crop dictionaries and a set of crop IDs so we never add duplicates
    matched: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    # Step 1: Check any specific crop IDs (like "C02") or crop names (like "Field Corn" or "Apples")
    if selected_crops:
        for item in selected_crops:
            # Skip empty strings or blank entries from the frontend
            if not item or not str(item).strip():
                continue

            raw_text = str(item).strip()

            # Try matching by crop ID first (for example "C01" through "C17")
            crop_obj = get_crop_by_id(raw_text, all_crops)

            # If it was not an ID, try matching by crop name (for example "Soybeans" or "Potatoes")
            if crop_obj is None:
                crop_obj = get_crop_by_name(raw_text, all_crops)

            # If it still did not match a single crop, check if the user passed a crop family type
            # like "grain", "legume", or "vegetable" inside the selected_crops list
            if crop_obj is None:
                type_matches = [
                    c
                    for c in all_crops
                    if str(c.get("crop_type", "")).lower() == raw_text.lower()
                ]
                for tm in type_matches:
                    cid = str(tm["crop_id"])
                    if cid not in seen_ids:
                        matched.append(tm)
                        seen_ids.add(cid)
            else:
                # We found a matching crop, so add it if we have not added its crop_id already
                cid = str(crop_obj["crop_id"])
                if cid not in seen_ids:
                    matched.append(crop_obj)
                    seen_ids.add(cid)

    # Step 2: Check if the frontend also sent a separate crop_types filter list
    # (for example ["grain", "legume", "vegetable", "orchard"])
    if crop_types:
        wanted_types = {str(t).strip().lower() for t in crop_types if str(t).strip()}
        for crop_obj in all_crops:
            if str(crop_obj.get("crop_type", "")).lower() in wanted_types:
                cid = str(crop_obj["crop_id"])
                if cid not in seen_ids:
                    matched.append(crop_obj)
                    seen_ids.add(cid)

    # If the farmer left the crop selection empty (or nothing matched), fall back to all catalog crops
    return matched if matched else all_crops


def resolve_previous_crops(
    previous_crops: Optional[list[str] | str] = None,
    catalog: Optional[list[dict[str, Any]]] = None,
    ask_if_missing: bool = False,
) -> list[dict[str, Any]]:
    """
    Resolve the crop or sequence of crops that was already farmed on the field
    prior to Year 1 (pushed from the frontend or entered in terminal mode).
    Returns a list of matched crop dictionaries ordered from older seasons to
    the most recently harvested crop right before Year 1.
    """
    all_crops = catalog if catalog is not None else load_crops()
    raw_items: list[str] = []

    if isinstance(previous_crops, str):
        raw_items = [part.strip() for part in previous_crops.split(",") if part.strip()]
    elif isinstance(previous_crops, list):
        for entry in previous_crops:
            if entry is not None and str(entry).strip():
                raw_items.append(str(entry).strip())

    if not raw_items and ask_if_missing and sys.stdin is not None and sys.stdin.isatty():
        try:
            user_in = input(
                "What crop was already farmed on this field last season? "
                "(Enter crop ID/name like C02 or Field Corn, or press Enter for none): "
            ).strip()
            if user_in and user_in.lower() not in ("none", "no", "n/a", "skip"):
                raw_items = [part.strip() for part in user_in.split(",") if part.strip()]
        except EOFError:
            pass

    resolved_prev: list[dict[str, Any]] = []
    for raw_text in raw_items:
        if raw_text.lower() in ("none", "no", "n/a", "null"):
            continue
        crop_obj = get_crop_by_id(raw_text, all_crops)
        if crop_obj is None and raw_text.isdigit():
            idx = int(raw_text)
            if 1 <= idx <= len(all_crops):
                crop_obj = all_crops[idx - 1]
        if crop_obj is None:
            crop_obj = get_crop_by_name(raw_text, all_crops)
        if crop_obj is None:
            crop_obj = next(
                (
                    c
                    for c in all_crops
                    if str(c.get("crop_type", "")).lower() == raw_text.lower()
                ),
                None,
            )
        if crop_obj is not None:
            resolved_prev.append(crop_obj)

    return resolved_prev


def build_climate_for_scoring(
    nasa_response: dict[str, Any],
    soil_data: dict[str, Any],
    lat: float = 42.70,
    lon: float = -76.80,
    mms_telemetry: Optional[dict[str, Any]] = None,
    sensor_overrides: Optional[dict[str, float]] = None,
) -> dict[str, Any]:
    """
    Combine the NASA POWER summary dictionary with NASA GWETROOT root-zone soil
    moisture, regional precipitation baselines, 2023-2024 climate trends, and
    optional local hardware sensor overrides for scoring.py.
    """
    summary = dict(nasa_response.get("summary", {}))
    raw_params = nasa_response.get("data", {})

    nearest_region = find_nearest_ny_region(lat, lon)
    if nearest_region is not None:
        normal_annual_mm = float(nearest_region.get("normal_annual_precip_mm", 950.0))
        normal_growing_mm = float(nearest_region.get("normal_growing_precip_mm", 450.0))
        region_name = str(nearest_region.get("region_name", "New York"))
    else:
        normal_annual_mm = 900.0
        normal_growing_mm = 430.0
        region_name = "General Temperate"

    annual_precip = summary.get("estimated_annual_precip_mm")
    if annual_precip is None:
        annual_precip = normal_annual_mm

    growing_precip = summary.get("growing_season_precip_mm")
    if growing_precip is None:
        growing_precip = round(float(annual_precip) * 0.48, 1)

    if summary.get("summer_temp_c") is not None:
        summer_temp_c = round(float(summary["summer_temp_c"]), 2)
    else:
        t2m_series = raw_params.get("T2M", {})
        summer_temps = [
            float(val)
            for key, val in t2m_series.items()
            if len(str(key)) >= 6 and str(key)[4:6] in ("06", "07", "08")
        ]
        summer_temp_c = (
            round(sum(summer_temps) / len(summer_temps), 2)
            if summer_temps
            else float(summary.get("t2m_avg_c") or 21.0)
        )
    growing_temp_c = float(summary.get("growing_season_temp_c") or (summer_temp_c - 2.0))

    annual_ratio = float(annual_precip) / max(normal_annual_mm, 1.0)
    growing_ratio = float(growing_precip) / max(normal_growing_mm, 1.0)
    blended_precip_ratio = 0.45 * annual_ratio + 0.55 * growing_ratio

    awc = float(soil_data.get("awc", 0.18))
    gwetroot = summary.get("growing_season_gwetroot") or summary.get("gwetroot_avg")
    if gwetroot is not None:
        nasa_volumetric_moisture = float(gwetroot) * 0.46
        soil_moisture_avg = round(
            max(0.10, min(0.48, 0.70 * nasa_volumetric_moisture + 0.30 * (awc * 1.5))),
            3,
        )
        drought_index = round(
            max(
                0.05,
                min(0.85, 1.0 - (0.45 * blended_precip_ratio + 0.55 * float(gwetroot))),
            ),
            3,
        )
    else:
        soil_moisture_avg = round(
            max(0.12, min(0.48, (awc * 1.4) + 0.08 * blended_precip_ratio)), 3
        )
        drought_index = round(
            max(0.05, min(0.85, 1.0 - 0.65 * blended_precip_ratio)), 3
        )

    anomaly_precip_pct = round(
        ((float(annual_precip) - normal_annual_mm) / max(normal_annual_mm, 1.0)) * 100.0,
        1,
    )
    growing_solar = float(
        summary.get("growing_season_solar_mj_m2_day")
        or summary.get("allsky_sfc_sw_dwn_avg")
        or 17.5
    )
    growing_wind = float(
        summary.get("growing_season_wind_m_s") or summary.get("ws2m_avg_m_s") or 3.0
    )

    override_ndvi: Optional[float] = None
    if sensor_overrides and isinstance(sensor_overrides, dict):
        if sensor_overrides.get("soil_moisture") is not None:
            sm_val = float(sensor_overrides["soil_moisture"])
            if sm_val > 1.0:
                sm_val = sm_val / 100.0
            soil_moisture_avg = round(max(0.05, min(0.60, sm_val)), 3)
            drought_index = round(
                max(0.05, min(0.90, 1.0 - (soil_moisture_avg / 0.42))),
                3,
            )
        if sensor_overrides.get("air_temp_c") is not None:
            air_t = round(float(sensor_overrides["air_temp_c"]), 2)
            growing_temp_c = air_t
            summer_temp_c = round(max(air_t, summer_temp_c * 0.4 + air_t * 0.6), 2)
        if sensor_overrides.get("ndvi_avg") is not None:
            override_ndvi = round(float(sensor_overrides["ndvi_avg"]), 3)
        if sensor_overrides.get("soil_ph") is not None:
            soil_data["ph"] = round(float(sensor_overrides["soil_ph"]), 2)

    moisture_factor = min(1.0, soil_moisture_avg / 0.34)
    solar_factor = min(1.0, growing_solar / 18.5)
    thermal_factor = max(0.4, min(1.0, (growing_temp_c - 8.0) / 11.0))

    # If the Mobile Measurement Station (MMS) is connected, incorporate its live readings
    soil_temp_c: Optional[float] = None
    air_humidity_pct: Optional[float] = None
    is_raining = False
    if mms_telemetry and mms_telemetry.get("connected"):
        latest = mms_telemetry.get("latest") or {}
        mms_moist_m3 = latest.get("soil_moisture_m3")
        if mms_moist_m3 is not None:
            # Blend 70% live MMS ground-truth root-zone moisture with 30% satellite and soil baseline
            soil_moisture_avg = round(0.70 * float(mms_moist_m3) + 0.30 * soil_moisture_avg, 3)
            if float(mms_moist_m3) < 0.24:
                drought_index = round(min(0.85, drought_index + 0.15), 3)
            elif float(mms_moist_m3) > 0.36:
                drought_index = round(max(0.05, drought_index - 0.10), 3)

        if latest.get("soil_temp_c") is not None:
            soil_temp_c = float(latest["soil_temp_c"])
        if latest.get("air_humidity_pct") is not None:
            air_humidity_pct = float(latest["air_humidity_pct"])
        if latest.get("is_raining") is not None:
            is_raining = bool(latest["is_raining"])

    estimated_ndvi = (
        override_ndvi
        if override_ndvi is not None
        else round(
            max(
                0.35,
                min(
                    0.88,
                    0.25 + 0.58 * (0.45 * moisture_factor + 0.30 * solar_factor + 0.25 * thermal_factor),
                ),
            ),
            3,
        )
    )

    climate_dict: dict[str, Any] = {
        "region_matched": region_name,
        "normal_annual_precip_mm": normal_annual_mm,
        "normal_growing_precip_mm": normal_growing_mm,
        "allsky_sfc_sw_dwn_avg": summary.get("allsky_sfc_sw_dwn_avg") or 13.0,
        "growing_season_solar_mj_m2_day": round(growing_solar, 2),
        "ws2m_avg_m_s": summary.get("ws2m_avg_m_s") or 3.0,
        "growing_season_wind_m_s": round(growing_wind, 2),
        "prectotcorr_avg_mm_day": summary.get("prectotcorr_avg_mm_day") or 2.6,
        "annual_precip_mm": float(annual_precip),
        "estimated_annual_precip_mm": float(annual_precip),
        "growing_season_precip_mm": float(growing_precip),
        "t2m_avg_c": summary.get("t2m_avg_c") or 10.0,
        "growing_season_temp_c": round(growing_temp_c, 2),
        "summer_temp_c": summer_temp_c,
        "gwetroot_avg": summary.get("gwetroot_avg"),
        "growing_season_gwetroot": summary.get("growing_season_gwetroot"),
        "drought_index": drought_index,
        "soil_moisture_avg": soil_moisture_avg,
        "anomaly_precip_pct": anomaly_precip_pct,
        "ndvi_avg": estimated_ndvi,
        "drought_trend": float(summary.get("drought_trend") or 0.0),
        "precip_anom_trend": float(summary.get("precip_anom_trend") or 0.0),
    }

    return climate_dict


def build_rotations_for_farmer(
    farmer_crops: list[dict[str, Any]],
    catalog: list[dict[str, Any]],
    rotation_length: int = 3,
    row_crop_only: bool = False,
    max_water_demand_mm: Optional[float] = None,
    previous_crops: Optional[list[dict[str, Any]]] = None,
) -> list[list[str]]:
    """
    Create candidate multi-year crop sequences tailored to the crops the farmer
    selected and what crop was already farmed on the field before Year 1. If the
    farmer picked at least 2 crops, we build sequences from their chosen pool
    plus complementary nitrogen-fixing legumes when needed.
    """
    # Clamp rotation length between 2 and 5 years so combinations stay fast and practical
    length = max(2, min(5, int(rotation_length)))
    farmer_ids = [str(c["crop_id"]) for c in farmer_crops]
    prev_ids = [str(c["crop_id"]) for c in (previous_crops or []) if c.get("crop_id")]
    last_prev_id = prev_ids[-1].upper() if prev_ids else None

    # Attempt 1: Build valid rotations using only the exact crops the farmer selected
    candidates = generate_candidate_rotations(
        crops=farmer_crops,
        length=length,
        row_crop_only=row_crop_only,
        max_water_demand_mm=max_water_demand_mm,
        previous_crop_ids=prev_ids,
    )

    # Attempt 2: Good rotations need at least one nitrogen-fixing legume (like Soybeans or Alfalfa).
    # If the farmer only picked non-legumes (like Corn and Potatoes), mix in legumes from our catalog
    # so we can recommend rotations that include their chosen crops without depleting soil nitrogen.
    if not candidates and farmer_crops:
        legume_helpers = [
            c
            for c in catalog
            if float(c.get("nitrogen_fixation", 0.0)) >= 0.5
            and str(c["crop_id"]) not in farmer_ids
        ]
        expanded_pool = farmer_crops + legume_helpers
        all_generated = generate_candidate_rotations(
            crops=expanded_pool,
            length=length,
            row_crop_only=row_crop_only,
            max_water_demand_mm=max_water_demand_mm,
            previous_crop_ids=prev_ids,
        )
        # Keep only candidate sequences that contain at least one crop the farmer asked for
        wanted_set = set(farmer_ids)
        candidates = [seq for seq in all_generated if any(cid in wanted_set for cid in seq)]

    # Attempt 3: Build non-repeating permutations from the farmer's annual/forage crops
    annual_farmer_ids = [cid for cid in farmer_ids if cid not in WOODY_PERENNIAL_IDS]
    if not candidates and len(annual_farmer_ids) >= 2:
        perm_len = min(length, len(annual_farmer_ids))
        raw_perms = [list(p) for p in itertools.permutations(annual_farmer_ids, perm_len)]
        filtered_perms = filter_rotations_by_constraints(
            raw_perms,
            crops=catalog,
            row_crop_only=row_crop_only,
            max_water_demand_mm=max_water_demand_mm,
        )
        perms_to_use = filtered_perms if filtered_perms else raw_perms
        if last_prev_id is not None:
            non_repeating_year1 = [
                seq for seq in perms_to_use if seq[0].upper() != last_prev_id
            ]
            candidates = non_repeating_year1 if non_repeating_year1 else perms_to_use
        else:
            candidates = perms_to_use

    # Attempt 4: Fall back to preset New York annual rotations filtered by constraints
    if not candidates:
        filtered_presets = filter_rotations_by_constraints(
            PRESET_ROTATIONS,
            crops=catalog,
            row_crop_only=row_crop_only,
            max_water_demand_mm=max_water_demand_mm,
        )
        presets_to_use = filtered_presets if filtered_presets else list(PRESET_ROTATIONS)
        if last_prev_id is not None:
            non_repeating_presets = [
                seq for seq in presets_to_use if seq[0].upper() != last_prev_id
            ]
            candidates = non_repeating_presets if non_repeating_presets else presets_to_use
        else:
            candidates = presets_to_use

    return candidates


def analyze_location_and_crops(
    lat: float,
    lon: float,
    selected_crops: Optional[list[str]] = None,
    crop_types: Optional[list[str]] = None,
    previous_crops: Optional[list[str] | str] = None,
    profile_name: str = "Balanced",
    custom_weights: Optional[dict[str, float]] = None,
    rotation_length: int = 3,
    row_crop_only: bool = True,
    max_water_demand_mm: Optional[float] = None,
    top_n: int = 5,
    start_year: int = 2023,
    end_year: int = 2024,
    use_cache: bool = True,
    sensor_overrides: Optional[dict[str, float]] = None,
    ask_previous_crop: bool = False,
) -> dict[str, Any]:
    """
    Main backend pipeline function. Takes the farmer's GPS coordinates, what crop
    was already farmed on the field, and crop choices from the frontend, fetches
    NASA POWER weather and USDA SSURGO soil data for that location, scores the
    farmer's chosen crops, and returns the top-ranked annual crop rotation
    sequences plus perennial site suitability.
    """
    lat_f = float(lat)
    lon_f = float(lon)
    if not (-90.0 <= lat_f <= 90.0) or not (-180.0 <= lon_f <= 180.0):
        raise ValueError(
            f"Invalid GPS coordinates (lat={lat_f}, lon={lon_f}). Latitude must be in [-90, 90] and longitude in [-180, 180]."
        )

    catalog = load_crops()

    # Step 1: Fetch NASA POWER climate data and USDA SSURGO soil data for the farm's coordinates
    nasa_result = fetch_nasa_power(
        lat=lat_f,
        lon=lon_f,
        start=start_year,
        end=end_year,
        temporal="monthly",
        use_cache=use_cache,
    )
    usda_result = fetch_usda_soil(lat=lat_f, lon=lon_f, use_cache=use_cache)

    soil_data = dict(usda_result["soil"])
    mms_telemetry = get_mms_telemetry()
    climate_data = build_climate_for_scoring(
        nasa_result,
        soil_data,
        lat=lat_f,
        lon=lon_f,
        mms_telemetry=mms_telemetry,
        sensor_overrides=sensor_overrides,
    )

    # Step 2: Resolve what crop was already farmed on this field before generating the new rotation
    previous_crop_objs = resolve_previous_crops(
        previous_crops=previous_crops,
        catalog=catalog,
        ask_if_missing=ask_previous_crop,
    )

    # Step 3: Convert the crop names, IDs, or crop types from the frontend into crop dictionaries
    farmer_crops = resolve_farmer_crops(
        selected_crops=selected_crops,
        crop_types=crop_types,
        catalog=catalog,
    )

    # Step 4: Score each chosen crop on its own and separate woody perennials into site suitability
    individual_crop_scores: list[dict[str, Any]] = []
    perennial_site_suitability: list[dict[str, Any]] = []
    for crop_obj in farmer_crops:
        single_score = score_rotation(
            crop_rows=[crop_obj],
            soil=soil_data,
            climate=climate_data,
            profile_name=profile_name,
            custom_weights=custom_weights,
            previous_crops=previous_crop_objs,
        )
        entry = {
            "crop_id": crop_obj["crop_id"],
            "crop_name": crop_obj["crop_name"],
            "crop_type": crop_obj["crop_type"],
            "is_woody_perennial": bool(crop_obj.get("is_woody_perennial", False)),
            "soil_compatibility": single_score["soil_compatibility"],
            "drainage_suitability": single_score["drainage_suitability"],
            "water_stress": single_score["water_stress"],
            "yield_potential": single_score["yield_potential"],
            "drought_tolerance": single_score["drought_tolerance"],
        }
        individual_crop_scores.append(entry)
        if bool(crop_obj.get("is_woody_perennial", False)):
            perennial_site_suitability.append(entry)

    # Step 5: If the farmer entered a specific 2 to 5 crop annual sequence, score their sequence order
    annual_selected = [c for c in farmer_crops if not bool(c.get("is_woody_perennial", False))]
    user_sequence_score: Optional[dict[str, Any]] = None
    if selected_crops and 2 <= len(annual_selected) <= 5 and len(selected_crops) <= 5:
        user_sequence_score = score_rotation(
            crop_rows=annual_selected,
            soil=soil_data,
            climate=climate_data,
            profile_name=profile_name,
            custom_weights=custom_weights,
            previous_crops=previous_crop_objs,
        )

    # Step 6: Generate valid multi-year candidate rotations tailored to the already-farmed crop and farmer pool
    candidate_sequences = build_rotations_for_farmer(
        farmer_crops=farmer_crops,
        catalog=catalog,
        rotation_length=rotation_length,
        row_crop_only=row_crop_only,
        max_water_demand_mm=max_water_demand_mm,
        previous_crops=previous_crop_objs,
    )

    # Score every candidate rotation using scoring.py (incorporating the effect of previous_crop_objs)
    scored_rotations: list[dict[str, Any]] = []
    for seq_ids in candidate_sequences:
        crop_rows = resolve_sequence_crops(seq_ids, catalog)
        if not crop_rows:
            continue
        scored = score_rotation(
            crop_rows=crop_rows,
            soil=soil_data,
            climate=climate_data,
            profile_name=profile_name,
            custom_weights=custom_weights,
            previous_crops=previous_crop_objs,
        )
        scored_rotations.append(scored)

    # Sort all scored rotations from highest to lowest total_score and slice the top_n results
    ranked_rotations = sort_rotations(scored_rotations)
    top_rotations = ranked_rotations[: max(1, int(top_n))]

    # Step 7: Run the #1 winning rotation across all 5 farmer priority profiles so the UI
    # can show how the score changes under Balanced, Max Yield, Water Conservation, etc.
    top_profile_comparison: dict[str, dict[str, Any]] = {}
    if top_rotations:
        best_ids = [cid.strip() for cid in top_rotations[0]["seq_ids"].split("->")]
        best_crop_rows = resolve_sequence_crops(best_ids, catalog)
        top_profile_comparison = compare_profiles_for_rotation(
            best_crop_rows,
            soil_data,
            climate_data,
            previous_crops=previous_crop_objs,
        )

    # Return one complete dictionary with location, soil, weather, previous crop, and rotation rankings
    return {
        "coordinates": {"lat": round(float(lat), 4), "lon": round(float(lon), 4)},
        "profile_used": profile_name if custom_weights is None else "Custom",
        "data_sources": {
            "nasa_power": nasa_result.get("source", "unknown"),
            "usda_soil": usda_result.get("source", "unknown"),
            "mms": "live" if mms_telemetry.get("connected") else "offline",
        },
        "mms_telemetry": mms_telemetry,
        "soil": {
            **soil_data,
            "baseline_soil_score": round(field_soil_baseline_score(soil_data), 3),
            "drainage_score": round(soil_drainage_score(soil_data), 3),
        },
        "climate": climate_data,
        "nasa_yearly": {
            key: nasa_result.get("summary", {}).get(key, {})
            for key in ("yearly_spring_precip_mm", "yearly_summer_precip_mm", "yearly_summer_temp_c")
        },
        "previous_crops_matched": [
            {
                "crop_id": c["crop_id"],
                "crop_name": c["crop_name"],
                "crop_type": c["crop_type"],
            }
            for c in previous_crop_objs
        ],
        "selected_crops_matched": [
            {
                "crop_id": c["crop_id"],
                "crop_name": c["crop_name"],
                "crop_type": c["crop_type"],
            }
            for c in farmer_crops
        ],
        "individual_crop_suitability": individual_crop_scores,
        "perennial_site_suitability": perennial_site_suitability,
        "user_sequence_score": user_sequence_score,
        "recommended_rotations": top_rotations,
        "top_rotation_profile_comparison": top_profile_comparison,
        "total_candidates_evaluated": len(scored_rotations),
    }


def analyze_farm_request(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Accept a raw JSON dictionary from the frontend, extract the coordinates and
    crop selections even if the frontend uses slightly different key names, and
    run analyze_location_and_crops().
    """
    coords = payload.get("coordinates") if isinstance(payload.get("coordinates"), dict) else {}
    lat = payload.get("lat", payload.get("latitude", coords.get("lat", coords.get("latitude"))))
    lon = payload.get("lon", payload.get("longitude", coords.get("lon", coords.get("longitude"))))

    if lat is None or lon is None:
        raise ValueError("Frontend request must include 'lat' and 'lon' coordinates.")

    raw_crops = payload.get("selected_crops", payload.get("crops"))
    if isinstance(raw_crops, str):
        selected_crops = [c.strip() for c in raw_crops.split(",") if c.strip()]
    elif isinstance(raw_crops, list):
        selected_crops = [str(c) for c in raw_crops]
    else:
        selected_crops = None

    raw_types = payload.get("crop_types", payload.get("crop_type"))
    if isinstance(raw_types, str):
        crop_types = [t.strip() for t in raw_types.split(",") if t.strip()]
    elif isinstance(raw_types, list):
        crop_types = [str(t) for t in raw_types]
    else:
        crop_types = None

    # Extract what crop was already farmed on the field (pushed from the frontend under any common key)
    raw_prev = None
    for prev_key in (
        "previous_crops",
        "previous_crop",
        "previousCropId",
        "already_farmed_crops",
        "already_farmed_crop",
        "already_farmed",
        "prior_crops",
        "prior_crop",
        "last_crop",
    ):
        val = payload.get(prev_key)
        if val is not None and (not isinstance(val, (str, list)) or len(val) > 0):
            raw_prev = val
            break

    previous_crops: Optional[list[str] | str]
    if isinstance(raw_prev, str):
        previous_crops = [c.strip() for c in raw_prev.split(",") if c.strip()]
    elif isinstance(raw_prev, list):
        previous_crops = [str(c).strip() for c in raw_prev if str(c).strip()]
    else:
        previous_crops = None

    return analyze_location_and_crops(
        lat=float(lat),
        lon=float(lon),
        selected_crops=selected_crops,
        crop_types=crop_types,
        previous_crops=previous_crops,
        profile_name=str(payload.get("profile_name", payload.get("profile", "Balanced"))),
        custom_weights=payload.get("custom_weights"),
        rotation_length=int(payload.get("rotation_length", payload.get("years", 3))),
        row_crop_only=bool(payload.get("row_crop_only", True)),
        max_water_demand_mm=(
            float(payload["max_water_demand_mm"])
            if payload.get("max_water_demand_mm") is not None
            else None
        ),
        top_n=int(payload.get("top_n", 5)),
        use_cache=bool(payload.get("use_cache", True)),
        sensor_overrides=payload.get("sensor_overrides"),
        ask_previous_crop=bool(payload.get("ask_previous_crop", False)),
    )


if FastAPI is not None:
    app = FastAPI(
        title="Field Shift Crop Rotation API",
        description="Fetches NASA POWER weather and USDA SSURGO soil data for a farm location and ranks crop rotations.",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class AnalyzeRequestModel(BaseModel):  # type: ignore[misc]
        lat: float = Field(..., ge=-90.0, le=90.0, description="Farm latitude in decimal degrees")
        lon: float = Field(..., ge=-180.0, le=180.0, description="Farm longitude in decimal degrees")
        previous_crop: Optional[str] = Field(
            default=None,
            description="Crop ID or crop name that was already farmed on the field last season (e.g. 'C02' or 'Field Corn')",
        )
        previous_crops: Optional[list[str]] = Field(
            default=None,
            description="Optional list of previously farmed crops ordered from older seasons to most recent",
        )
        selected_crops: Optional[list[str]] = Field(
            default=None,
            description="List of crop IDs or crop names the farmer wants to grow (e.g. ['C02', 'C03'])",
        )
        crop_types: Optional[list[str]] = Field(
            default=None,
            description="Optional list of crop families to filter by (e.g. ['grain', 'legume', 'vegetable'])",
        )
        profile_name: str = Field(
            default="Balanced",
            description="One of: Balanced, Max Yield, Water Conservation, Soil Health First, Climate Resilient",
        )
        custom_weights: Optional[dict[str, float]] = Field(
            default=None,
            description="Optional custom 7-weight dictionary overriding profile_name",
        )
        rotation_length: int = Field(default=3, ge=2, le=5)
        row_crop_only: bool = Field(default=True)
        max_water_demand_mm: Optional[float] = Field(default=None)
        top_n: int = Field(default=5, ge=1, le=20)
        sensor_overrides: Optional[dict[str, float]] = Field(
            default=None,
            description="Optional local sensor overrides (soil_moisture, soil_ph, air_temp_c, ndvi_avg)",
        )

    @app.on_event("startup")
    def boot_mms_reader() -> None:
        """Start reading the Mobile Measurement Station (MMS) when the server starts."""
        start_mms_reader()

    @app.get("/mms/latest")
    @app.get("/sensor/latest")
    def get_latest_mms_reading() -> dict[str, Any]:
        """Return live telemetry from the Mobile Measurement Station (MMS) or connected=False if offline."""
        return get_mms_telemetry()

    @app.get("/health")
    def health_check() -> dict[str, Any]:
        """Simple health check endpoint so the frontend knows the backend server is awake."""
        return {"status": "ok", "gemini": gemini_is_configured()}

    @app.get("/config")
    def public_config() -> dict[str, Any]:
        """
        Browser-safe settings. Only the Google Maps key goes out (it is locked to our sites
        in Google Cloud). GEMINI_API_KEY must never be added here, it stays backend-only.
        """
        maps_key = get_google_maps_api_key()
        return {
            "google_maps_api_key": maps_key if maps_key else None,
            "gemini_configured": gemini_is_configured(),
        }

    @app.get("/crops")
    def list_available_crops() -> dict[str, Any]:
        """Return all 17 New York crop groups so the frontend can build its selection checkboxes."""
        crops = load_crops()
        return {"count": len(crops), "crops": crops}

    @app.get("/regions")
    def list_ny_regions() -> dict[str, Any]:
        """Return New York agricultural region baselines and coordinates."""
        regions = load_ny_regions()
        return {"count": len(regions), "regions": regions}

    @app.get("/profiles")
    def list_priority_profiles() -> dict[str, Any]:
        """Return the 5 preset farmer priority profiles and their 7 weights for UI sliders."""
        return {"profiles": PROFILES}

    @app.post("/analyze")
    def analyze_endpoint(request: AnalyzeRequestModel) -> dict[str, Any]:
        """
        Receive coordinates and selected crops from the frontend via HTTP POST,
        fetch NASA weather and USDA soil data, and return ranked crop rotations.
        """
        try:
            # Convert the Pydantic request model into a plain Python dictionary
            payload = (
                request.model_dump()
                if hasattr(request, "model_dump")
                else request.dict()
            )
            return analyze_farm_request(payload)
        except ValueError as exc:
            # Return HTTP 400 Bad Request if coordinates or profile names are invalid
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    class ExplainRequestModel(BaseModel):  # type: ignore[misc]
        """What is on the dashboard right now, sent as ids and numbers so Gemini only sees clean data."""

        field_number: int = 1
        city: str = "Albany"
        profile: str = "Balanced"
        previous_crop: Optional[str] = None
        max_water: int = 550
        probe: str = "off"
        rotation: list[str] = []
        scores: dict[str, float] = {}
        total_score: float = 0.0
        years: list[int] = []
        summer_temp_c: list[float] = []
        season_rain_mm: list[float] = []

    @app.post("/explain")
    def explain_endpoint(req: ExplainRequestModel) -> dict[str, Any]:
        """Ask Gemini to put the top rotation and the climate chart into plain English."""
        if not gemini_is_configured():
            return {"enabled": False, "text": None}

        catalog = load_crops()
        rotation_crops = [c for c in (get_crop_by_id(cid, catalog) for cid in req.rotation) if c][:3]
        if len(rotation_crops) < 3:
            return {"enabled": True, "text": None}

        previous = get_crop_by_id(req.previous_crop, catalog) if req.previous_crop else None
        score_names = ("soil_health", "water_safety", "resilience", "yield_potential", "nitrogen_fixation")
        points = min(len(req.years), len(req.summer_temp_c), len(req.season_rain_mm), 10)

        facts = {
            "field": f"Field F{max(1, req.field_number):03d} near {req.city or 'a custom location'}, New York",
            "farmer_priority": req.profile if req.profile in PROFILES else "Balanced",
            "previous_crop": previous["crop_name"] if previous else "not given",
            "max_water_demand_mm_per_year": req.max_water,
            "mms_mobile_measuring_station": req.probe if req.probe in ("wet", "dry") else "not used",
            "recommended_rotation": [
                {
                    "year": i + 1,
                    "crop": c["crop_name"],
                    "type": c.get("crop_type"),
                    "water_need_mm": c.get("water_demand_mm"),
                    "fixes_nitrogen": float(c.get("nitrogen_fixation") or 0) >= 0.5,
                }
                for i, c in enumerate(rotation_crops)
            ],
            "rotation_total_score_0_to_1": round(req.total_score, 2),
            "scores_0_to_1": {k: round(float(req.scores[k]), 2) for k in score_names if k in req.scores},
            "summer_temperature_c_by_year": {str(req.years[i]): req.summer_temp_c[i] for i in range(points)},
            "growing_season_rain_mm_by_year": {str(req.years[i]): round(req.season_rain_mm[i]) for i in range(points)},
        }
        return {"enabled": True, "text": explain_dashboard(facts)}

    # Serve the dashboard too, so http://localhost:8000 runs the whole app. Must stay below the routes.
    try:
        from fastapi.staticfiles import StaticFiles

        FRONTEND_DIR = BACKEND_DIR.parent / "front end"
        if FRONTEND_DIR.is_dir():
            app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

            # Make browsers re-check the dashboard files every load, so edits to
            # app.js / api.js / maps.js show up instead of a stale cached copy
            @app.middleware("http")
            async def no_stale_frontend(request, call_next):
                response = await call_next(request)
                if request.method == "GET" and not response.headers.get("cache-control"):
                    response.headers["Cache-Control"] = "no-cache"
                return response
    except ImportError:
        pass
else:
    # Keep app set to None when FastAPI is not installed so importing main.py still works
    app = None


if __name__ == "__main__":
    # Run this file directly (python src/backend/main.py) to test a sample frontend request
    # for a Finger Lakes, NY farm where Field Corn was already farmed last season
    sample_frontend_payload = {
        "lat": 42.70,
        "lon": -76.80,
        "previous_crop": "Field Corn",
        "selected_crops": ["Field Corn", "Soybeans", "Potatoes", "Cabbage"],
        "profile_name": "Balanced",
        "rotation_length": 3,
        "top_n": 3,
    }

    # Run the full pipeline and print the results to the terminal
    result = analyze_farm_request(sample_frontend_payload)
    print("Coordinates:", result["coordinates"])
    print("Data Sources:", result["data_sources"])
    print(
        "Already Farmed Crop(s):",
        [c["crop_name"] for c in result["previous_crops_matched"]],
    )
    print("Matched Crops:", [c["crop_name"] for c in result["selected_crops_matched"]])
    print("Soil Map Unit:", result["soil"]["map_unit_name"])
    print("Top Recommended Rotations:")
    print(json.dumps(result["recommended_rotations"], indent=2))
