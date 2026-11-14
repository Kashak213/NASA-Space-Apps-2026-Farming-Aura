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
    or a standard climate dict. Defaults to 3.0 m/s (a gentle breeze) if not provided.
    """
    # Check each possible key name used by nasa_client.py or mock climate files
    for key in ("ws2m_avg_m_s", "WS2M", "wind_speed_m_s"):
        if climate.get(key) is not None:
            return float(climate[key])
    return 3.0


def get_solar_irradiance(climate: dict[str, Any]) -> float:
    """
    Read sunlight intensity (All Sky Surface Shortwave Downward Irradiance, in
    MJ/m^2/day for the NASA POWER AG community) from a climate dictionary.
    Defaults to 14.0 MJ/m^2/day (a normal temperate farming average) if missing.
    """
    # Check the key names returned by nasa_client.py or custom climate inputs
    for key in ("allsky_sfc_sw_dwn_avg", "ALLSKY_SFC_SW_DWN", "solar_irradiance_mj_m2_day"):
        if climate.get(key) is not None:
            return float(climate[key])
    return 14.0


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

    # Wind at or below 2.5 m/s is calm (1.0). Wind up near 8.5 m/s is very strong (0.0).
    field_wind_safety = 1.0 - clip((wind_m_s - 2.5) / 6.0, 0.0, 1.0)
    if not crop_rows:
        return field_wind_safety

    # Cover crops and sturdy deep-rooted crops hold soil in place and resist wind damage better
    crop_wind_buffers: list[float] = []
    for crop in crop_rows:
        soil_hold = float(crop.get("soil_building_score", 0.5))
        drought_hardiness = float(crop.get("drought_tolerance", 0.5))
        crop_wind_buffers.append(0.50 * soil_hold + 0.50 * drought_hardiness)

    crop_buffer_avg = statistics.mean(crop_wind_buffers)
    # Blend field wind safety (70%) with how well the chosen crops handle wind (30%)
    return clip(0.70 * field_wind_safety + 0.30 * crop_buffer_avg, 0.0, 1.0)


def sunlight_suitability_score(
    climate: dict[str, Any], crop_rows: Optional[list[dict[str, Any]]] = None
) -> float:
    """
    Calculate a 0.0 to 1.0 sunlight suitability score from NASA POWER shortwave
    irradiance (ALLSKY_SFC_SW_DWN, in MJ/m^2/day). Plants need sunlight for
    photosynthesis, where 13 to 20 MJ/m^2/day is a strong growing range. Very low
    sunlight slows down high-yield crops like corn, while extreme sunlight (> 22)
    increases leaf heating and water loss unless crops are drought tolerant.
    """
    solar = get_solar_irradiance(climate)

    # Map sunlight intensity: 16.5 MJ/m^2/day is the sweet spot (1.0), dropping off if
    # it is super cloudy (< 8 MJ/m^2/day) or scorching (> 25 MJ/m^2/day)
    field_light_score = 1.0 - clip(abs(solar - 16.5) / 10.0, 0.0, 1.0)
    if not crop_rows:
        return field_light_score

    crop_light_fits: list[float] = []
    for crop in crop_rows:
        # High-yield cash crops (like corn at 10.5 t/ha) crave stronger sunlight (~18 MJ/m^2/day),
        # while cover crops and cool-season legumes do fine around 13 MJ/m^2/day
        yield_norm = clip(float(crop.get("typical_yield_t_ha", 0.0)) / 10.5, 0.0, 1.0)
        ideal_solar = 13.0 + 5.0 * yield_norm
        crop_fit = 1.0 - clip(abs(solar - ideal_solar) / 9.0, 0.0, 1.0)
        crop_light_fits.append(crop_fit)

    return clip(0.60 * field_light_score + 0.40 * statistics.mean(crop_light_fits), 0.0, 1.0)


def field_soil_baseline_score(soil: dict[str, Any]) -> float:
    """
    Score the starting soil quality of a field from 0.0 to 1.0 using organic
    carbon, pH, bulk density, CEC, and how close the sand/clay mix is to loam.
    """
    # Organic carbon: 1% maps to 0.0 (depleted dirt) and 5% maps to 1.0 (rich dark topsoil)
    oc = float(soil.get("organic_carbon_pct", 2.5))
    oc_score = clip((oc - 1.0) / 4.0, 0.0, 1.0)

    # Soil pH: 6.5 is ideal for root nutrient uptake in most farm crops
    ph = float(soil.get("ph", 6.5))
    ph_score = 1.0 - min(abs(ph - 6.5) / 2.0, 1.0)

    # Bulk density: lower numbers mean looser soil that roots and water can move through easily
    bd = float(soil.get("bulk_density", 1.35))
    bd_score = clip((1.7 - bd) / 0.6, 0.0, 1.0)

    # Cation exchange capacity (CEC): higher CEC means clay and organic matter hold onto nutrients better
    cec = float(soil.get("cec", 20.0))
    cec_score = clip(cec / 40.0, 0.0, 1.0)

    # Loam soil usually sits around 40% sand and 25% clay
    sand = float(soil.get("sand_pct", 40.0))
    clay = float(soil.get("clay_pct", 25.0))
    texture_score = 1.0 - clip((abs(sand - 40.0) + abs(clay - 25.0)) / 60.0, 0.0, 1.0)

    # Combine all 5 soil lab metrics into one baseline soil score
    return (
        0.25 * oc_score
        + 0.20 * ph_score
        + 0.25 * bd_score
        + 0.15 * cec_score
        + 0.15 * texture_score
    )


def soil_health_score(
    soil: dict[str, Any],
    crop_rows: Optional[list[dict[str, Any]]] = None,
    climate: Optional[dict[str, Any]] = None,
) -> float:
    """
    Weight 1 (soil_health): Combine the field's baseline soil score with how
    much the crops in the rotation add organic matter, break up packed soil,
    and protect topsoil from blowing away on windy fields.
    """
    s_base = field_soil_baseline_score(soil)

    # If climate data is passed, check if strong winds risk blowing away dry sandy topsoil
    if climate is not None:
        wind_m_s = get_wind_speed_m_s(climate)
        sand_fraction = clip(float(soil.get("sand_pct", 40.0)) / 100.0, 0.0, 1.0)
        # Wind above 4.0 m/s slightly lowers baseline soil score on sandy fields due to wind erosion risk
        wind_erosion_penalty = clip((wind_m_s - 4.0) / 8.0, 0.0, 0.12) * sand_fraction
        s_base = clip(s_base - wind_erosion_penalty, 0.0, 1.0)

    if not crop_rows:
        return s_base

    # Packed fields (high bulk density) benefit more from deep-rooted crops that open up soil channels
    bd = float(soil.get("bulk_density", 1.35))
    compaction_need = clip((bd - 1.15) / 0.45, 0.2, 1.0)

    regen_scores: list[float] = []
    for crop in crop_rows:
        build = float(crop.get("soil_building_score", 0.5))
        root_norm = clip(float(crop.get("root_depth_m", 1.0)) / 2.5, 0.0, 1.0)
        regen_scores.append(
            0.65 * build
            + 0.35 * (root_norm * compaction_need + build * (1.0 - compaction_need))
        )

    regen_avg = statistics.mean(regen_scores)
    # Blend starting soil quality (65%) with how much the rotation rebuilds the soil (35%)
    return clip(0.65 * s_base + 0.35 * regen_avg, 0.0, 1.0)


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

    # Strong wind (> 3.5 m/s) speeds up evaporation from topsoil and transpiration from leaves
    wind_m_s = get_wind_speed_m_s(climate)
    wind_drying_penalty = clip((wind_m_s - 3.5) / 40.0, 0.0, 0.12)

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
) -> float:
    """
    Weight 2 (water_stress): Score how safely a crop avoids running out of water.
    Dry, windy, or intensely sunny fields penalize thirsty crops, especially when
    yearly rain is below crop demand.
    """
    # If wind is strong (> 3.5 m/s) or sunlight is intense (> 18 MJ/m^2/day), plants
    # transpire more water through their leaf stomata, nudging up effective water demand
    effective_demand_norm = demand_norm
    if wind_speed_m_s is not None and wind_speed_m_s > 3.5:
        wind_transpiration_bump = clip((wind_speed_m_s - 3.5) * 0.03, 0.0, 0.15)
        effective_demand_norm = clip(effective_demand_norm + wind_transpiration_bump, 0.0, 1.0)

    if solar_irradiance is not None and solar_irradiance > 18.0:
        solar_transpiration_bump = clip((solar_irradiance - 18.0) * 0.015, 0.0, 0.10)
        effective_demand_norm = clip(effective_demand_norm + solar_transpiration_bump, 0.0, 1.0)

    # Wet fields (supply near 1.0) score high for any crop, while dry fields penalize high-demand crops
    base_stress = 1.0 - (1.0 - supply) * effective_demand_norm
    if annual_precip_mm is None or crop_demand_mm is None:
        return clip(base_stress, 0.0, 1.0)

    # Check if yearly rainfall covers the crop's water need with a 15% safety buffer
    precip_adequacy = clip(
        float(annual_precip_mm) / max(float(crop_demand_mm) * 1.15, 1.0), 0.0, 1.0
    )
    return clip(0.75 * base_stress + 0.25 * precip_adequacy, 0.0, 1.0)


def climate_resilience_score(
    climate: dict[str, Any], crop_rows: Optional[list[dict[str, Any]]] = None
) -> float:
    """
    Weight 3 (climate_res): Score how well the field and rotation handle weather
    swings using rain anomalies, NDVI plant health, summer heat, wind stress (WS2M),
    sunlight suitability (ALLSKY_SFC_SW_DWN), and crop family diversity.
    """
    # Map rainfall anomaly from [-40%, +20%] onto [0.0, 1.0]
    anomaly = float(climate.get("anomaly_precip_pct", 0.0))
    anomaly_score = clip((anomaly + 40.0) / 60.0, 0.0, 1.0)

    # Map satellite NDVI plant greenness onto [0.0, 1.0]
    ndvi_score = clip(float(climate.get("ndvi_avg", 0.70)) / 0.9, 0.0, 1.0)

    # Penalize fields where rain anomalies are dropping fast, summers are hot, or winds are high
    anom_trend_penalty = clip(
        -float(climate.get("precip_anom_trend", 0.0)) / 40.0, 0.0, 0.25
    )
    summer_heat_penalty = clip(
        (float(climate.get("summer_temp_c", 24.0)) - 24.5) / 8.0, 0.0, 0.15
    )
    wind_m_s = get_wind_speed_m_s(climate)
    wind_lodging_penalty = clip((wind_m_s - 4.0) / 25.0, 0.0, 0.12)

    c_base = clip(
        (anomaly_score + ndvi_score) / 2.0
        - 0.5 * (anom_trend_penalty + summer_heat_penalty + wind_lodging_penalty),
        0.0,
        1.0,
    )

    if not crop_rows:
        return c_base

    # Mixing different crop families (grain, legume, oilseed, cover) spreads out weather and wind risk
    unique_types = len({c.get("crop_type", "") for c in crop_rows})
    diversity_score = clip(unique_types / min(len(crop_rows), 3), 0.0, 1.0)
    drought_hedge = statistics.mean([float(c.get("drought_tolerance", 0.5)) for c in crop_rows])
    w_safety = wind_stress_score(climate, crop_rows)
    sun_fit = sunlight_suitability_score(climate, crop_rows)

    # Combine crop diversity (40%), drought hardiness (30%), wind safety (15%), and sunlight fit (15%)
    c_buffer = (
        0.40 * diversity_score
        + 0.30 * drought_hedge
        + 0.15 * w_safety
        + 0.15 * sun_fit
    )

    return clip(0.65 * c_base + 0.35 * c_buffer, 0.0, 1.0)


def soil_compatibility_score(soil: dict[str, Any], crop: dict[str, Any]) -> float:
    """
    Weight 7 base (soil_compat): Check how closely a crop's preferred pH and
    clay percentage match the field's actual soil pH and clay percentage.
    """
    # Compare field pH against the center of the crop's ideal pH window
    ph = float(soil.get("ph", 6.5))
    ph_min = float(crop.get("optimal_ph_min", 5.8))
    ph_max = float(crop.get("optimal_ph_max", 7.0))
    ph_center = (ph_max + ph_min) / 2.0
    ph_half = (ph_max - ph_min) / 2.0 + 0.5
    ph_score = max(0.0, 1.0 - abs(ph - ph_center) / ph_half)

    # Compare field clay % against the center of the crop's ideal clay window
    clay = float(soil.get("clay_pct", 25.0))
    clay_min = float(crop.get("optimal_clay_min", 15.0))
    clay_max = float(crop.get("optimal_clay_max", 40.0))
    clay_center = (clay_max + clay_min) / 2.0
    clay_half = (clay_max - clay_min) / 2.0 + 5.0
    clay_score = max(0.0, 1.0 - abs(clay - clay_center) / clay_half)

    # Average the pH match and clay match into a single compatibility score
    return (ph_score + clay_score) / 2.0


def yield_potential_score(
    crop: dict[str, Any], climate: Optional[dict[str, Any]] = None
) -> float:
    """
    Weight 5 (yield): Divide a crop's typical yield (t/ha) by 12.0 t/ha, and
    adjust for sunlight intensity (ALLSKY_SFC_SW_DWN) since photosynthesis
    depends on solar radiation to build grain biomass.
    """
    base_yield = clip(float(crop.get("typical_yield_t_ha", 0.0)) / 12.0, 0.0, 1.0)
    if climate is None or base_yield == 0.0:
        return base_yield

    # Sunlight around 14 to 20 MJ/m^2/day supports full photosynthesis (multiplier up to 1.06),
    # while dim/cloudy conditions (< 11 MJ/m^2/day) slightly trim yield potential (down to 0.90)
    solar = get_solar_irradiance(climate)
    solar_factor = clip(0.90 + (solar - 10.0) * 0.016, 0.88, 1.06)
    return clip(base_yield * solar_factor, 0.0, 1.0)


def sequence_transition_analysis(
    crop_rows: list[dict[str, Any]], soil: dict[str, Any]
) -> dict[str, Any]:
    """
    Check how well each crop in the sequence sets up the next year's crop,
    including when the final year loops back to Year 1. Penalizes planting the
    same crop or crop family twice in a row (which builds up pests) and rewards
    legume-to-grain nitrogen carry-over and alternating root depths.
    """
    n = len(crop_rows)
    if n == 0:
        return {
            "transition_score": 0.0,
            "n_carryover_bonus": 0.0,
            "penalty_multiplier": 1.0,
            "repeat_crop_count": 0,
        }
    if n == 1:
        # A 1-crop rotation is a monoculture, so it gets a 0.75 repeat penalty right away
        return {
            "transition_score": 0.3,
            "n_carryover_bonus": 0.0,
            "penalty_multiplier": 0.75,
            "repeat_crop_count": 1,
        }

    repeat_crop_count = 0
    same_type_count = 0
    n_credit_total = 0.0
    root_alt_total = 0.0

    # Walk through each year i and compare it to the following year (i + 1) % n
    for i in range(n):
        curr = crop_rows[i]
        nxt = crop_rows[(i + 1) % n]
        # Give slightly higher weight to earlier transitions in the rotation
        step_weight = 1.0 - 0.06 * i

        # Check if the exact same crop or the same crop family is planted two years in a row
        if curr.get("crop_id") == nxt.get("crop_id"):
            repeat_crop_count += 1
        elif curr.get("crop_type") == nxt.get("crop_type"):
            same_type_count += 1

        # Legumes fix nitrogen in root nodules, leaving extra soil N for a following grain crop
        curr_nfix = float(curr.get("nitrogen_fixation", 0.0))
        nxt_nfix = float(nxt.get("nitrogen_fixation", 0.0))
        if curr_nfix >= 0.5 and nxt_nfix == 0.0:
            demand_weight = clip(float(nxt.get("typical_yield_t_ha", 5.0)) / 10.5, 0.3, 1.0)
            n_credit_total += curr_nfix * demand_weight * step_weight

        # Alternating shallow and deep roots pulls water and nutrients from different soil layers
        root_diff = abs(float(curr.get("root_depth_m", 1.0)) - float(nxt.get("root_depth_m", 1.0)))
        root_alt_total += clip(root_diff / 1.5, 0.0, 1.0) * step_weight

    # Starting Year 1 with a legume or cover crop helps extra on low-carbon fields
    first_crop = crop_rows[0]
    oc_deficit = clip((3.0 - float(soil.get("organic_carbon_pct", 2.5))) / 2.0, 0.0, 1.0)
    year1_readiness = (
        0.04
        * (
            float(first_crop.get("nitrogen_fixation", 0.0))
            + float(first_crop.get("soil_building_score", 0.5))
        )
        * (0.5 + 0.5 * oc_deficit)
    )

    n_carryover_bonus = clip(n_credit_total / n + year1_readiness, 0.0, 0.25)
    root_alt_score = clip(root_alt_total / n, 0.0, 1.0)

    # Lower the penalty multiplier if the rotation repeats the same crop or crop family back to back
    repeat_ratio = repeat_crop_count / n
    same_type_ratio = same_type_count / n
    penalty_multiplier = clip(
        1.0 - 0.35 * repeat_ratio - 0.08 * same_type_ratio, 0.65, 1.0
    )

    # Combine root alternation and nitrogen carry-over into a single transition score
    transition_score = clip(
        (
            0.50 * root_alt_score
            + 0.50 * clip(n_credit_total / max(n * 0.5, 1.0), 0.0, 1.0)
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
    }


def score_rotation(
    crop_rows: list[dict[str, Any]],
    soil: dict[str, Any],
    climate: dict[str, Any],
    profile_name: str = "Balanced",
    custom_weights: Optional[dict[str, float]] = None,
) -> dict[str, Any]:
    """
    Calculate all 7 sub-scores (including wind speed and sunlight intensity effects)
    for a crop sequence and combine them using the chosen preset profile (or
    custom weights) plus the repeat-crop penalty multiplier.
    """
    if not crop_rows:
        raise ValueError("crop_rows cannot be empty when scoring a rotation")

    # Get the 7 normalized weights for the active profile
    weights = get_profile_weights(profile_name=profile_name, custom_weights=custom_weights)

    # Analyze crop-to-crop transitions around the multi-year loop
    trans = sequence_transition_analysis(crop_rows, soil)
    wind_m_s = get_wind_speed_m_s(climate)
    solar_mj = get_solar_irradiance(climate)

    # 1. Soil health score (includes wind erosion check on sandy soil)
    s_health = soil_health_score(soil, crop_rows, climate=climate)

    # 2. Water stress safety score (includes wind and sunlight drying effects)
    supply = field_water_supply_score(climate)
    annual_precip = climate.get("annual_precip_mm") or climate.get("estimated_annual_precip_mm")
    w_stress = statistics.mean(
        [
            water_stress_score(
                supply,
                crop_water_demand_norm(c),
                annual_precip,
                float(c.get("water_demand_mm", 400.0)),
                wind_speed_m_s=wind_m_s,
                solar_irradiance=solar_mj,
            )
            for c in crop_rows
        ]
    )

    # 3. Climate resilience score (includes wind lodging penalty, wind safety, and sunlight fit)
    c_res = climate_resilience_score(climate, crop_rows)

    # 4. Nitrogen fixation score (including legume-to-grain carry-over credit)
    n_fix_raw = statistics.mean([float(c.get("nitrogen_fixation", 0.0)) for c in crop_rows])
    n_fix_avg = clip(0.85 * n_fix_raw + 0.60 * trans["n_carryover_bonus"], 0.0, 1.0)

    # 5. Yield potential score (adjusted for sunlight photosynthesis intensity)
    yield_avg = statistics.mean([yield_potential_score(c, climate=climate) for c in crop_rows])

    # 6. Drought tolerance score
    drought_tol_avg = statistics.mean([float(c.get("drought_tolerance", 0.5)) for c in crop_rows])

    # 7. Soil compatibility score (pH/clay fit blended with sequence transition score)
    base_compat = statistics.mean([soil_compatibility_score(soil, c) for c in crop_rows])
    soil_compat_avg = clip(0.80 * base_compat + 0.20 * trans["transition_score"], 0.0, 1.0)

    # Standalone wind and sunlight scores so the UI or API can show them directly
    w_safety = wind_stress_score(climate, crop_rows)
    sun_score = sunlight_suitability_score(climate, crop_rows)

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
        "wind_safety": round(w_safety, 3),
        "wind_speed_m_s": round(wind_m_s, 2),
        "sunlight_score": round(sun_score, 3),
        "solar_irradiance_mj_m2_day": round(solar_mj, 2),
        "transition_score": round(trans["transition_score"], 3),
        "penalty_multiplier": round(trans["penalty_multiplier"], 3),
        "weights_used": {k: round(v, 3) for k, v in weights.items()},
    }


def sort_rotations(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sort scored rotations from highest to lowest. Ties on total_score are broken
    by water_stress first (drought safety) and nitrogen_fixation second.
    """
    return sorted(
        results,
        key=lambda r: (r["total_score"], r["water_stress"], r["nitrogen_fixation"]),
        reverse=True,
    )


def compare_profiles_for_rotation(
    crop_rows: list[dict[str, Any]],
    soil: dict[str, Any],
    climate: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """
    Score the same crop rotation across all 5 preset profiles so the user or UI
    can see how different farmer priorities change the score.
    """
    return {
        profile_name: score_rotation(crop_rows, soil, climate, profile_name=profile_name)
        for profile_name in PROFILES
    }
