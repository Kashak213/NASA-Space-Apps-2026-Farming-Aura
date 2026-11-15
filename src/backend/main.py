"""
FastAPI server that connects the Farming Aura dashboard to the Python scoring engine and NASA POWER.
Run it from this folder with: uvicorn main:app --reload
Then open http://localhost:8000 to get the dashboard with the backend plugged in.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BACKEND_DIR.parent / "front end"

# lets the imports below work whether uvicorn is started here or from the repo root
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from gemini_client import explain_dashboard, gemini_is_configured  # noqa: E402
from nasa_client import fetch_nasa_power  # noqa: E402
from scoring import CITIES, CROPS, FIELDS, PRIORITY_PROFILES, rank_rotations  # noqa: E402

app = FastAPI(title="Farming Aura API")

# the dashboard on GitHub Pages or a local Live Server is a different origin, so the browser needs CORS turned on
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DAYS_IN_MONTH = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
SPRING_MONTHS = (3, 4, 5)
SUMMER_MONTHS = (6, 7, 8)

# NASA answers get remembered per location so moving a slider doesn't hit their API again
_nasa_memory = {}


def season_rain_mm(precip_series, year, months):
    """Turn NASA's monthly mm/day averages into total mm of rain for one season."""
    total = 0.0
    found = 0
    for month in months:
        value = precip_series.get(f"{year}{month:02d}")
        if value is not None:
            total += value * DAYS_IN_MONTH[month]
            found += 1
    return round(total) if found == len(months) else None


def get_nasa_field_update(lat, lon):
    """Ask NASA POWER for 2023 and 2024 weather at this spot and shape it like our field records."""
    key = (round(lat, 2), round(lon, 2))
    if key in _nasa_memory:
        return _nasa_memory[key]

    result = {"source": "demo", "field_update": None, "summary": None}
    try:
        nasa = fetch_nasa_power(lat=key[0], lon=key[1], start=2023, end=2024, timeout=6)
        rain = nasa["data"].get("PRECTOTCORR", {})
        temp = nasa["data"].get("T2M", {})
        summer_temps = [temp[f"2024{m:02d}"] for m in SUMMER_MONTHS if f"2024{m:02d}" in temp]
        update = {
            "spring2023Precip": season_rain_mm(rain, 2023, SPRING_MONTHS),
            "summer2023Precip": season_rain_mm(rain, 2023, SUMMER_MONTHS),
            "spring2024Precip": season_rain_mm(rain, 2024, SPRING_MONTHS),
            "summer2024Precip": season_rain_mm(rain, 2024, SUMMER_MONTHS),
            "tempSummer": round(sum(summer_temps) / len(summer_temps), 1) if summer_temps else None,
        }
        # only trust the update if NASA gave us every number we need
        if all(v is not None for v in update.values()):
            result = {"source": nasa["source"], "field_update": update, "summary": nasa["summary"]}
    except Exception:
        # no wifi and no cached file for this spot, so the field keeps its sample numbers
        pass

    # a failed lookup is not remembered so it can work once the wifi comes back
    if result["field_update"] is not None:
        _nasa_memory[key] = result
    return result


class AnalyzeRequest(BaseModel):
    """Everything the farmer picked in the dashboard."""

    field_id: str = "F001"
    city: str = "Albany"
    lat: Optional[float] = None
    lon: Optional[float] = None
    profile: str = "Balanced"
    intensity: int = 50
    selected_crops: List[str] = ["C01", "C02", "C03"]
    previous_crop: Optional[str] = "C02"
    max_water: int = 550
    dry_probe: bool = False
    use_nasa: bool = True


@app.get("/health")
def health():
    return {"ok": True, "crops": len(CROPS), "fields": len(FIELDS), "gemini": gemini_is_configured()}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    """Score every candidate rotation for this farmer and send them back best first."""
    field = dict(FIELDS.get(req.field_id, FIELDS["F001"]))

    # use the typed coordinates if there are any, otherwise the city's
    city = CITIES.get(req.city, CITIES["Albany"])
    lat = req.lat if req.lat is not None else float(city["lat"])
    lon = req.lon if req.lon is not None else float(city["lon"])

    nasa = {"source": "demo", "field_update": None, "summary": None}
    if req.use_nasa:
        nasa = get_nasa_field_update(lat, lon)
        if nasa["field_update"]:
            # real NASA rain and summer temperature replace the sample values before scoring
            field.update(nasa["field_update"])

    ranked = rank_rotations(
        field,
        req.selected_crops,
        profile_name=req.profile,
        intensity=req.intensity,
        previous_crop_id=req.previous_crop,
        max_water=req.max_water,
        dry_probe=req.dry_probe,
    )

    return {
        "engine": "backend",
        "nasa_source": nasa["source"],
        "nasa_summary": nasa["summary"],
        "coordinates": {"lat": lat, "lon": lon},
        "field_id": field["id"],
        "field_update": nasa["field_update"],
        "ranked": ranked,
    }


class ExplainRequest(BaseModel):
    """What is on the dashboard right now, sent as ids and numbers so Gemini only sees clean data."""

    field_number: int = 1
    city: str = "Albany"
    profile: str = "Balanced"
    previous_crop: Optional[str] = None
    max_water: int = 550
    probe: str = "off"
    rotation: List[str] = []
    scores: Dict[str, float] = {}
    total_score: float = 0.0
    years: List[int] = []
    summer_temp_c: List[float] = []
    season_rain_mm: List[float] = []


@app.post("/explain")
def explain(req: ExplainRequest):
    """Ask Gemini to put the top rotation and the climate chart into plain English."""
    if not gemini_is_configured():
        return {"enabled": False, "text": None}

    rotation_crops = [CROPS[cid] for cid in req.rotation if cid in CROPS][:3]
    if len(rotation_crops) < 3:
        return {"enabled": True, "text": None}

    city = CITIES.get(req.city)
    previous = CROPS.get(req.previous_crop) if req.previous_crop else None
    score_names = ("soil_health", "water_safety", "resilience", "yield_potential", "nitrogen_fixation")
    points = min(len(req.years), len(req.summer_temp_c), len(req.season_rain_mm), 10)

    facts = {
        "field": f"Field F{max(1, req.field_number):03d} near {city['label'] if city else 'a custom location in New York'}",
        "farmer_priority": req.profile if req.profile in PRIORITY_PROFILES else "Balanced",
        "previous_crop": previous["name"] if previous else "not given",
        "max_water_demand_mm_per_year": req.max_water,
        "moisture_probe": req.probe if req.probe in ("wet", "dry") else "not used",
        "recommended_rotation": [
            {
                "year": i + 1,
                "crop": c["name"],
                "role": c["roleTag"],
                "water_need_mm": c["water"],
                "fixes_nitrogen": c["nFix"] >= 0.5,
            }
            for i, c in enumerate(rotation_crops)
        ],
        "rotation_total_score_0_to_1": round(req.total_score, 2),
        "scores_0_to_1": {k: round(float(req.scores[k]), 2) for k in score_names if k in req.scores},
        "summer_temperature_c_by_year": {str(req.years[i]): req.summer_temp_c[i] for i in range(points)},
        "growing_season_rain_mm_by_year": {str(req.years[i]): round(req.season_rain_mm[i]) for i in range(points)},
    }
    return {"enabled": True, "text": explain_dashboard(facts)}


# serve the dashboard itself so one command runs the whole app, this has to stay below the routes
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
