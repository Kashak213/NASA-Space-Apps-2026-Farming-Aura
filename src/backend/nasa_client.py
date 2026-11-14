"""
NASA POWER API client for fetching field weather and solar data.

Connects to the NASA POWER agroclimatology endpoint to pull solar irradiance,
wind speed, precipitation, and air temperature for a given latitude and
longitude, strips -999 fill values, and saves a local cache copy in
data/nasa_cache for offline demo backup.
"""

from __future__ import annotations

import json
import statistics
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

# Try to import requests first since it is in requirements.txt,
# but fall back to Python's built-in urllib if requests is not installed yet
try:
    import requests
except ImportError:
    requests = None

# Point to src/backend/ and the local offline cache folder src/backend/data/nasa_cache/
BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "data" / "nasa_cache"

# Official NASA POWER REST endpoints for daily and monthly point queries
NASA_POWER_DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_POWER_MONTHLY_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"

# Exact NASA POWER parameter codes we request from the Agroclimatology (AG) community.
# ALLSKY_SFC_SW_DWN measures sunlight hitting the ground for photosynthesis,
# WS2M measures wind speed at 2 meters which affects plant transpiration,
# PRECTOTCORR measures corrected daily rainfall in mm/day,
# and T2M measures air temperature at 2 meters in degrees Celsius.
NASA_PARAMETERS: tuple[str, ...] = (
    "ALLSKY_SFC_SW_DWN",
    "WS2M",
    "PRECTOTCORR",
    "T2M",
)

# Readable names for each NASA code so the frontend or logs are easy to read
PARAMETER_LABELS: dict[str, str] = {
    "ALLSKY_SFC_SW_DWN": "All Sky Surface Shortwave Downward Irradiance",
    "WS2M": "Wind Speed at 2 Meters",
    "PRECTOTCORR": "Precipitation Corrected",
    "T2M": "Temperature at 2 Meters",
}


def _http_get_json(url: str, params: dict[str, Any], timeout: int = 10) -> dict[str, Any]:
    """Send an HTTP GET request to NASA POWER and return the parsed JSON dictionary."""
    # If the requests library is installed, use it to send the query parameters
    if requests is not None:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    # Otherwise build the query string manually and use standard library urllib
    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"
    req = urllib.request.Request(full_url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def strip_fill_values(
    raw_parameter_block: dict[str, dict[str, float]],
    fill_threshold: float = -900.0,
) -> dict[str, dict[str, float]]:
    """
    Remove NASA POWER -999 missing-data fill values and annual summary keys
    ending in 13 from each parameter time series.
    """
    cleaned: dict[str, dict[str, float]] = {}

    # Loop through each weather variable (for example T2M or PRECTOTCORR)
    for param_code, series in raw_parameter_block.items():
        if not isinstance(series, dict):
            continue

        valid_points: dict[str, float] = {}
        for date_key, value in series.items():
            # Monthly NASA responses add a 13th month key like "202413" for the full-year average.
            # We skip keys ending in 13 so we only keep real months (01 through 12) and don't double count.
            if len(str(date_key)) == 6 and str(date_key).endswith("13"):
                continue

            # NASA POWER puts -999.0 when satellite or station data is missing for a date.
            # Keeping only values above -900.0 stops -999 from ruining our averages.
            if isinstance(value, (int, float)) and float(value) > fill_threshold:
                valid_points[str(date_key)] = float(value)

        cleaned[param_code] = valid_points

    return cleaned


def fetch_nasa_power(
    lat: float,
    lon: float,
    start: str | int = 2023,
    end: str | int = 2024,
    temporal: str = "monthly",
    parameters: tuple[str, ...] = NASA_PARAMETERS,
    use_cache: bool = True,
    timeout: int = 10,
) -> dict[str, Any]:
    """
    Query NASA POWER for ALLSKY_SFC_SW_DWN, WS2M, PRECTOTCORR, and T2M at a
    given coordinate. For monthly queries, start and end should be YYYY. For
    daily queries, start and end should be YYYYMMDD.
    """
    # Check whether the caller asked for daily or monthly data
    mode = temporal.lower().strip()
    if mode not in ("daily", "monthly"):
        raise ValueError("temporal must be 'daily' or 'monthly'")

    # Pick the matching NASA URL and join parameter codes with commas
    endpoint = NASA_POWER_DAILY_URL if mode == "daily" else NASA_POWER_MONTHLY_URL
    param_str = ",".join(parameters)

    # Build the query dictionary expected by the NASA POWER API
    query_params = {
        "parameters": param_str,
        "community": "AG",  # AG stands for Agroclimatology (farming weather data)
        "latitude": round(float(lat), 4),
        "longitude": round(float(lon), 4),
        "start": str(start),
        "end": str(end),
        "format": "JSON",
    }

    # Build a predictable filename so each coordinate and year range gets its own backup JSON file
    cache_name = f"power_{mode}_{lat:.4f}_{lon:.4f}_{start}_{end}.json"
    cache_path = CACHE_DIR / cache_name
    raw_payload: Optional[dict[str, Any]] = None
    source = "live"

    try:
        # Try fetching live data from NASA first
        raw_payload = _http_get_json(endpoint, query_params, timeout=timeout)
        if use_cache:
            # Save the raw JSON to data/nasa_cache/ so offline demos still work if Wi-Fi drops
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(raw_payload, indent=2), encoding="utf-8")
    except Exception:
        # If the live request fails (no internet or NASA server timeout), load from the saved cache file
        if use_cache and cache_path.exists():
            raw_payload = json.loads(cache_path.read_text(encoding="utf-8"))
            source = "cache"
        else:
            raise

    # NASA nests the actual numbers inside properties -> parameter in the JSON response
    raw_params = raw_payload.get("properties", {}).get("parameter", {})

    # Strip out -999 missing values and 13th-month summary keys before returning
    cleaned_params = strip_fill_values(raw_params)

    return {
        "source": source,
        "temporal": mode,
        "coordinates": {"lat": round(float(lat), 4), "lon": round(float(lon), 4)},
        "period": {"start": str(start), "end": str(end)},
        "parameter_labels": {code: PARAMETER_LABELS.get(code, code) for code in parameters},
        "data": cleaned_params,
        "summary": summarize_parameters(cleaned_params, temporal=mode),
    }


def summarize_parameters(
    cleaned_params: dict[str, dict[str, float]],
    temporal: str = "monthly",
) -> dict[str, Optional[float]]:
    """
    Compute mean values across the cleaned series for solar irradiance,
    wind speed, precipitation, and temperature.
    """
    # Helper that averages all valid readings for one parameter code, or returns None if empty
    def _mean_or_none(code: str) -> Optional[float]:
        vals = list(cleaned_params.get(code, {}).values())
        return round(statistics.mean(vals), 3) if vals else None

    irradiance_avg = _mean_or_none("ALLSKY_SFC_SW_DWN")
    wind_avg = _mean_or_none("WS2M")
    precip_daily_avg = _mean_or_none("PRECTOTCORR")
    temp_avg = _mean_or_none("T2M")

    # NASA POWER reports PRECTOTCORR as an average daily rate (mm/day) even in monthly mode.
    # Multiplying the daily average by 365.25 converts it into estimated total yearly rainfall (mm/year),
    # which lets us compare field rainfall directly against crop water demand in mm.
    est_annual_precip_mm = (
        round(precip_daily_avg * 365.25, 1) if precip_daily_avg is not None else None
    )

    return {
        "allsky_sfc_sw_dwn_avg": irradiance_avg,
        "ws2m_avg_m_s": wind_avg,
        "prectotcorr_avg_mm_day": precip_daily_avg,
        "estimated_annual_precip_mm": est_annual_precip_mm,
        "t2m_avg_c": temp_avg,
    }


if __name__ == "__main__":
    # Run this file directly (python src/backend/nasa_client.py) to test a Finger Lakes, NY point
    sample_result = fetch_nasa_power(lat=42.70, lon=-76.80, start=2023, end=2024)
    print("Source:", sample_result["source"])
    print("Summary:", json.dumps(sample_result["summary"], indent=2))
