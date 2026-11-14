"""
NASA POWER client for pulling field weather and sunlight data by lat/lon.
Saves raw responses in data/nasa_cache so the app still works if demo Wi-Fi drops.
"""

import json
import statistics
import urllib.parse
import urllib.request
from pathlib import Path

# use requests if installed, otherwise standard urllib works fine
try:
    import requests
except ImportError:
    requests = None

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "data" / "nasa_cache"

NASA_POWER_DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_POWER_MONTHLY_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"

# AG community codes:
# ALLSKY_SFC_SW_DWN = sunlight hitting the ground (for photosynthesis)
# WS2M = wind speed at 2m (drives transpiration water loss)
# PRECTOTCORR = daily rain in mm/day
# T2M = air temp at 2m in C
NASA_PARAMETERS = (
    "ALLSKY_SFC_SW_DWN",
    "WS2M",
    "PRECTOTCORR",
    "T2M",
)

PARAMETER_LABELS = {
    "ALLSKY_SFC_SW_DWN": "All Sky Surface Shortwave Downward Irradiance",
    "WS2M": "Wind Speed at 2 Meters",
    "PRECTOTCORR": "Precipitation Corrected",
    "T2M": "Temperature at 2 Meters",
}


def _http_get_json(url: str, params: dict, timeout: int = 10) -> dict:
    """Grab JSON from NASA POWER using requests or urllib."""
    if requests is not None:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    query_string = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"{url}?{query_string}",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def strip_fill_values(raw_parameter_block: dict, fill_threshold: float = -900.0) -> dict:
    """Drop NASA -999 missing values and the extra month-13 annual summary key."""
    cleaned = {}

    for param_code, series in raw_parameter_block.items():
        if not isinstance(series, dict):
            continue

        valid_points = {}
        for date_key, value in series.items():
            # monthly mode tacks on a fake "13" month (like 202413) for the yearly avg, skip it
            if len(str(date_key)) == 6 and str(date_key).endswith("13"):
                continue

            # nasa puts -999.0 when satellite data is missing so filter out anything below -900
            if isinstance(value, (int, float)) and float(value) > fill_threshold:
                valid_points[str(date_key)] = float(value)

        cleaned[param_code] = valid_points

    return cleaned


def fetch_nasa_power(
    lat: float,
    lon: float,
    start=2023,
    end=2024,
    temporal: str = "monthly",
    parameters: tuple = NASA_PARAMETERS,
    use_cache: bool = True,
    timeout: int = 10,
) -> dict:
    """Fetch weather data from NASA POWER for a lat/lon point (YYYY for monthly, YYYYMMDD for daily)."""
    mode = temporal.lower().strip()
    if mode not in ("daily", "monthly"):
        raise ValueError("temporal must be 'daily' or 'monthly'")

    endpoint = NASA_POWER_DAILY_URL if mode == "daily" else NASA_POWER_MONTHLY_URL
    query_params = {
        "parameters": ",".join(parameters),
        "community": "AG",
        "latitude": round(float(lat), 4),
        "longitude": round(float(lon), 4),
        "start": str(start),
        "end": str(end),
        "format": "JSON",
    }

    cache_name = f"power_{mode}_{lat:.4f}_{lon:.4f}_{start}_{end}.json"
    cache_path = CACHE_DIR / cache_name
    raw_payload = None
    source = "live"

    try:
        raw_payload = _http_get_json(endpoint, query_params, timeout=timeout)
        if use_cache:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(raw_payload, indent=2), encoding="utf-8")
    except Exception:
        # fall back to cached json if wifi dies or nasa times out during judging
        if use_cache and cache_path.exists():
            raw_payload = json.loads(cache_path.read_text(encoding="utf-8"))
            source = "cache"
        else:
            raise

    # actual readings live under properties -> parameter
    raw_params = raw_payload.get("properties", {}).get("parameter", {})
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


def summarize_parameters(cleaned_params: dict, temporal: str = "monthly") -> dict:
    """Average each weather parameter across the time range and estimate yearly rain."""
    averages = {}
    for code in ("ALLSKY_SFC_SW_DWN", "WS2M", "PRECTOTCORR", "T2M"):
        vals = list(cleaned_params.get(code, {}).values())
        averages[code] = round(statistics.mean(vals), 3) if vals else None

    precip_daily_avg = averages["PRECTOTCORR"]
    # PRECTOTCORR is always in mm/day even on monthly mode, so * 365.25 gives ~mm/year
    # to compare against crop water demand
    est_annual_precip_mm = (
        round(precip_daily_avg * 365.25, 1) if precip_daily_avg is not None else None
    )

    return {
        "allsky_sfc_sw_dwn_avg": averages["ALLSKY_SFC_SW_DWN"],
        "ws2m_avg_m_s": averages["WS2M"],
        "prectotcorr_avg_mm_day": precip_daily_avg,
        "estimated_annual_precip_mm": est_annual_precip_mm,
        "t2m_avg_c": averages["T2M"],
    }


if __name__ == "__main__":
    # quick test with a Finger Lakes NY coordinate
    sample_result = fetch_nasa_power(lat=42.70, lon=-76.80, start=2023, end=2024)
    print("Source:", sample_result["source"])
    print("Summary:", json.dumps(sample_result["summary"], indent=2))
