"""
Backend coordinator and API entry point for the crop rotation planner.

Receives farm coordinates (latitude and longitude) and the farmer's chosen
crops or crop types from the frontend, fetches weather data from NASA POWER
(nasa_client.py) and soil properties from USDA SSURGO (fetch_soil.py), and
runs the rotation scoring engine (scoring.py) to return ranked crop rotation
recommendations.
"""

from __future__ import annotations

# Standard library imports for building crop combinations and printing JSON test output
import itertools
import json
import math
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional

# Ensure both src/ and src/backend/ are on sys.path so imports work from any working directory
BACKEND_DIR = Path(__file__).resolve().parent
SRC_DIR = BACKEND_DIR.parent
for _p in (str(BACKEND_DIR), str(SRC_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Import the Google Maps API key helper from src/config.py (.env and Hugging Face Secrets)
from config import get_google_maps_api_key

# Import crop lookup helpers and rotation generators from crops.py
from crops import (
    PRESET_ROTATIONS,
    generate_candidate_rotations,
    get_crop_by_id,
    get_crop_by_name,
    load_crops,
    resolve_sequence_crops,
)

# Import the USDA NRCS Soil Data Access client to get field soil lab metrics
from fetch_soil import fetch_usda_soil

# Import the NASA POWER client to get sunlight, wind speed, rainfall, and temperature
from nasa_client import fetch_nasa_power

# Import the Mobile Measurement Station (MMS) serial telemetry reader
from mms_sensor import get_mms_telemetry, start_mms_reader

# Import the 7-weight scoring functions and preset farmer priority profiles from scoring.py
from scoring import (
    PROFILES,
    compare_profiles_for_rotation,
    field_soil_baseline_score,
    score_rotation,
    sort_rotations,
)

# Try importing FastAPI and Pydantic so main.py can run as an HTTP web server,
# while still working as a normal Python module for Streamlit or terminal tests
# even when FastAPI is not installed on a teammate's laptop yet
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel, Field
except ImportError:
    FastAPI = None
    HTTPException = None
    CORSMiddleware = None
    HTMLResponse = None
    BaseModel = object
    Field = None


def compute_polygon_centroid_and_acres(polygon_points: list[dict[str, Any]]) -> dict[str, float]:
    """
    Calculate the center latitude, center longitude, and land area in acres and
    hectares for a farm outline or field sector polygon drawn on Google Maps.
    """
    cleaned: list[tuple[float, float]] = []
    for pt in polygon_points or []:
        if not isinstance(pt, dict):
            continue
        pt_lat = pt.get("lat", pt.get("latitude"))
        pt_lon = pt.get("lon", pt.get("lng", pt.get("longitude")))
        if pt_lat is not None and pt_lon is not None:
            cleaned.append((float(pt_lat), float(pt_lon)))

    if not cleaned:
        raise ValueError("Polygon must contain at least one coordinate with lat and lon/lng.")

    avg_lat = sum(p[0] for p in cleaned) / len(cleaned)
    avg_lon = sum(p[1] for p in cleaned) / len(cleaned)

    # Need at least 3 corners to enclose a 2D field polygon for area math
    if len(cleaned) < 3:
        return {
            "lat": round(avg_lat, 6),
            "lon": round(avg_lon, 6),
            "area_acres": 0.0,
            "area_hectares": 0.0,
        }

    # Convert degrees to local meters around avg_lat and apply the shoelace polygon area formula
    meters_per_deg_lat = 111132.92
    meters_per_deg_lon = 111412.84 * math.cos(math.radians(avg_lat))

    shoelace_sum = 0.0
    n = len(cleaned)
    for i in range(n):
        lat1, lon1 = cleaned[i]
        lat2, lon2 = cleaned[(i + 1) % n]
        x1 = (lon1 - avg_lon) * meters_per_deg_lon
        y1 = (lat1 - avg_lat) * meters_per_deg_lat
        x2 = (lon2 - avg_lon) * meters_per_deg_lon
        y2 = (lat2 - avg_lat) * meters_per_deg_lat
        shoelace_sum += (x1 * y2) - (x2 * y1)

    area_sq_meters = abs(shoelace_sum) * 0.5
    area_acres = area_sq_meters / 4046.8564224
    area_hectares = area_sq_meters / 10000.0

    return {
        "lat": round(avg_lat, 6),
        "lon": round(avg_lon, 6),
        "area_acres": round(area_acres, 2),
        "area_hectares": round(area_hectares, 2),
    }


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
    mms_telemetry: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Combine the NASA POWER summary dictionary with estimated soil moisture and
    drought index values so scoring.py has every climate key it needs. If the
    Mobile Measurement Station (MMS) is connected, blend its live ground-truth
    readings into soil moisture, temperature, and drought index.
    """
    # Pull the averaged summary metrics and raw monthly time series from the NASA POWER response
    summary = dict(nasa_response.get("summary", {}))
    raw_params = nasa_response.get("data", {})

    # Read estimated yearly rainfall (mm/year), defaulting to 900 mm (normal NY rain) if missing
    annual_precip = summary.get("estimated_annual_precip_mm")
    if annual_precip is None:
        annual_precip = 900.0

    # Calculate summer average temperature (Celsius) from June ("06"), July ("07"), and August ("08")
    # because scoring.py checks summer heat stress in climate_resilience_score()
    t2m_series = raw_params.get("T2M", {})
    summer_temps = [
        float(val)
        for key, val in t2m_series.items()
        if len(str(key)) == 6 and str(key)[4:6] in ("06", "07", "08")
    ]
    summer_temp_c = (
        round(sum(summer_temps) / len(summer_temps), 2)
        if summer_temps
        else float(summary.get("t2m_avg_c") or 22.0)
    )

    # Compare the field's annual rainfall against a 950 mm New York baseline to estimate a
    # 0.0 to 1.0 drought index (where lower numbers mean wetter, safer conditions)
    precip_ratio = float(annual_precip) / 950.0
    drought_index = round(max(0.05, min(0.85, 1.0 - 0.65 * precip_ratio)), 3)

    # Estimate average topsoil moisture (m3/m3) by combining USDA available water capacity (awc)
    # with the rainfall ratio so wetter soils with higher water-holding capacity score higher
    awc = float(soil_data.get("awc", 0.18))
    soil_moisture_avg = round(max(0.12, min(0.48, (awc * 1.4) + 0.08 * precip_ratio)), 3)

    # If the Mobile Measurement Station (MMS) is connected, incorporate its live readings
    soil_temp_c: Optional[float] = None
    air_humidity_pct: Optional[float] = None
    is_raining = False
    if mms_telemetry and mms_telemetry.get("connected"):
        latest = mms_telemetry.get("latest") or {}
        mms_moist_m3 = latest.get("soil_moisture_m3")
        if mms_moist_m3 is not None:
            # Blend 70% live MMS ground-truth root-zone moisture with 30% satellite/soil baseline
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

    # Calculate how far above or below normal (950 mm) the yearly rainfall is as a percentage
    anomaly_precip_pct = round(((float(annual_precip) - 950.0) / 950.0) * 100.0, 1)

    # Return the complete dictionary formatted for scoring.py
    return {
        "allsky_sfc_sw_dwn_avg": summary.get("allsky_sfc_sw_dwn_avg") or 14.0,
        "ws2m_avg_m_s": summary.get("ws2m_avg_m_s") or 3.0,
        "prectotcorr_avg_mm_day": summary.get("prectotcorr_avg_mm_day") or 2.6,
        "annual_precip_mm": float(annual_precip),
        "estimated_annual_precip_mm": float(annual_precip),
        "t2m_avg_c": summary.get("t2m_avg_c") or 10.0,
        "summer_temp_c": summer_temp_c,
        "soil_temp_c": soil_temp_c,
        "air_humidity_pct": air_humidity_pct,
        "is_raining": is_raining,
        "drought_index": drought_index,
        "soil_moisture_avg": soil_moisture_avg,
        "anomaly_precip_pct": anomaly_precip_pct,
        "ndvi_avg": 0.72,
        "drought_trend": 0.0,
        "precip_anom_trend": 0.0,
    }


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

    # Attempt 3: If the farmer picked perennial crops (like Apples, Grapes, and Berries) that
    # do not include a legume, build non-repeating permutations from their selected crop IDs
    if not candidates and len(farmer_ids) >= 2:
        perm_len = min(length, len(farmer_ids))
        candidates = [list(p) for p in itertools.permutations(farmer_ids, perm_len)]

    # Attempt 4: If the farmer only picked 1 crop and nothing else matched, use preset NY rotations
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
    row_crop_only: bool = False,
    max_water_demand_mm: Optional[float] = None,
    top_n: int = 5,
    start_year: int = 2023,
    end_year: int = 2024,
    use_cache: bool = True,
) -> dict[str, Any]:
    """
    Main backend pipeline function. Takes the farmer's GPS coordinates and crop
    choices from the frontend, fetches NASA POWER weather and USDA SSURGO soil
    data for that location, scores the farmer's chosen crops, and returns the
    top-ranked crop rotation sequences.
    """
    # Load the full 13-crop New York catalog from data/crops.json
    catalog = load_crops()

    # Step 1: Fetch NASA POWER climate data and USDA SSURGO soil data for the farm's coordinates
    nasa_result = fetch_nasa_power(
        lat=lat,
        lon=lon,
        start=start_year,
        end=end_year,
        temporal="monthly",
        use_cache=use_cache,
    )
    usda_result = fetch_usda_soil(lat=lat, lon=lon, use_cache=use_cache)

    # Extract the normalized soil dictionary and check if the Mobile Measurement Station (MMS) is connected
    soil_data = usda_result["soil"]
    mms_telemetry = get_mms_telemetry()
    climate_data = build_climate_for_scoring(nasa_result, soil_data, mms_telemetry=mms_telemetry)

    # Step 2: Convert the crop names, IDs, or crop types from the frontend into crop dictionaries
    farmer_crops = resolve_farmer_crops(
        selected_crops=selected_crops,
        crop_types=crop_types,
        catalog=catalog,
    )

    # Step 3: Score each chosen crop on its own so the frontend can show how well each
    # individual crop fits this farm's soil pH, clay percentage, rainfall, and sunlight
    individual_crop_scores: list[dict[str, Any]] = []
    for crop_obj in farmer_crops:
        single_score = score_rotation(
            crop_rows=[crop_obj],
            soil=soil_data,
            climate=climate_data,
            profile_name=profile_name,
            custom_weights=custom_weights,
        )
        individual_crop_scores.append(
            {
                "crop_id": crop_obj["crop_id"],
                "crop_name": crop_obj["crop_name"],
                "crop_type": crop_obj["crop_type"],
                "soil_compatibility": single_score["soil_compatibility"],
                "water_stress": single_score["water_stress"],
                "yield_potential": single_score["yield_potential"],
                "drought_tolerance": single_score["drought_tolerance"],
            }
        )

    # Step 4: If the farmer selected 2 or more specific crops, score them in the exact order
    # they entered so they can compare their own sequence against our optimized recommendations
    user_sequence_score: Optional[dict[str, Any]] = None
    if selected_crops and len(farmer_crops) >= 2:
        user_sequence_score = score_rotation(
            crop_rows=farmer_crops,
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
            "mms": "live" if mms_telemetry.get("connected") else "offline",
        },
        "mms_telemetry": mms_telemetry,
        "soil": {
            **soil_data,
            "baseline_soil_score": round(field_soil_baseline_score(soil_data), 3),
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
    # Check if the frontend nested coordinates inside {"coordinates": {"lat": ..., "lon": ...}}
    # or passed them at the top level as {"lat": ..., "lon": ...} or {"latitude": ..., "longitude": ...}
    coords = payload.get("coordinates") if isinstance(payload.get("coordinates"), dict) else {}
    lat = payload.get("lat", payload.get("latitude", coords.get("lat", coords.get("latitude"))))
    lon = payload.get("lon", payload.get("longitude", coords.get("lon", coords.get("longitude"))))

    # Raise a clear error if either latitude or longitude is missing from the frontend request
    if lat is None or lon is None:
        raise ValueError("Frontend request must include 'lat' and 'lon' coordinates.")

    # Read the farmer's chosen crops from either "selected_crops" or "crops".
    # If the frontend sent a comma-separated string like "Field Corn, Soybeans", split it into a list.
    raw_crops = payload.get("selected_crops", payload.get("crops"))
    if isinstance(raw_crops, str):
        selected_crops = [c.strip() for c in raw_crops.split(",") if c.strip()]
    elif isinstance(raw_crops, list):
        selected_crops = [str(c) for c in raw_crops]
    else:
        selected_crops = None

    # Read optional crop family types from "crop_types" or "crop_type" (like ["grain", "legume"])
    raw_types = payload.get("crop_types", payload.get("crop_type"))
    if isinstance(raw_types, str):
        crop_types = [t.strip() for t in raw_types.split(",") if t.strip()]
    elif isinstance(raw_types, list):
        crop_types = [str(t) for t in raw_types]
    else:
        crop_types = None

    # Pass all cleaned frontend inputs into our main analysis pipeline
    return analyze_location_and_crops(
        lat=float(lat),
        lon=float(lon),
        selected_crops=selected_crops,
        crop_types=crop_types,
        profile_name=str(payload.get("profile_name", payload.get("profile", "Balanced"))),
        custom_weights=payload.get("custom_weights"),
        rotation_length=int(payload.get("rotation_length", payload.get("years", 3))),
        row_crop_only=bool(payload.get("row_crop_only", False)),
        max_water_demand_mm=(
            float(payload["max_water_demand_mm"])
            if payload.get("max_water_demand_mm") is not None
            else None
        ),
        top_n=int(payload.get("top_n", 5)),
        use_cache=bool(payload.get("use_cache", True)),
    )


def get_frontend_config_payload() -> dict[str, Any]:
    """
    Return the Google Maps API key from .env or Hugging Face Spaces Secrets so the
    frontend can load the interactive Google Satellite map and fall back to Leaflet
    only when no key is configured.
    """
    gmaps_key = get_google_maps_api_key()
    return {
        "google_maps_api_key": gmaps_key,
        "has_google_maps_key": bool(gmaps_key),
    }


def load_ui_html() -> str:
    """Read the interactive map and crop rotation planner HTML file from src/ui/index.html."""
    ui_path = SRC_DIR / "ui" / "index.html"
    if ui_path.is_file():
        return ui_path.read_text(encoding="utf-8")
    return "<html><body><h2>Field Shift UI not found at src/ui/index.html</h2></body></html>"


# If FastAPI is installed in the environment, set up the HTTP web server and routes
if FastAPI is not None:
    # Create the FastAPI application instance
    app = FastAPI(
        title="Field Shift Crop Rotation API",
        description="Fetches NASA POWER weather and USDA SSURGO soil data for a farm location and ranks crop rotations.",
        version="1.0.0",
    )

    # Enable CORS so a browser or Streamlit frontend running on another port can call this API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Define the expected JSON request body for POST /analyze using Pydantic
    class AnalyzeRequestModel(BaseModel):  # type: ignore[misc]
        lat: Optional[float] = Field(default=None, description="Farm latitude in decimal degrees")
        lon: Optional[float] = Field(default=None, description="Farm longitude in decimal degrees")
        farm_boundary: Optional[list[dict[str, float]]] = Field(
            default=None,
            description="Optional list of {lat, lng} vertices for the farm outline polygon drawn on Google Maps",
        )
        sectors: Optional[list[dict[str, Any]]] = Field(
            default=None,
            description="Optional list of highlighted field sector polygons inside the farm",
        )
        selected_crops: Optional[list[str]] = Field(
            default=None,
            description="List of crop IDs or crop names the farmer wants to grow (e.g. ['C02', 'C03'] or ['Field Corn', 'Soybeans'])",
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
        row_crop_only: bool = Field(default=False)
        max_water_demand_mm: Optional[float] = Field(default=None)
        top_n: int = Field(default=5, ge=1, le=20)

    @app.get("/", response_class=HTMLResponse)
    def serve_frontend_ui() -> Any:
        """Serve the interactive Google Maps farm outline and sector selector web app."""
        return HTMLResponse(content=load_ui_html())

    @app.get("/config")
    def get_public_config() -> dict[str, Any]:
        """Return the Google Maps API key loaded from .env or Hugging Face Spaces Secrets."""
        return get_frontend_config_payload()

    @app.get("/health")
    def health_check() -> dict[str, str]:
        """Simple health check endpoint so the frontend knows the backend server is awake."""
        return {"status": "ok"}

    @app.get("/crops")
    def list_available_crops() -> dict[str, Any]:
        """Return all 13 New York crops so the frontend can build its crop selection checkboxes."""
        crops = load_crops()
        return {"count": len(crops), "crops": crops}

    @app.get("/profiles")
    def list_priority_profiles() -> dict[str, Any]:
        """Return the 5 preset farmer priority profiles and their 7 weights for UI sliders."""
        return {"profiles": PROFILES}

    @app.get("/mms/latest")
    @app.get("/sensor/latest")
    def get_latest_mms_reading() -> dict[str, Any]:
        """Return live telemetry from the Mobile Measurement Station (MMS) or connected=False if offline."""
        return get_mms_telemetry()

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

    # Start reading the Mobile Measurement Station (MMS) as soon as the server boots.
    # If the MMS is not plugged in, get_mms_telemetry() just reports connected=False.
    @app.on_event("startup")
    def boot_mms_reader() -> None:
        start_mms_reader()

    # Serve the frontend from the same server so one command runs the whole demo.
    # This goes last so the API routes above take priority over the static files.
    _frontend_dir = Path(__file__).resolve().parent.parent / "front end"
    if _frontend_dir.exists():
        from fastapi.staticfiles import StaticFiles

        app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
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
