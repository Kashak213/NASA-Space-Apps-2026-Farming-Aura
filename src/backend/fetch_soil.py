"""
USDA NRCS Soil Data Access (SDA) API client for fetching field soil properties.

Connects to the USDA Soil Data Access Tabular REST API (SSURGO database) using
a latitude and longitude point query to pull topsoil horizon properties
(organic carbon, soil pH, bulk density, cation exchange capacity, and
sand/silt/clay percentages) formatted directly for scoring.py, with local
caching in data/soil_cache for offline backup.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any, Optional

# Try to import requests first since it is in requirements.txt,
# but fall back to Python's built-in urllib if requests is not installed yet
try:
    import requests
except ImportError:
    requests = None

# Point to src/backend/ and the local offline cache folder src/backend/data/soil_cache/
BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "data" / "soil_cache"

# Official USDA NRCS Soil Data Access (SDA) Tabular REST endpoint
USDA_SDA_URL = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"

# Default topsoil fallback values (loam soil) matching scoring.py defaults
DEFAULT_SOIL_DATA: dict[str, Any] = {
    "organic_carbon_pct": 2.5,
    "organic_matter_pct": 4.3,
    "ph": 6.5,
    "bulk_density": 1.35,
    "cec": 20.0,
    "sand_pct": 40.0,
    "silt_pct": 35.0,
    "clay_pct": 25.0,
    "awc": 0.18,
    "drainage_class": "Well drained",
    "map_unit_name": "Default Loam Topsoil",
    "component_name": "Loam",
}

# Van Bemmelen conversion factor: Soil Organic Carbon (%) = Organic Matter (%) * 0.58
OM_TO_OC_FACTOR = 0.58


def _build_sda_sql(lat: float, lon: float, max_depth_cm: int = 30) -> str:
    """
    Build a T-SQL query for the USDA SDA endpoint that intersects a WGS84 point
    (lon, lat) with SSURGO map units, picks the dominant soil component, and
    returns representative topsoil horizon properties (0 to max_depth_cm).
    """
    # Note: WKT point order is (longitude latitude)
    wkt_point = f"point({float(lon):.6f} {float(lat):.6f})"
    return f"""
    SELECT TOP 5
        mu.mukey,
        mu.muname AS map_unit_name,
        c.cokey,
        c.compname AS component_name,
        c.comppct_r AS component_pct,
        c.drainagecl AS drainage_class,
        ch.hzname AS horizon_name,
        ch.hzdept_r AS depth_top_cm,
        ch.hzdepb_r AS depth_bottom_cm,
        ch.om_r AS organic_matter_pct,
        COALESCE(ch.ph1to1h2o_r, ch.ph01mcacl2_r) AS ph,
        COALESCE(ch.dbthirdbar_r, ch.dbovendry_r) AS bulk_density,
        COALESCE(ch.cec7_r, ch.ecec_r) AS cec,
        ch.sandtotal_r AS sand_pct,
        ch.silttotal_r AS silt_pct,
        ch.claytotal_r AS clay_pct,
        ch.awc_r AS awc
    FROM mapunit AS mu
    INNER JOIN SDA_Get_Mukey_from_intersection_with_WktWgs84('{wkt_point}') AS spatial
        ON mu.mukey = spatial.mukey
    INNER JOIN component AS c
        ON mu.mukey = c.mukey
    INNER JOIN chorizon AS ch
        ON c.cokey = ch.cokey
    WHERE ch.hzdept_r < {int(max_depth_cm)}
      AND (ch.sandtotal_r IS NOT NULL OR ch.ph1to1h2o_r IS NOT NULL OR ch.om_r IS NOT NULL)
    ORDER BY
         CASE WHEN c.majcompflag = 'Yes' THEN 0 ELSE 1 END,
        c.comppct_r DESC,
        ch.hzdept_r ASC
    """


def _http_post_sda(sql_query: str, timeout: int = 12) -> dict[str, Any]:
    """Send a POST request to the USDA SDA REST API and return the parsed JSON response."""
    payload = {
        "query": sql_query,
        "format": "JSON+COLUMNNAME",
    }

    if requests is not None:
        resp = requests.post(
            USDA_SDA_URL,
            json=payload,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()

    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        USDA_SDA_URL,
        data=data_bytes,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _safe_float(val: Any) -> Optional[float]:
    """Convert a string or number from the USDA table into a float, or None if missing."""
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def parse_sda_response(raw_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Convert a USDA SDA 'JSON+COLUMNNAME' Table array (where row 0 is column names
    and subsequent rows are data values) into a list of dictionaries.
    """
    table = raw_payload.get("Table")
    if not isinstance(table, list) or len(table) < 2:
        return []

    headers = [str(col) for col in table[0]]
    rows: list[dict[str, Any]] = []
    for raw_row in table[1:]:
        if isinstance(raw_row, list) and len(raw_row) == len(headers):
            rows.append(dict(zip(headers, raw_row)))
    return rows


def normalize_soil_for_scoring(horizon_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Aggregate one or more topsoil horizon rows from USDA SSURGO into the exact
    soil dictionary keys expected by scoring.py:
      - organic_carbon_pct (float)
      - ph (float)
      - bulk_density (float)
      - cec (float)
      - sand_pct (float)
      - clay_pct (float)
    Falls back to DEFAULT_SOIL_DATA for any individual metric missing in SSURGO.
    """
    if not horizon_rows:
        return dict(DEFAULT_SOIL_DATA)

    # Pick the primary (shallowest / highest component %) row for labels, and
    # use subsequent topsoil horizons to fill in any null lab values
    primary = horizon_rows[0]

    def _first_valid_float(key: str) -> Optional[float]:
        for row in horizon_rows:
            val = _safe_float(row.get(key))
            if val is not None:
                return val
        return None

    om_pct = _first_valid_float("organic_matter_pct")
    if om_pct is not None:
        # Convert USDA Organic Matter (%) to Organic Carbon (%) for scoring.py,
        # clamping extravagant peat/muck values (> 15% OM) to a realistic mineral topsoil range
        oc_pct = round(min(om_pct * OM_TO_OC_FACTOR, 8.0), 2)
        om_pct = round(om_pct, 2)
    else:
        oc_pct = DEFAULT_SOIL_DATA["organic_carbon_pct"]
        om_pct = DEFAULT_SOIL_DATA["organic_matter_pct"]

    ph = _first_valid_float("ph")
    bulk_density = _first_valid_float("bulk_density")
    cec = _first_valid_float("cec")
    sand_pct = _first_valid_float("sand_pct")
    silt_pct = _first_valid_float("silt_pct")
    clay_pct = _first_valid_float("clay_pct")
    awc = _first_valid_float("awc")

    # If sand and clay are present but silt is missing, derive silt as 100 - (sand + clay)
    if silt_pct is None and sand_pct is not None and clay_pct is not None:
        silt_pct = max(0.0, 100.0 - sand_pct - clay_pct)

    return {
        "organic_carbon_pct": oc_pct,
        "organic_matter_pct": om_pct,
        "ph": round(ph, 2) if ph is not None else DEFAULT_SOIL_DATA["ph"],
        "bulk_density": (
            round(bulk_density, 2)
            if bulk_density is not None
            else DEFAULT_SOIL_DATA["bulk_density"]
        ),
        "cec": round(cec, 2) if cec is not None else DEFAULT_SOIL_DATA["cec"],
        "sand_pct": round(sand_pct, 1) if sand_pct is not None else DEFAULT_SOIL_DATA["sand_pct"],
        "silt_pct": round(silt_pct, 1) if silt_pct is not None else DEFAULT_SOIL_DATA["silt_pct"],
        "clay_pct": round(clay_pct, 1) if clay_pct is not None else DEFAULT_SOIL_DATA["clay_pct"],
        "awc": round(awc, 3) if awc is not None else DEFAULT_SOIL_DATA["awc"],
        "drainage_class": primary.get("drainage_class") or DEFAULT_SOIL_DATA["drainage_class"],
        "map_unit_name": primary.get("map_unit_name") or DEFAULT_SOIL_DATA["map_unit_name"],
        "component_name": primary.get("component_name") or DEFAULT_SOIL_DATA["component_name"],
        "mukey": primary.get("mukey"),
        "cokey": primary.get("cokey"),
    }


def fetch_usda_soil(
    lat: float,
    lon: float,
    max_depth_cm: int = 30,
    use_cache: bool = True,
    fallback_on_error: bool = True,
    timeout: int = 12,
) -> dict[str, Any]:
    """
    Query the USDA NRCS Soil Data Access (SDA) API for a given latitude and
    longitude and return both the raw horizon rows and a normalized `soil`
    dictionary ready to pass directly into scoring.py functions
    (e.g., score_rotation, soil_health_score, field_soil_baseline_score).
    """
    lat_r = round(float(lat), 4)
    lon_r = round(float(lon), 4)
    cache_name = f"usda_soil_{lat_r:.4f}_{lon_r:.4f}_{int(max_depth_cm)}cm.json"
    cache_path = CACHE_DIR / cache_name

    raw_payload: Optional[dict[str, Any]] = None
    source = "live"

    try:
        sql_query = _build_sda_sql(lat_r, lon_r, max_depth_cm=max_depth_cm)
        raw_payload = _http_post_sda(sql_query, timeout=timeout)
        if use_cache:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(raw_payload, indent=2), encoding="utf-8")
    except Exception as exc:
        if use_cache and cache_path.exists():
            raw_payload = json.loads(cache_path.read_text(encoding="utf-8"))
            source = "cache"
        elif fallback_on_error:
            return {
                "source": "fallback",
                "error": str(exc),
                "coordinates": {"lat": lat_r, "lon": lon_r},
                "soil": dict(DEFAULT_SOIL_DATA),
                "horizons": [],
            }
        else:
            raise

    horizon_rows = parse_sda_response(raw_payload or {})
    soil_dict = normalize_soil_for_scoring(horizon_rows)

    return {
        "source": source,
        "coordinates": {"lat": lat_r, "lon": lon_r},
        "soil": soil_dict,
        "horizons": horizon_rows,
    }


def get_soil_for_scoring(
    lat: float,
    lon: float,
    use_cache: bool = True,
    timeout: int = 12,
) -> dict[str, Any]:
    """
    Convenience wrapper that returns the flat `soil` dictionary directly for
    immediate use in scoring.score_rotation(crop_rows, soil, climate).
    """
    result = fetch_usda_soil(lat=lat, lon=lon, use_cache=use_cache, timeout=timeout)
    soil = dict(result["soil"])
    soil["source"] = result["source"]
    soil["coordinates"] = result["coordinates"]
    return soil


if __name__ == "__main__":
    from crops import resolve_sequence_crops
    from scoring import field_soil_baseline_score, score_rotation

    # Test with a Finger Lakes, NY farmland coordinate (Seneca County, NY)
    sample_lat, sample_lon = 42.70, -76.80
    response = fetch_usda_soil(lat=sample_lat, lon=sample_lon)
    soil_data = response["soil"]

    print("Source:", response["source"])
    print("Soil properties for scoring.py:")
    print(json.dumps(soil_data, indent=2))
    print("Baseline Soil Score:", round(field_soil_baseline_score(soil_data), 3))

    # Score a sample 3-year Field Corn -> Soybeans & Small Grains -> Hay & Alfalfa rotation
    sample_crops = resolve_sequence_crops(["C02", "C03", "C01"])
    sample_climate = {
        "drought_index": 0.20,
        "soil_moisture_avg": 0.32,
        "annual_precip_mm": 920.0,
        "ws2m_avg_m_s": 3.4,
        "allsky_sfc_sw_dwn_avg": 14.8,
    }
    scored = score_rotation(sample_crops, soil=soil_data, climate=sample_climate)
    print("Sample Rotation Score:", json.dumps(scored, indent=2))
