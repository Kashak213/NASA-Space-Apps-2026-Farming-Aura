"""
Crop rotation scoring engine with 5 preset farmer priority profiles and 7 weights.

Implements the 7 sub-score calculations (soil health, water stress, climate
resilience, nitrogen fixation, yield potential, drought tolerance, and soil
compatibility), wind speed (WS2M) and sunlight intensity (ALLSKY_SFC_SW_DWN)
effects from NASA POWER, sequence transition penalties, and the 5 preset
weighting profiles (Balanced, Max Yield, Water Conservation, Soil Health First,
and Climate Resilient).
"""

from __future__ import annotations

import statistics
from typing import Any, Optional

# The 7 factor keys that every profile uses to weight a crop rotation
WEIGHT_KEYS: tuple[str, ...] = (
    "soil_health",   # w1: Baseline soil quality + how much the crops rebuild organic matter
    "water_stress",  # w2: Field water supply (adjusted for wind and sun drying) vs crop water demand
    "climate_res",   # w3: Rain, NDVI, heat, wind, and sunlight stability + crop family diversity
    "nitrogen_fix",  # w4: Legume N-fixation + extra credit when a legume comes before a grain
    "yield",         # w5: Expected crop harvest tonnage adjusted for sunlight photosynthesis
    "drought_tol",   # w6: How well the crops survive dry spells
    "soil_compat",   # w7: How well crop pH and clay ranges match the field + root depth mix
)

# Five preset farmer priority profiles.
# Each profile has 7 weights that add up to 1.00, shifting the scoring formula
# toward what that farmer cares about most.
PROFILES: dict[str, dict[str, float]] = {
    # Balanced spreads weight evenly across soil, water, climate, nitrogen, and yield
    "Balanced": {
        "soil_health": 0.20,
        "water_stress": 0.20,
        "climate_res": 0.15,
        "nitrogen_fix": 0.15,
        "yield": 0.15,
        "drought_tol": 0.10,
        "soil_compat": 0.05,
    },
    # Max Yield puts 40% of the total weight on harvest tonnage for cash-crop focus
    "Max Yield": {
        "soil_health": 0.10,
        "water_stress": 0.15,
        "climate_res": 0.10,
        "nitrogen_fix": 0.10,
        "yield": 0.40,
        "drought_tol": 0.10,
        "soil_compat": 0.05,
    },
    # Water Conservation puts 50% combined weight on water safety (35%) and drought tolerance (15%)
    "Water Conservation": {
        "soil_health": 0.10,
        "water_stress": 0.35,
        "climate_res": 0.15,
        "nitrogen_fix": 0.10,
        "yield": 0.10,
        "drought_tol": 0.15,
        "soil_compat": 0.05,
    },
    # Soil Health First puts 55% combined weight on rebuilding soil (30%) and legume N-fixation (25%)
    "Soil Health First": {
        "soil_health": 0.30,
        "water_stress": 0.10,
        "climate_res": 0.10,
        "nitrogen_fix": 0.25,
        "yield": 0.10,
        "drought_tol": 0.10,
        "soil_compat": 0.05,
    },
    # Climate Resilient focuses on weather stability (25%), water safety (20%), and drought tolerance (15%)
    "Climate Resilient": {
        "soil_health": 0.15,
        "water_stress": 0.20,
        "climate_res": 0.25,
        "nitrogen_fix": 0.10,
        "yield": 0.10,
        "drought_tol": 0.15,
        "soil_compat": 0.05,
    },
}


def clip(val: float, lo: float, hi: float) -> float:
    """Keep a number inside the range [lo, hi] so scores never go below 0 or above 1."""
    # max(lo, ...) raises values that are too small, and min(hi, ...) caps values that are too big
    return max(lo, min(hi, val))


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    """
    Make sure all 7 weights are non-negative and divide by their sum so they
    always add up to 1.0, even if a user moves custom sliders on the frontend.
    """
    # Replace any missing or negative weight with 0.0
    cleaned = {k: max(0.0, float(weights.get(k, 0.0))) for k in WEIGHT_KEYS}
    total = sum(cleaned.values())

    # If the user set every slider to 0, fall back to the Balanced profile so we don't divide by zero
    if total <= 0.0:
        return dict(PROFILES["Balanced"])

    # Divide each weight by the sum so the 7 weights add up to 1.0
    return {k: cleaned[k] / total for k in WEIGHT_KEYS}


def get_profile_weights(
    profile_name: str = "Balanced",
    custom_weights: Optional[dict[str, float]] = None,
) -> dict[str, float]:
    """
    Return the normalized 7-weight dictionary for one of the 5 preset profiles,
    or normalize custom slider weights if the caller passes them in.
    """
    # If custom weights were passed from UI sliders, normalize and use those first
    if custom_weights is not None:
        return normalize_weights(custom_weights)

    # Otherwise look up the requested preset profile name
    if profile_name not in PROFILES:
        valid = ", ".join(PROFILES.keys())
        raise ValueError(f"Unknown profile '{profile_name}'. Choose from: {valid}")
    return dict(PROFILES[profile_name])


def get_wind_speed_m_s(climate: dict[str, Any]) -> float:
    """
    Read the 2-meter wind speed (in m/s) from either a NASA POWER summary dict
    or a standard climate dict, preferring growing-season wind when available.
    Defaults to 3.0 m/s (a gentle breeze) if not provided.
    """
    for key in ("growing_season_wind_m_s", "ws2m_avg_m_s", "WS2M", "wind_speed_m_s"):
        if climate.get(key) is not None:
            return float(climate[key])
    return 3.0


def get_solar_irradiance(climate: dict[str, Any]) -> float:
    """
    Read growing-season sunlight intensity (All Sky Surface Shortwave Downward
    Irradiance, in MJ/m^2/day for the NASA POWER AG community) from a climate
    dictionary so winter snow months do not distort summer crop photosynthesis.
    Defaults to 17.5 MJ/m^2/day (a normal temperate growing-season average) if missing.
    """
    for key in (
        "growing_season_solar_mj_m2_day",
        "allsky_sfc_sw_dwn_avg",
        "ALLSKY_SFC_SW_DWN",
        "solar_irradiance_mj_m2_day",
    ):
        if climate.get(key) is not None:
            return float(climate[key])
    return 17.5


def crop_temperature_fit(crop: dict[str, Any], climate: Optional[dict[str, Any]] = None) -> float:
    """
    Score how well the field's May-September growing-season temperature matches
    the crop's optimal temperature window [optimal_temp_min_c, optimal_temp_max_c].
    Any temperature inside the optimal plateau scores 1.0, tapering off outside.
    """
    if not climate:
        return 1.0
    field_temp = climate.get("growing_season_temp_c")
    if field_temp is None:
        if climate.get("summer_temp_c") is not None:
            field_temp = float(climate["summer_temp_c"]) - 2.0
        elif climate.get("t2m_avg_c") is not None:
            field_temp = float(climate["t2m_avg_c"]) + 7.5
        else:
            return 1.0

    t_val = float(field_temp)
    t_min = float(crop.get("optimal_temp_min_c", 13.0))
    t_max = float(crop.get("optimal_temp_max_c", 25.0))
    if t_min <= t_val <= t_max:
        return 1.0
    dist = (t_min - t_val) if t_val < t_min else (t_val - t_max)
    return clip(1.0 - dist / 6.0, 0.0, 1.0)


def soil_drainage_score(
    soil: dict[str, Any], crop: Optional[dict[str, Any]] = None
) -> float:
    """
    Evaluate field drainage quality from USDA SSURGO drainage_class and subsoil
    bulk density (hardpan/fragipan indicator). When a crop is provided, penalize
    deep-rooted or rot-sensitive crops on poorly drained or hardpan soils.
    """
    raw_class = str(soil.get("drainage_class", "Well drained")).strip().lower()
    drainage_map = {
        "well drained": 1.00,
        "moderately well drained": 0.88,
        "somewhat excessively drained": 0.86,
        "excessively drained": 0.74,
        "somewhat poorly drained": 0.58,
        "poorly drained": 0.32,
        "very poorly drained": 0.15,
    }
    base_drain = drainage_map.get(raw_class, 0.85)

    subsoil_bd = float(soil.get("subsoil_bulk_density", soil.get("bulk_density", 1.35)))
    hardpan_penalty = clip((subsoil_bd - 1.60) / 0.35, 0.0, 0.25)
    field_drain = clip(base_drain - hardpan_penalty, 0.10, 1.0)

    if crop is None:
        return field_drain

    wetness_deficit = max(0.0, 0.90 - field_drain)
    if wetness_deficit <= 0.0:
        return 1.0

    tol = float(crop.get("drainage_tolerance", 0.55))
    root_m = float(crop.get("root_depth_m", 1.0))
    deep_root_exposure = clip((root_m - 1.2) / 1.8, 0.0, 0.30)
    vulnerability = clip((1.0 - tol) + deep_root_exposure, 0.10, 1.0)
    return clip(1.0 - wetness_deficit * vulnerability * 1.15, 0.15, 1.0)


def wind_stress_score(
    climate: dict[str, Any], crop_rows: Optional[list[dict[str, Any]]] = None
) -> float:
    """
    Calculate a 0.0 to 1.0 wind safety score from NASA POWER 2-meter wind speed (WS2M).
    Higher wind speeds blow away the humid air layer around leaves (increasing water loss
    through transpiration) and can bend or knock over tall grain stalks (lodging).
    A score near 1.0 means calm, safe wind conditions, while a lower score means windy stress.
    """
    wind_m_s = get_wind_speed_m_s(climate)

    # Wind at or below 1.2 m/s is calm (1.0). Wind up near 7.2 m/s is very strong (0.0).
    field_wind_safety = 1.0 - clip((wind_m_s - 1.2) / 6.0, 0.0, 1.0)
    if not crop_rows:
        return field_wind_safety

    # Cover crops and sturdy deep-rooted crops hold soil in place and resist wind damage better
    crop_wind_buffers: list[float] = []
    for crop in crop_rows:
        soil_hold = float(crop.get("soil_building_score", 0.5))
        root_anchor = clip(float(crop.get("root_depth_m", 1.0)) / 2.0, 0.2, 1.0)
        crop_wind_buffers.append(0.55 * soil_hold + 0.45 * root_anchor)

    crop_buffer_avg = statistics.mean(crop_wind_buffers)
    return clip(0.65 * field_wind_safety + 0.35 * crop_buffer_avg, 0.0, 1.0)


def sunlight_suitability_score(
    climate: dict[str, Any], crop_rows: Optional[list[dict[str, Any]]] = None
) -> float:
    """
    Calculate a 0.0 to 1.0 sunlight suitability score from growing-season NASA POWER
    shortwave irradiance (ALLSKY_SFC_SW_DWN, in MJ/m^2/day).
    """
    solar = get_solar_irradiance(climate)

    # 17.5 MJ/m^2/day is the growing-season sweet spot (1.0)
    field_light_score = 1.0 - clip(abs(solar - 17.5) / 10.0, 0.0, 1.0)
    if not crop_rows:
        return field_light_score

    crop_light_fits: list[float] = []
    for crop in crop_rows:
        ctype = str(crop.get("crop_type", "")).lower()
        if ctype in ("grain", "vegetable", "vineyard", "orchard"):
            ideal_solar = 18.5
        elif ctype in ("legume", "forage_legume", "root_veg", "berry"):
            ideal_solar = 16.5
        else:
            ideal_solar = 14.5
        crop_fit = 1.0 - clip(abs(solar - ideal_solar) / 8.5, 0.0, 1.0)
        crop_light_fits.append(crop_fit)

    return clip(0.50 * field_light_score + 0.50 * statistics.mean(crop_light_fits), 0.0, 1.0)


def field_soil_baseline_score(soil: dict[str, Any]) -> float:
    """
    Score the starting soil quality of a field from 0.0 to 1.0 using organic
    carbon, pH, bulk density, CEC, drainage class, and sand/clay loam balance.
    """
    oc = float(soil.get("organic_carbon_pct", 2.5))
    oc_score = clip((oc - 1.0) / 4.0, 0.0, 1.0)

    ph = float(soil.get("ph", 6.5))
    if 6.0 <= ph <= 7.0:
        ph_score = 1.0
    else:
        ph_dist = (6.0 - ph) if ph < 6.0 else (ph - 7.0)
        ph_score = clip(1.0 - ph_dist / 1.8, 0.0, 1.0)

    bd = float(soil.get("bulk_density", 1.35))
    bd_score = clip((1.7 - bd) / 0.6, 0.0, 1.0)

    cec = float(soil.get("cec", 20.0))
    cec_score = clip(cec / 35.0, 0.0, 1.0)

    sand = float(soil.get("sand_pct", 40.0))
    clay = float(soil.get("clay_pct", 25.0))
    texture_score = 1.0 - clip((abs(sand - 40.0) + abs(clay - 25.0)) / 60.0, 0.0, 1.0)

    drain_score = soil_drainage_score(soil)

    return (
        0.22 * oc_score
        + 0.18 * ph_score
        + 0.20 * bd_score
        + 0.14 * cec_score
        + 0.12 * texture_score
        + 0.14 * drain_score
    )


def soil_health_score(
    soil: dict[str, Any],
    crop_rows: Optional[list[dict[str, Any]]] = None,
    climate: Optional[dict[str, Any]] = None,
    previous_crops: Optional[list[dict[str, Any]]] = None,
) -> float:
    """
    Weight 1 (soil_health): Combine the field's baseline soil score with how
    much the crops in the rotation add organic matter, break up packed soil,
    fit the field's drainage class, protect topsoil from erosion, and recover
    from whatever crop was already farmed last season.
    """
    s_base = field_soil_baseline_score(soil)

    if climate is not None:
        wind_m_s = get_wind_speed_m_s(climate)
        sand_fraction = clip(float(soil.get("sand_pct", 40.0)) / 100.0, 0.0, 1.0)
        wind_erosion_penalty = clip((wind_m_s - 2.2) / 7.0, 0.0, 0.12) * sand_fraction
        s_base = clip(s_base - wind_erosion_penalty, 0.0, 1.0)

    if not crop_rows:
        return s_base

    bd = float(soil.get("bulk_density", 1.35))
    compaction_need = clip((bd - 1.15) / 0.45, 0.2, 1.0)

    # Check if the crop farmed right before Year 1 depleted soil organic matter or compacted topsoil
    prev_list = [c for c in (previous_crops or []) if isinstance(c, dict) and c.get("crop_id")]
    prev_soil_delta = 0.0
    if prev_list:
        last_prev = prev_list[-1]
        prev_build = float(last_prev.get("soil_building_score", 0.5))
        prev_heavy = bool(last_prev.get("heavy_pk_feeder", False))
        year1_crop = crop_rows[0]
        year1_build = float(year1_crop.get("soil_building_score", 0.5))
        year1_nfix = float(year1_crop.get("nitrogen_fixation", 0.0))
        year1_root = float(year1_crop.get("root_depth_m", 1.0))

        if prev_heavy or prev_build <= 0.35:
            # Field just came out of a heavy feeder like Corn, Potatoes, or Cabbage
            compaction_need = clip(compaction_need + 0.15, 0.2, 1.0)
            if year1_build >= 0.75 or year1_nfix >= 0.5:
                # Reward planting a soil-rebuilding legume or cover crop in Year 1
                prev_soil_delta = 0.045 + 0.015 * clip(year1_root / 2.0, 0.0, 1.0)
            elif year1_build <= 0.35:
                # Penalize planting another soil-depleting crop immediately in Year 1
                prev_soil_delta = -0.045
        elif prev_build >= 0.75:
            # Prior legume or cover crop left organic residue that boosts starting soil condition
            prev_soil_delta = 0.025

    regen_scores: list[float] = []
    for crop in crop_rows:
        build = float(crop.get("soil_building_score", 0.5))
        root_norm = clip(float(crop.get("root_depth_m", 1.0)) / 2.2, 0.0, 1.0)
        drain_fit = soil_drainage_score(soil, crop)
        crop_regen = (
            0.55 * build
            + 0.25 * (root_norm * compaction_need + build * (1.0 - compaction_need))
            + 0.20 * drain_fit
        )
        regen_scores.append(crop_regen)

    regen_avg = statistics.mean(regen_scores)
    return clip(0.40 * s_base + 0.60 * regen_avg + prev_soil_delta, 0.0, 1.0)


def field_water_supply_score(climate: dict[str, Any]) -> float:
    """
    Estimate how much usable water a field has from drought index, soil moisture,
    year-over-year drought trend, wind-driven evaporation (WS2M), and sunlight
    evaporation (ALLSKY_SFC_SW_DWN).
    """
    # Lower drought index means wetter conditions, so we subtract from 1.0
    drought_score = 1.0 - clip(float(climate.get("drought_index", 0.25)), 0.0, 1.0)

    # Soil moisture of 0.50 m3/m3 or higher maps to a full 1.0 moisture score
    moisture_score = clip(float(climate.get("soil_moisture_avg", 0.30)) / 0.5, 0.0, 1.0)

    # Penalize fields where drought got worse from last year to this year
    trend_penalty = clip(float(climate.get("drought_trend", 0.0)) * 1.2, 0.0, 0.20)

    # Moderate to strong wind (> 1.8 m/s) speeds up evaporation from topsoil and transpiration from leaves
    wind_m_s = get_wind_speed_m_s(climate)
    wind_drying_penalty = clip((wind_m_s - 1.8) / 35.0, 0.0, 0.12)

    # Intense sunlight (> 18.0 MJ/m^2/day) heats the soil surface and evaporates moisture faster
    solar = get_solar_irradiance(climate)
    solar_drying_penalty = clip((solar - 18.0) / 70.0, 0.0, 0.08)

    return clip(
        (drought_score + moisture_score) / 2.0
        - trend_penalty
        - wind_drying_penalty
        - solar_drying_penalty,
        0.0,
        1.0,
    )


def crop_water_demand_norm(crop: dict[str, Any]) -> float:
    """Scale crop water demand from 0.0 (150 mm, low water use) to 1.0 (600 mm, thirsty crop)."""
    return clip((float(crop.get("water_demand_mm", 400.0)) - 150.0) / 450.0, 0.0, 1.0)


def water_stress_score(
    supply: float,
    demand_norm: float,
    annual_precip_mm: Optional[float] = None,
    crop_demand_mm: Optional[float] = None,
    wind_speed_m_s: Optional[float] = None,
    solar_irradiance: Optional[float] = None,
    growing_precip_mm: Optional[float] = None,
    soil_awc: Optional[float] = None,
) -> float:
    """
    Weight 2 (water_stress): Score how safely a crop avoids running out of water
    during the active growing season. Uses May-September rainfall plus stored
    root-zone soil moisture rather than full-year snowmelt totals.
    """
    effective_demand_norm = demand_norm
    if wind_speed_m_s is not None and wind_speed_m_s > 3.5:
        wind_transpiration_bump = clip((wind_speed_m_s - 3.5) * 0.03, 0.0, 0.15)
        effective_demand_norm = clip(effective_demand_norm + wind_transpiration_bump, 0.0, 1.0)

    if solar_irradiance is not None and solar_irradiance > 18.5:
        solar_transpiration_bump = clip((solar_irradiance - 18.5) * 0.015, 0.0, 0.10)
        effective_demand_norm = clip(effective_demand_norm + solar_transpiration_bump, 0.0, 1.0)

    base_stress = 1.0 - (1.0 - supply) * effective_demand_norm
    if (annual_precip_mm is None and growing_precip_mm is None) or crop_demand_mm is None:
        return clip(base_stress, 0.0, 1.0)

    if growing_precip_mm is not None:
        stored_root_water_mm = float(soil_awc or 0.18) * 600.0
        usable_water_mm = float(growing_precip_mm) + stored_root_water_mm
    else:
        usable_water_mm = float(annual_precip_mm or 900.0) * 0.62

    precip_adequacy = clip(
        usable_water_mm / max(float(crop_demand_mm) * 1.10, 1.0), 0.0, 1.0
    )
    return clip(0.65 * base_stress + 0.35 * precip_adequacy, 0.0, 1.0)


def climate_resilience_score(
    climate: dict[str, Any], crop_rows: Optional[list[dict[str, Any]]] = None
) -> float:
    """
    Weight 3 (climate_res): Score how well the field and rotation handle weather
    swings using rain anomalies, NDVI plant health, summer heat, wind stress,
    sunlight suitability, crop temperature fit, and functional crop family diversity.
    """
    anomaly = float(climate.get("anomaly_precip_pct", 0.0))
    anomaly_score = clip((anomaly + 40.0) / 60.0, 0.0, 1.0)

    ndvi_score = clip(float(climate.get("ndvi_avg", 0.70)) / 0.9, 0.0, 1.0)

    anom_trend_penalty = clip(
        -float(climate.get("precip_anom_trend", 0.0)) / 40.0, 0.0, 0.25
    )
    summer_heat_penalty = clip(
        (float(climate.get("summer_temp_c", 22.0)) - 24.5) / 8.0, 0.0, 0.15
    )

    c_base = clip(
        (anomaly_score + ndvi_score) / 2.0
        - 0.5 * (anom_trend_penalty + summer_heat_penalty),
        0.0,
        1.0,
    )

    if not crop_rows:
        return c_base

    unique_types = len({c.get("crop_type", "") for c in crop_rows})
    diversity_score = clip(unique_types / min(len(crop_rows), 3), 0.0, 1.0)
    temp_fit_avg = statistics.mean([crop_temperature_fit(c, climate) for c in crop_rows])
    w_safety = wind_stress_score(climate, crop_rows)
    sun_fit = sunlight_suitability_score(climate, crop_rows)

    c_buffer = (
        0.40 * diversity_score
        + 0.25 * temp_fit_avg
        + 0.20 * w_safety
        + 0.15 * sun_fit
    )

    return clip(0.40 * c_base + 0.60 * c_buffer, 0.0, 1.0)


def soil_compatibility_score(
    soil: dict[str, Any],
    crop: dict[str, Any],
    climate: Optional[dict[str, Any]] = None,
) -> float:
    """
    Weight 7 base (soil_compat): Check how closely a crop's optimal pH window,
    clay texture window, drainage tolerance, and temperature range match the field.
    Any field value inside [optimal_min, optimal_max] scores a full 1.0 plateau.
    """
    ph = float(soil.get("ph", 6.5))
    ph_min = float(crop.get("optimal_ph_min", 5.8))
    ph_max = float(crop.get("optimal_ph_max", 7.0))
    if ph_min <= ph <= ph_max:
        ph_score = 1.0
    else:
        ph_dist = (ph_min - ph) if ph < ph_min else (ph - ph_max)
        ph_score = clip(1.0 - ph_dist / 1.5, 0.0, 1.0)

    clay = float(soil.get("clay_pct", 25.0))
    clay_min = float(crop.get("optimal_clay_min", 15.0))
    clay_max = float(crop.get("optimal_clay_max", 40.0))
    if clay_min <= clay <= clay_max:
        clay_score = 1.0
    else:
        clay_dist = (clay_min - clay) if clay < clay_min else (clay - clay_max)
        clay_score = clip(1.0 - clay_dist / 15.0, 0.0, 1.0)

    drain_score = soil_drainage_score(soil, crop)
    temp_score = crop_temperature_fit(crop, climate)

    return clip(
        0.45 * ph_score + 0.20 * clay_score + 0.20 * drain_score + 0.15 * temp_score,
        0.0,
        1.0,
    )


def yield_potential_score(
    crop: dict[str, Any], climate: Optional[dict[str, Any]] = None
) -> float:
    """
    Weight 5 (yield): Normalize each crop's yield against its own regional
    benchmark yield (benchmark_yield_t_ha) blended with category-scaled harvest
    output so dry grains and legumes are compared fairly against high-water
    vegetables, then adjust for growing-season sunlight and temperature fit.
    """
    typical_y = float(crop.get("typical_yield_t_ha", 0.0))
    if typical_y <= 0.0:
        return 0.0

    ctype = str(crop.get("crop_type", "")).lower()
    category_scale_map = {
        "legume": 4.2,
        "forage_legume": 10.5,
        "grain": 11.5,
        "oilseed": 3.5,
        "vegetable": 36.0,
        "root_veg": 35.0,
        "orchard": 28.0,
        "vineyard": 12.5,
        "berry": 9.5,
        "agroforestry": 5.0,
    }
    cat_scale = category_scale_map.get(ctype, 12.0)

    benchmark_y = float(crop.get("benchmark_yield_t_ha", 0.0))
    if benchmark_y > 0.0:
        rel_yield = clip(typical_y / benchmark_y, 0.0, 1.0)
        tonnage_index = clip(typical_y / cat_scale, 0.25, 1.0)
        base_yield = 0.65 * rel_yield + 0.35 * tonnage_index
    else:
        base_yield = clip(typical_y / cat_scale, 0.0, 1.0)

    if climate is None:
        return clip(base_yield, 0.0, 1.0)

    solar = get_solar_irradiance(climate)
    solar_factor = clip(0.92 + (solar - 14.0) * 0.018, 0.88, 1.06)
    temp_factor = 0.85 + 0.15 * crop_temperature_fit(crop, climate)
    return clip(base_yield * solar_factor * temp_factor, 0.0, 1.0)


def sequence_transition_analysis(
    crop_rows: list[dict[str, Any]],
    soil: dict[str, Any],
    previous_crops: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Check how well each crop in the sequence sets up the next year's crop,
    including both the transition from the previously farmed crop into Year 1
    and the multi-year loop. Penalizes planting the same crop or crop family
    back to back, repeating root/vegetable disease hosts within 2 years, or
    running heavy P/K feeders consecutively without soil recovery.
    """
    n = len(crop_rows)
    if n == 0:
        return {
            "transition_score": 0.0,
            "n_carryover_bonus": 0.0,
            "penalty_multiplier": 1.0,
            "repeat_crop_count": 0,
            "previous_crop_effect": {
                "has_previous_crop": False,
                "previous_crop_ids": [],
                "previous_crop_names": [],
                "year1_transition": "none",
                "prev_n_carryover_credit": 0.0,
                "prev_soil_recovery_bonus": 0.0,
                "prev_penalty_applied": 0.0,
            },
        }

    def _guild(c_obj: dict[str, Any]) -> str:
        ct = str(c_obj.get("crop_type", ""))
        return "legume" if ct in ("legume", "forage_legume") else ct

    prev_list = [c for c in (previous_crops or []) if isinstance(c, dict) and c.get("crop_id")]
    prev_ids = [str(c.get("crop_id", "")) for c in prev_list]
    prev_names = [str(c.get("crop_name", c.get("crop_id", ""))) for c in prev_list]

    if n == 1:
        single_crop = crop_rows[0]
        prev_repeat = 1 if (prev_list and prev_list[-1].get("crop_id") == single_crop.get("crop_id")) else 0
        single_pen = 0.65 if prev_repeat else 0.75
        return {
            "transition_score": 0.30,
            "n_carryover_bonus": 0.0,
            "penalty_multiplier": single_pen,
            "repeat_crop_count": 1 + prev_repeat,
            "previous_crop_effect": {
                "has_previous_crop": bool(prev_list),
                "previous_crop_ids": prev_ids,
                "previous_crop_names": prev_names,
                "year1_transition": "monoculture_repeat_penalty" if prev_repeat else "single_crop_check",
                "prev_n_carryover_credit": 0.0,
                "prev_soil_recovery_bonus": 0.0,
                "prev_penalty_applied": round(0.75 - single_pen, 3),
            },
        }

    repeat_crop_count = 0
    same_type_count = 0
    redundant_nfix_count = 0
    disease_window_hits = 0
    heavy_pk_back_to_back = 0
    n_credit_total = 0.0
    root_alt_total = 0.0

    # For a 2-year rotation [A, B], step 0 (A->B) and step 1 (B->A) are the same undirected pair
    pair_steps = 1 if n == 2 else n

    for i in range(n):
        curr = crop_rows[i]
        nxt = crop_rows[(i + 1) % n]

        curr_type = str(curr.get("crop_type", ""))
        nxt_type = str(nxt.get("crop_type", ""))
        curr_guild = _guild(curr)
        nxt_guild = _guild(nxt)

        if i < pair_steps:
            if curr.get("crop_id") == nxt.get("crop_id"):
                repeat_crop_count += 1
            elif curr_guild == nxt_guild:
                same_type_count += 1

            if bool(curr.get("heavy_pk_feeder", False)) and bool(nxt.get("heavy_pk_feeder", False)):
                if float(curr.get("nitrogen_fixation", 0.0)) < 0.5 and float(nxt.get("nitrogen_fixation", 0.0)) < 0.5:
                    heavy_pk_back_to_back += 1

        curr_nfix = float(curr.get("nitrogen_fixation", 0.0))
        nxt_nfix = float(nxt.get("nitrogen_fixation", 0.0))
        if curr_nfix >= 0.5 and nxt_nfix < 0.2:
            # High-demand grains and brassicas/potatoes make the best use of legume or cover-crop N carry-over
            demand_weight = 1.05 if bool(nxt.get("heavy_pk_feeder", False)) else 0.65
            if curr_type == "cover" and bool(nxt.get("heavy_pk_feeder", False)):
                demand_weight = 1.20
            n_credit_total += curr_nfix * demand_weight
        elif curr_nfix >= 0.5 and nxt_nfix >= 0.5 and i < pair_steps:
            # Back-to-back nitrogen fixers (legume->legume, cover->legume, or legume->cover) waste soil N credit
            redundant_nfix_count += 2

        root_diff = abs(float(curr.get("root_depth_m", 1.0)) - float(nxt.get("root_depth_m", 1.0)))
        root_alt_total += clip(root_diff / 1.2, 0.0, 1.0)

    # Check 2-year soil-borne disease host repeats (planting the same root_veg or vegetable every 2nd year)
    if n == 2:
        for c_item in crop_rows:
            if str(c_item.get("crop_type", "")) in ("root_veg", "vegetable"):
                disease_window_hits += 1
    elif n >= 4:
        gap_steps = 2 if n == 4 else n
        for i in range(gap_steps):
            curr = crop_rows[i]
            two_ahead = crop_rows[(i + 2) % n]
            if (
                curr.get("crop_id") == two_ahead.get("crop_id")
                and str(curr.get("crop_type", "")) in ("root_veg", "vegetable")
            ):
                disease_window_hits += 1

    # Evaluate the transition from the previously farmed crop(s) into Year 1 and Year 2
    first_crop = crop_rows[0]
    first_guild = _guild(first_crop)
    first_nfix = float(first_crop.get("nitrogen_fixation", 0.0))
    first_heavy = bool(first_crop.get("heavy_pk_feeder", False))

    prev_n_carryover_credit = 0.0
    prev_soil_recovery_bonus = 0.0
    prev_penalty = 0.0
    year1_transition_label = "no_prior_crop_specified"

    if prev_list:
        last_prev = prev_list[-1]
        prev_id = str(last_prev.get("crop_id", ""))
        prev_type = str(last_prev.get("crop_type", ""))
        prev_guild = _guild(last_prev)
        prev_nfix = float(last_prev.get("nitrogen_fixation", 0.0))
        prev_heavy = bool(last_prev.get("heavy_pk_feeder", False))
        prev_build = float(last_prev.get("soil_building_score", 0.5))

        if prev_id == str(first_crop.get("crop_id", "")):
            repeat_crop_count += 1
            prev_penalty += 0.18
            year1_transition_label = "monoculture_repeat_penalty"
        elif prev_guild == first_guild:
            same_type_count += 1
            prev_penalty += 0.07
            year1_transition_label = "same_family_penalty"
        else:
            year1_transition_label = "clean_family_break"

        if prev_type in ("root_veg", "vegetable") and n >= 2:
            if str(crop_rows[1].get("crop_id", "")) == prev_id:
                disease_window_hits += 1
                prev_penalty += 0.05
                if year1_transition_label == "clean_family_break":
                    year1_transition_label = "year2_disease_window_penalty"
        if len(prev_list) >= 2:
            two_back = prev_list[-2]
            if (
                str(two_back.get("crop_type", "")) in ("root_veg", "vegetable")
                and str(two_back.get("crop_id", "")) == str(first_crop.get("crop_id", ""))
            ):
                disease_window_hits += 1
                prev_penalty += 0.05
                year1_transition_label = "year1_disease_window_penalty"

        if prev_heavy and first_heavy and prev_nfix < 0.5 and first_nfix < 0.5:
            heavy_pk_back_to_back += 1
            prev_penalty += 0.04

        if prev_nfix >= 0.5 and first_nfix < 0.2:
            demand_mult = 0.16 if first_heavy else 0.11
            prev_n_carryover_credit = round(prev_nfix * demand_mult, 3)
            year1_transition_label = "prior_legume_n_carryover"
        elif (prev_heavy or prev_build <= 0.35) and prev_nfix < 0.2 and first_nfix >= 0.5:
            prev_soil_recovery_bonus = round(0.06 + 0.05 * first_nfix, 3)
            year1_transition_label = "soil_recovery_legume_after_heavy_feeder"
        elif prev_nfix >= 0.5 and first_nfix >= 0.5:
            redundant_nfix_count += 1
            prev_penalty += 0.04
            if year1_transition_label == "clean_family_break":
                year1_transition_label = "redundant_n_fixer_penalty"

        prev_root_diff = abs(
            float(last_prev.get("root_depth_m", 1.0)) - float(first_crop.get("root_depth_m", 1.0))
        )
        root_alt_score = clip(
            (root_alt_total + clip(prev_root_diff / 1.2, 0.0, 1.0)) / (n + 1),
            0.0,
            1.0,
        )
        year1_bonus = prev_n_carryover_credit + prev_soil_recovery_bonus
    else:
        oc_deficit = clip((3.0 - float(soil.get("organic_carbon_pct", 2.5))) / 2.0, 0.0, 1.0)
        year1_bonus = (
            0.05
            * (
                first_nfix
                + float(first_crop.get("soil_building_score", 0.5))
            )
            * (0.5 + 0.5 * oc_deficit)
        )
        root_alt_score = clip(root_alt_total / n, 0.0, 1.0)

    n_carryover_bonus = clip(
        n_credit_total / max(n * 0.45, 1.0) + year1_bonus - 0.08 * (redundant_nfix_count / n),
        0.0,
        0.45,
    )

    repeat_ratio = repeat_crop_count / n
    same_type_ratio = same_type_count / n
    pk_mining_ratio = heavy_pk_back_to_back / n
    disease_ratio = disease_window_hits / n
    redundant_n_ratio = redundant_nfix_count / n
    penalty_multiplier = clip(
        1.0
        - 0.35 * repeat_ratio
        - 0.10 * same_type_ratio
        - 0.06 * pk_mining_ratio
        - 0.06 * disease_ratio
        - 0.05 * redundant_n_ratio
        - prev_penalty,
        0.55,
        1.0,
    )

    transition_score = clip(
        (
            0.45 * root_alt_score
            + 0.45 * clip((n_credit_total / max(n * 0.45, 1.0)) + year1_bonus, 0.0, 1.0)
            + 0.10 * (1.0 - clip(prev_penalty * 3.0, 0.0, 1.0))
        )
        * penalty_multiplier,
        0.0,
        1.0,
    )

    return {
        "transition_score": transition_score,
        "n_carryover_bonus": n_carryover_bonus,
        "penalty_multiplier": penalty_multiplier,
        "repeat_crop_count": repeat_crop_count,
        "previous_crop_effect": {
            "has_previous_crop": bool(prev_list),
            "previous_crop_ids": prev_ids,
            "previous_crop_names": prev_names,
            "year1_transition": year1_transition_label,
            "prev_n_carryover_credit": round(prev_n_carryover_credit, 3),
            "prev_soil_recovery_bonus": round(prev_soil_recovery_bonus, 3),
            "prev_penalty_applied": round(prev_penalty, 3),
        },
    }


def score_rotation(
    crop_rows: list[dict[str, Any]],
    soil: dict[str, Any],
    climate: dict[str, Any],
    profile_name: str = "Balanced",
    custom_weights: Optional[dict[str, float]] = None,
    previous_crops: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Calculate all 7 sub-scores (including wind speed, sunlight intensity, and
    previously farmed crop carry-over effects) for a crop sequence and combine
    them using the chosen preset profile (or custom weights) plus the
    repeat-crop penalty multiplier.
    """
    if not crop_rows:
        raise ValueError("crop_rows cannot be empty when scoring a rotation")

    # Get the 7 normalized weights for the active profile
    weights = get_profile_weights(profile_name=profile_name, custom_weights=custom_weights)

    # Analyze crop-to-crop transitions from the previously farmed crop through the multi-year loop
    trans = sequence_transition_analysis(crop_rows, soil, previous_crops=previous_crops)
    wind_m_s = get_wind_speed_m_s(climate)
    solar_mj = get_solar_irradiance(climate)

    # 1. Soil health score (includes drainage, hardpan, wind erosion, and previous-crop recovery)
    s_health = soil_health_score(
        soil, crop_rows, climate=climate, previous_crops=previous_crops
    )

    # 2. Water stress safety score (uses growing-season rain + AWC root-zone storage)
    supply = field_water_supply_score(climate)
    annual_precip = climate.get("annual_precip_mm") or climate.get("estimated_annual_precip_mm")
    growing_precip = climate.get("growing_season_precip_mm")
    soil_awc = soil.get("awc", 0.18)
    w_stress = statistics.mean(
        [
            water_stress_score(
                supply,
                crop_water_demand_norm(c),
                annual_precip,
                float(c.get("water_demand_mm", 400.0)),
                wind_speed_m_s=wind_m_s,
                solar_irradiance=solar_mj,
                growing_precip_mm=growing_precip,
                soil_awc=soil_awc,
            )
            for c in crop_rows
        ]
    )

    # 3. Climate resilience score (includes crop diversity, thermal fit, wind safety, and sunlight fit)
    c_res = climate_resilience_score(climate, crop_rows)

    # 4. Nitrogen fixation score (including legume-to-grain carry-over credit)
    n_fix_raw = statistics.mean([float(c.get("nitrogen_fixation", 0.0)) for c in crop_rows])
    n_fix_avg = clip(0.85 * n_fix_raw + 0.95 * trans["n_carryover_bonus"], 0.0, 1.0)

    # 5. Yield potential score (normalized against crop benchmark yield + sunlight and temperature)
    yield_avg = statistics.mean([yield_potential_score(c, climate=climate) for c in crop_rows])

    # 6. Drought tolerance score
    drought_tol_avg = statistics.mean([float(c.get("drought_tolerance", 0.5)) for c in crop_rows])

    # 7. Soil compatibility score (plateau pH/clay fit + drainage + temperature + sequence transition)
    base_compat = statistics.mean(
        [soil_compatibility_score(soil, c, climate=climate) for c in crop_rows]
    )
    soil_compat_avg = clip(0.75 * base_compat + 0.25 * trans["transition_score"], 0.0, 1.0)

    # Standalone wind, sunlight, and drainage scores so the UI or API can show them directly
    w_safety = wind_stress_score(climate, crop_rows)
    sun_score = sunlight_suitability_score(climate, crop_rows)
    drain_fit_avg = statistics.mean([soil_drainage_score(soil, c) for c in crop_rows])

    # Multiply each of the 7 sub-scores by its profile weight
    weighted_sum = (
        weights["soil_health"] * s_health
        + weights["water_stress"] * w_stress
        + weights["climate_res"] * c_res
        + weights["nitrogen_fix"] * n_fix_avg
        + weights["yield"] * yield_avg
        + weights["drought_tol"] * drought_tol_avg
        + weights["soil_compat"] * soil_compat_avg
    )

    # Apply the repeat-crop penalty multiplier to get the final 0.0 to 1.0 score
    total_score = clip(weighted_sum * trans["penalty_multiplier"], 0.0, 1.0)

    seq_ids = [str(c.get("crop_id", "")) for c in crop_rows]
    seq_names = [str(c.get("crop_name", c.get("crop_id", ""))) for c in crop_rows]

    return {
        "profile": profile_name if custom_weights is None else "Custom",
        "seq_ids": " -> ".join(seq_ids),
        "seq_names": " -> ".join(seq_names),
        "total_score": round(total_score, 4),
        "soil_health": round(s_health, 3),
        "water_stress": round(w_stress, 3),
        "climate_res": round(c_res, 3),
        "nitrogen_fixation": round(n_fix_avg, 3),
        "yield_potential": round(yield_avg, 3),
        "drought_tolerance": round(drought_tol_avg, 3),
        "soil_compatibility": round(soil_compat_avg, 3),
        "drainage_suitability": round(drain_fit_avg, 3),
        "wind_safety": round(w_safety, 3),
        "wind_speed_m_s": round(wind_m_s, 2),
        "sunlight_score": round(sun_score, 3),
        "solar_irradiance_mj_m2_day": round(solar_mj, 2),
        "transition_score": round(trans["transition_score"], 3),
        "penalty_multiplier": round(trans["penalty_multiplier"], 3),
        "previous_crop_effect": trans["previous_crop_effect"],
        "weights_used": {k: round(v, 3) for k, v in weights.items()},
        "_raw_sort_key": (
            total_score,
            trans["transition_score"],
            w_stress,
            n_fix_avg,
        ),
    }


def sort_rotations(
    results: list[dict[str, Any]],
    diversify_crop_sets: bool = True,
) -> list[dict[str, Any]]:
    """
    Sort scored rotations from highest to lowest using full floating-point
    precision first, breaking ties by transition_score, water_stress, and
    nitrogen_fixation. When diversify_crop_sets is True, keeps the best-ordered
    sequence for each distinct crop combination at the top of the rankings before
    listing alternative permutations of the same crop set.
    """
    ranked = sorted(
        results,
        key=lambda r: r.get(
            "_raw_sort_key",
            (
                r["total_score"],
                r.get("transition_score", 0.0),
                r["water_stress"],
                r["nitrogen_fixation"],
            ),
        ),
        reverse=True,
    )
    for item in ranked:
        item.pop("_raw_sort_key", None)

    if not diversify_crop_sets or len(ranked) <= 1:
        return ranked

    primary_picks: list[dict[str, Any]] = []
    secondary_permutations: list[dict[str, Any]] = []
    seen_crop_sets: set[tuple[str, ...]] = set()

    for item in ranked:
        seq_str = str(item.get("seq_ids", ""))
        crop_set_key = tuple(sorted(part.strip() for part in seq_str.split("->") if part.strip()))
        if crop_set_key and crop_set_key not in seen_crop_sets:
            seen_crop_sets.add(crop_set_key)
            primary_picks.append(item)
        else:
            secondary_permutations.append(item)

    return primary_picks + secondary_permutations


def compare_profiles_for_rotation(
    crop_rows: list[dict[str, Any]],
    soil: dict[str, Any],
    climate: dict[str, Any],
    previous_crops: Optional[list[dict[str, Any]]] = None,
) -> dict[str, dict[str, Any]]:
    """
    Score the same crop rotation across all 5 preset profiles so the user or UI
    can see how different farmer priorities change the score.
    """
    return {
        profile_name: score_rotation(
            crop_rows,
            soil,
            climate,
            profile_name=profile_name,
            previous_crops=previous_crops,
        )
        for profile_name in PROFILES
    }
