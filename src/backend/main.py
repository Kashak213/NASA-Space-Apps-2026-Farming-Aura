"""
FastAPI server that connects the Farming Aura dashboard to the Python scoring engine and NASA POWER.
Run it from this folder with: uvicorn main:app --reload
Then open http://localhost:8000 to get the dashboard with the backend plugged in.
"""

import sys
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BACKEND_DIR.parent / "front end"

# lets the imports below work whether uvicorn is started here or from the repo root
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from nasa_client import fetch_nasa_power  # noqa: E402
from scoring import CITIES, CROPS, FIELDS, rank_rotations  # noqa: E402

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
    return {"ok": True, "crops": len(CROPS), "fields": len(FIELDS)}


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


# serve the dashboard itself so one command runs the whole app, this has to stay below the routes
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
