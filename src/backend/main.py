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

# Import the 7-weight scoring functions and preset farmer priority profiles from scoring.py
from scoring import (
    PROFILES,
    compare_profiles_for_rotation,
    field_soil_baseline_score,
    score_rotation,
    soil_drainage_score,
    sort_rotations,
)

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
    # Load all 13 New York crops from data/crops.json if a catalog list was not passed in
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

            # Try matching by crop ID first (for example "C01" through "C13")
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


def build_climate_for_scoring(
    nasa_response: dict[str, Any],
    soil_data: dict[str, Any],
    lat: float = 42.70,
    lon: float = -76.80,
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

    t2m_series = raw_params.get("T2M", {})
    summer_temps = [
        float(val)
        for key, val in t2m_series.items()
        if len(str(key)) == 6 and str(key)[4:6] in ("06", "07", "08")
    ]
    summer_temp_c = (
        round(sum(summer_temps) / len(summer_temps), 2)
        if summer_temps
        else float(summary.get("summer_temp_c") or summary.get("t2m_avg_c") or 21.0)
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

    moisture_factor = min(1.0, soil_moisture_avg / 0.34)
    solar_factor = min(1.0, growing_solar / 18.5)
    thermal_factor = max(0.4, min(1.0, (growing_temp_c - 8.0) / 11.0))
    estimated_ndvi = round(
        max(
            0.35,
            min(
                0.88,
                0.25 + 0.58 * (0.45 * moisture_factor + 0.30 * solar_factor + 0.25 * thermal_factor),
            ),
        ),
        3,
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

    if sensor_overrides and isinstance(sensor_overrides, dict):
        if sensor_overrides.get("soil_moisture") is not None:
            sm_val = float(sensor_overrides["soil_moisture"])
            if sm_val > 1.0:
                sm_val = sm_val / 100.0
            climate_dict["soil_moisture_avg"] = round(max(0.05, min(0.60, sm_val)), 3)
            climate_dict["drought_index"] = round(
                max(0.05, min(0.90, 1.0 - (climate_dict["soil_moisture_avg"] / 0.42))),
                3,
            )
        if sensor_overrides.get("air_temp_c") is not None:
            climate_dict["growing_season_temp_c"] = round(float(sensor_overrides["air_temp_c"]), 2)
        if sensor_overrides.get("ndvi_avg") is not None:
            climate_dict["ndvi_avg"] = round(float(sensor_overrides["ndvi_avg"]), 3)
        if sensor_overrides.get("soil_ph") is not None:
            soil_data["ph"] = round(float(sensor_overrides["soil_ph"]), 2)

    return climate_dict


def build_rotations_for_farmer(
    farmer_crops: list[dict[str, Any]],
    catalog: list[dict[str, Any]],
    rotation_length: int = 3,
    row_crop_only: bool = False,
    max_water_demand_mm: Optional[float] = None,
) -> list[list[str]]:
    """
    Create candidate multi-year crop sequences tailored to the crops the farmer
    selected. If the farmer picked at least 2 crops, we build sequences from
    their chosen pool plus complementary nitrogen-fixing legumes when needed.
    """
    # Clamp rotation length between 2 and 5 years so combinations stay fast and practical
    length = max(2, min(5, int(rotation_length)))
    farmer_ids = [str(c["crop_id"]) for c in farmer_crops]

    # Attempt 1: Build valid rotations using only the exact crops the farmer selected
    candidates = generate_candidate_rotations(
        crops=farmer_crops,
        length=length,
        row_crop_only=row_crop_only,
        max_water_demand_mm=max_water_demand_mm,
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
        )
        # Keep only candidate sequences that contain at least one crop the farmer asked for
        wanted_set = set(farmer_ids)
        candidates = [seq for seq in all_generated if any(cid in wanted_set for cid in seq)]

    # Attempt 3: Build non-repeating permutations from the farmer's annual/forage crops
    annual_farmer_ids = [cid for cid in farmer_ids if cid not in WOODY_PERENNIAL_IDS]
    if not candidates and len(annual_farmer_ids) >= 2:
        perm_len = min(length, len(annual_farmer_ids))
        candidates = [list(p) for p in itertools.permutations(annual_farmer_ids, perm_len)]

    # Attempt 4: Fall back to preset New York annual rotations
    if not candidates:
        candidates = list(PRESET_ROTATIONS)

    return candidates


def analyze_location_and_crops(
    lat: float,
    lon: float,
    selected_crops: Optional[list[str]] = None,
    crop_types: Optional[list[str]] = None,
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
) -> dict[str, Any]:
    """
    Main backend pipeline function. Takes the farmer's GPS coordinates and crop
    choices from the frontend, fetches NASA POWER weather and USDA SSURGO soil
    data for that location, scores the farmer's chosen crops, and returns the
    top-ranked annual crop rotation sequences plus perennial site suitability.
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
    climate_data = build_climate_for_scoring(
        nasa_result,
        soil_data,
        lat=lat_f,
        lon=lon_f,
        sensor_overrides=sensor_overrides,
    )

    # Step 2: Convert the crop names, IDs, or crop types from the frontend into crop dictionaries
    farmer_crops = resolve_farmer_crops(
        selected_crops=selected_crops,
        crop_types=crop_types,
        catalog=catalog,
    )

    # Step 3: Score each chosen crop on its own and separate woody perennials into site suitability
    individual_crop_scores: list[dict[str, Any]] = []
    perennial_site_suitability: list[dict[str, Any]] = []
    for crop_obj in farmer_crops:
        single_score = score_rotation(
            crop_rows=[crop_obj],
            soil=soil_data,
            climate=climate_data,
            profile_name=profile_name,
            custom_weights=custom_weights,
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

    # Step 4: If the farmer entered a specific 2 to 5 crop annual sequence, score their sequence order
    annual_selected = [c for c in farmer_crops if not bool(c.get("is_woody_perennial", False))]
    user_sequence_score: Optional[dict[str, Any]] = None
    if selected_crops and 2 <= len(annual_selected) <= 5 and len(selected_crops) <= 5:
        user_sequence_score = score_rotation(
            crop_rows=annual_selected,
            soil=soil_data,
            climate=climate_data,
            profile_name=profile_name,
            custom_weights=custom_weights,
        )

    # Step 5: Generate valid multi-year candidate rotations from the farmer's crop pool
    candidate_sequences = build_rotations_for_farmer(
        farmer_crops=farmer_crops,
        catalog=catalog,
        rotation_length=rotation_length,
        row_crop_only=row_crop_only,
        max_water_demand_mm=max_water_demand_mm,
    )

    # Score every candidate rotation using scoring.py
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
        )
        scored_rotations.append(scored)

    # Sort all scored rotations from highest to lowest total_score and slice the top_n results
    ranked_rotations = sort_rotations(scored_rotations)
    top_rotations = ranked_rotations[: max(1, int(top_n))]

    # Step 6: Run the #1 winning rotation across all 5 farmer priority profiles so the UI
    # can show how the score changes under Balanced, Max Yield, Water Conservation, etc.
    top_profile_comparison: dict[str, dict[str, Any]] = {}
    if top_rotations:
        best_ids = [cid.strip() for cid in top_rotations[0]["seq_ids"].split("->")]
        best_crop_rows = resolve_sequence_crops(best_ids, catalog)
        top_profile_comparison = compare_profiles_for_rotation(
            best_crop_rows, soil_data, climate_data
        )

    # Return one complete dictionary with location, soil, weather, and rotation rankings for the UI
    return {
        "coordinates": {"lat": round(float(lat), 4), "lon": round(float(lon), 4)},
        "profile_used": profile_name if custom_weights is None else "Custom",
        "data_sources": {
            "nasa_power": nasa_result.get("source", "unknown"),
            "usda_soil": usda_result.get("source", "unknown"),
        },
        "soil": {
            **soil_data,
            "baseline_soil_score": round(field_soil_baseline_score(soil_data), 3),
            "drainage_score": round(soil_drainage_score(soil_data), 3),
        },
        "climate": climate_data,
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

    return analyze_location_and_crops(
        lat=float(lat),
        lon=float(lon),
        selected_crops=selected_crops,
        crop_types=crop_types,
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

    @app.get("/health")
    def health_check() -> dict[str, str]:
        """Simple health check endpoint so the frontend knows the backend server is awake."""
        return {"status": "ok"}

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
else:
    # Keep app set to None when FastAPI is not installed so importing main.py still works
    app = None


if __name__ == "__main__":
    # Run this file directly (python src/backend/main.py) to test a sample frontend request
    # for a Finger Lakes, NY farm growing Field Corn, Soybeans, Potatoes, and Cabbage
    sample_frontend_payload = {
        "lat": 42.70,
        "lon": -76.80,
        "selected_crops": ["Field Corn", "Soybeans", "Potatoes", "Cabbage"],
        "profile_name": "Balanced",
        "rotation_length": 3,
        "top_n": 3,
    }

    # Run the full pipeline and print the results to the terminal
    result = analyze_farm_request(sample_frontend_payload)
    print("Coordinates:", result["coordinates"])
    print("Data Sources:", result["data_sources"])
    print("Matched Crops:", [c["crop_name"] for c in result["selected_crops_matched"]])
    print("Soil Map Unit:", result["soil"]["map_unit_name"])
    print("Top Recommended Rotations:")
    print(json.dumps(result["recommended_rotations"], indent=2))
