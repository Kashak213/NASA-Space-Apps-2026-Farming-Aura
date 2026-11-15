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
# ALLSKY_SFC_SW_DWN measures sunlight hitting the ground for photosynthesis (MJ/m^2/day),
# WS2M measures wind speed at 2 meters which affects plant transpiration (m/s),
# PRECTOTCORR measures corrected daily rainfall (mm/day),
# T2M measures air temperature at 2 meters (degrees Celsius),
# and GWETROOT measures satellite-assimilated root-zone soil wetness (0.0 to 1.0 fraction).
NASA_PARAMETERS: tuple[str, ...] = (
    "ALLSKY_SFC_SW_DWN",
    "WS2M",
    "PRECTOTCORR",
    "T2M",
    "GWETROOT",
)

# Readable names for each NASA code so the frontend or logs are easy to read
PARAMETER_LABELS: dict[str, str] = {
    "ALLSKY_SFC_SW_DWN": "All Sky Surface Shortwave Downward Irradiance",
    "WS2M": "Wind Speed at 2 Meters",
    "PRECTOTCORR": "Precipitation Corrected",
    "T2M": "Temperature at 2 Meters",
    "GWETROOT": "Root Zone Soil Wetness",
}

# Exact number of days per month (with 28.25 for February) for day-weighted annual totals
MONTH_DAYS: dict[str, float] = {
    "01": 31.0,
    "02": 28.25,
    "03": 31.0,
    "04": 30.0,
    "05": 31.0,
    "06": 30.0,
    "07": 31.0,
    "08": 31.0,
    "09": 30.0,
    "10": 31.0,
    "11": 30.0,
    "12": 31.0,
}
GROWING_SEASON_MONTHS: tuple[str, ...] = ("05", "06", "07", "08", "09")
SUMMER_MONTHS: tuple[str, ...] = ("06", "07", "08")


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

    if use_cache and cache_path.exists():
        try:
            cached_data = json.loads(cache_path.read_text(encoding="utf-8"))
            cached_params = cached_data.get("properties", {}).get("parameter", {})
            if all(code in cached_params for code in parameters):
                raw_payload = cached_data
                source = "cache"
        except Exception:
            raw_payload = None

    if raw_payload is None:
        try:
            # Fetch live data from NASA POWER when not cached yet or when use_cache=False
            raw_payload = _http_get_json(endpoint, query_params, timeout=timeout)
            source = "live"
            if use_cache:
                payload_to_cache = dict(raw_payload)
                payload_to_cache.pop("times", None)
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(payload_to_cache, indent=2), encoding="utf-8")
        except Exception:
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
    Compute day-weighted annual averages, May-September growing-season averages,
    and year-over-year climate trends across the cleaned NASA POWER series.
    """
    def _day_weighted_mean(code: str, allowed_months: Optional[tuple[str, ...]] = None) -> Optional[float]:
        series = cleaned_params.get(code, {})
        if not series:
            return None
        weighted_sum = 0.0
        total_days = 0.0
        fallback_vals: list[float] = []
        for date_key, val in series.items():
            key_str = str(date_key)
            if len(key_str) == 6:
                month_str = key_str[4:6]
                if allowed_months is not None and month_str not in allowed_months:
                    continue
                days = MONTH_DAYS.get(month_str, 30.4375)
                weighted_sum += float(val) * days
                total_days += days
            elif len(key_str) == 8:
                month_str = key_str[4:6]
                if allowed_months is not None and month_str not in allowed_months:
                    continue
                fallback_vals.append(float(val))
        if total_days > 0.0:
            return round(weighted_sum / total_days, 3)
        return round(statistics.mean(fallback_vals), 3) if fallback_vals else None

    def _yearly_means(code: str, allowed_months: Optional[tuple[str, ...]] = None) -> dict[str, float]:
        series = cleaned_params.get(code, {})
        by_year: dict[str, list[tuple[float, float]]] = {}
        for date_key, val in series.items():
            key_str = str(date_key)
            if len(key_str) >= 6:
                yr = key_str[:4]
                month_str = key_str[4:6]
                if allowed_months is not None and month_str not in allowed_months:
                    continue
                days = MONTH_DAYS.get(month_str, 1.0) if len(key_str) == 6 else 1.0
                by_year.setdefault(yr, []).append((float(val), days))
        out: dict[str, float] = {}
        for yr, items in sorted(by_year.items()):
            tot_d = sum(d for _, d in items)
            if tot_d > 0:
                out[yr] = sum(v * d for v, d in items) / tot_d
        return out

    irradiance_avg = _day_weighted_mean("ALLSKY_SFC_SW_DWN")
    growing_irradiance_avg = _day_weighted_mean("ALLSKY_SFC_SW_DWN", GROWING_SEASON_MONTHS)
    wind_avg = _day_weighted_mean("WS2M")
    growing_wind_avg = _day_weighted_mean("WS2M", GROWING_SEASON_MONTHS)
    precip_daily_avg = _day_weighted_mean("PRECTOTCORR")
    growing_precip_daily_avg = _day_weighted_mean("PRECTOTCORR", GROWING_SEASON_MONTHS)
    temp_avg = _day_weighted_mean("T2M")
    growing_temp_avg = _day_weighted_mean("T2M", GROWING_SEASON_MONTHS)
    summer_temp_avg = _day_weighted_mean("T2M", SUMMER_MONTHS)
    gwetroot_avg = _day_weighted_mean("GWETROOT")
    growing_gwetroot_avg = _day_weighted_mean("GWETROOT", GROWING_SEASON_MONTHS)

    est_annual_precip_mm = (
        round(precip_daily_avg * 365.25, 1) if precip_daily_avg is not None else None
    )
    # May through September has 153 days (31 + 30 + 31 + 31 + 30)
    est_growing_precip_mm = (
        round(growing_precip_daily_avg * 153.0, 1)
        if growing_precip_daily_avg is not None
        else None
    )

    # Calculate year-over-year climate trends (such as 2023 to 2024) from the monthly series
    yearly_precip = _yearly_means("PRECTOTCORR")
    yearly_summer_precip = _yearly_means("PRECTOTCORR", SUMMER_MONTHS)
    yearly_summer_temp = _yearly_means("T2M", SUMMER_MONTHS)
    precip_anom_trend = 0.0
    drought_trend = 0.0

    if len(yearly_precip) >= 2:
        years_sorted = sorted(yearly_precip.keys())
        first_yr, last_yr = years_sorted[0], years_sorted[-1]
        p_first = yearly_precip[first_yr] * 365.25
        p_last = yearly_precip[last_yr] * 365.25
        if p_first > 0:
            precip_anom_trend = round(((p_last - p_first) / p_first) * 100.0, 2)

    if len(yearly_summer_precip) >= 2:
        years_sorted = sorted(yearly_summer_precip.keys())
        first_yr, last_yr = years_sorted[0], years_sorted[-1]
        sp_first = yearly_summer_precip[first_yr]
        sp_last = yearly_summer_precip[last_yr]
        st_diff = (
            yearly_summer_temp.get(last_yr, 21.0) - yearly_summer_temp.get(first_yr, 21.0)
        )
        # Positive drought_trend means summers are getting drier or hotter year over year
        precip_drop_ratio = (sp_first - sp_last) / max(sp_first, 1.0)
        drought_trend = round(max(-0.25, min(0.25, 0.20 * precip_drop_ratio + 0.02 * st_diff)), 3)

    return {
        "allsky_sfc_sw_dwn_avg": irradiance_avg,
        "growing_season_solar_mj_m2_day": growing_irradiance_avg or irradiance_avg,
        "ws2m_avg_m_s": wind_avg,
        "growing_season_wind_m_s": growing_wind_avg or wind_avg,
        "prectotcorr_avg_mm_day": precip_daily_avg,
        "estimated_annual_precip_mm": est_annual_precip_mm,
        "growing_season_precip_mm": est_growing_precip_mm,
        "t2m_avg_c": temp_avg,
        "growing_season_temp_c": growing_temp_avg or temp_avg,
        "summer_temp_c": summer_temp_avg or growing_temp_avg or temp_avg,
        "gwetroot_avg": gwetroot_avg,
        "growing_season_gwetroot": growing_gwetroot_avg or gwetroot_avg,
        "precip_anom_trend": precip_anom_trend,
        "drought_trend": drought_trend,
    }


if __name__ == "__main__":
    # Run this file directly (python src/backend/nasa_client.py) to test a Finger Lakes, NY point
    sample_result = fetch_nasa_power(lat=42.70, lon=-76.80, start=2023, end=2024)
    print("Source:", sample_result["source"])
    print("Summary:", json.dumps(sample_result["summary"], indent=2))
