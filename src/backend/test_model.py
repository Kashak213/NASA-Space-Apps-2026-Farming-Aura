"""
Interactive terminal testing program for the crop rotation model.

Lets you manually enter a farm's latitude and longitude, pick which crops
you want to grow, choose a scoring priority profile (like Balanced, Max Yield,
Water Conservation, Soil Health First, Climate Resilient, or Custom weights),
and see the live NASA weather data, USDA soil report, and top-ranked crop
rotations.
"""

from __future__ import annotations

import sys
from typing import Any, Optional

# Make sure Windows terminals print tables and arrows cleanly
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from crops import load_crops
from main import analyze_farm_request
from scoring import PROFILES, WEIGHT_KEYS


def prompt_float(
    prompt_text: str,
    default_val: float,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
) -> float:
    """
    Ask the user to type a decimal number (like latitude or longitude).
    If the user just presses Enter, return default_val.
    """
    while True:
        raw = input(f"{prompt_text} [default: {default_val}]: ").strip()
        if not raw:
            return default_val
        try:
            val = float(raw)
            if min_val is not None and val < min_val:
                print(f"  -> Value must be at least {min_val}.")
                continue
            if max_val is not None and val > max_val:
                print(f"  -> Value must be at most {max_val}.")
                continue
            return val
        except ValueError:
            print("  -> Please enter a valid number (for example 42.70 or -76.80).")


def prompt_int(prompt_text: str, default_val: int, min_val: int, max_val: int) -> int:
    """
    Ask the user to type a whole number between min_val and max_val.
    If the user just presses Enter, return default_val.
    """
    while True:
        raw = input(f"{prompt_text} ({min_val}-{max_val}) [default: {default_val}]: ").strip()
        if not raw:
            return default_val
        try:
            val = int(raw)
            if min_val <= val <= max_val:
                return val
            print(f"  -> Please enter a number between {min_val} and {max_val}.")
        except ValueError:
            print("  -> Please enter a whole number.")


def prompt_previous_crop(catalog: list[dict[str, Any]]) -> Optional[list[str]]:
    """
    Ask the user what crop (or sequence of crops) was already farmed on the
    field prior to Year 1 so the model can factor in nitrogen carry-over, soil
    compaction recovery, and pest/disease break rules.
    """
    print("\n" + "=" * 74)
    print("  STEP 2A: WHAT CROP WAS ALREADY FARMED ON THIS FIELD?")
    print("=" * 74)
    print(f"  {'#':<4} {'ID':<6} {'Crop Name':<42} {'Family':<14}")
    print(f"  {'-' * 4} {'-' * 6} {'-' * 42} {'-' * 14}")
    for idx, crop in enumerate(catalog, 1):
        print(
            f"  {idx:<4} {crop['crop_id']:<6} {crop['crop_name'][:42]:<42} "
            f"{crop['crop_type']:<14}"
        )

    print("\n  Enter the crop that was farmed last season (number, ID like C02, or name like Field Corn).")
    print("  Press Enter if no prior crop history is known.")
    raw = input("\n  Already farmed crop(s): ").strip()
    if not raw or raw.lower() in ("none", "no", "skip"):
        return None

    chosen_prev: list[str] = []
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        if token.isdigit():
            num = int(token)
            if 1 <= num <= len(catalog):
                chosen_prev.append(str(catalog[num - 1]["crop_id"]))
                continue
        chosen_prev.append(token)

    return chosen_prev if chosen_prev else None


def prompt_crops(catalog: list[dict[str, Any]]) -> Optional[list[str]]:
    """
    Show the numbered table of all 17 New York crop groups and let the user type
    crop numbers (1, 2, 3), crop IDs (C01, C02), crop names (Field Corn, Soybeans),
    or crop types (grain, legume, vegetable). Pressing Enter selects all crops.
    """
    print("\n" + "=" * 74)
    print("  STEP 2B: CHOOSE CROPS TO FARM IN THE NEW ROTATION")
    print("=" * 74)
    print(f"  {'#':<4} {'ID':<6} {'Crop Name':<36} {'Family':<14} {'Water (mm)'}")
    print(f"  {'-' * 4} {'-' * 6} {'-' * 36} {'-' * 14} {'-' * 10}")
    for idx, crop in enumerate(catalog, 1):
        print(
            f"  {idx:<4} {crop['crop_id']:<6} {crop['crop_name']:<36} "
            f"{crop['crop_type']:<14} {crop['water_demand_mm']}"
        )

    print("\n  Enter crops separated by commas.")
    print("  You can type numbers (2, 3, 11), IDs (C02, C03, C11), names (Corn, Soybeans, Potatoes),")
    print("  or crop families (grain, legume, vegetable). Press Enter to test all 17 crop groups.")

    raw = input("\n  Your crop selection: ").strip()
    if not raw or raw.lower() == "all":
        return None

    # Convert any menu numbers (like "1" -> "C01", "2" -> "C02") while keeping names or IDs as-is
    chosen: list[str] = []
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        if token.isdigit():
            num = int(token)
            if 1 <= num <= len(catalog):
                chosen.append(str(catalog[num - 1]["crop_id"]))
                continue
        chosen.append(token)

    return chosen if chosen else None


def prompt_scoring_profile() -> tuple[str, Optional[dict[str, float]]]:
    """
    Let the user pick one of the 5 preset scoring systems (Balanced, Max Yield,
    Water Conservation, Soil Health First, Climate Resilient) by number or name,
    or enter custom weights for the 7 factors.
    """
    profile_names = list(PROFILES.keys())

    print("\n" + "=" * 74)
    print("  STEP 3: CHOOSE SCORING SYSTEM (FARMER PRIORITY PROFILE)")
    print("=" * 74)
    for idx, name in enumerate(profile_names, 1):
        w = PROFILES[name]
        print(
            f"  {idx}. {name:<20} "
            f"(soil={w['soil_health']:.2f}, water={w['water_stress']:.2f}, "
            f"climate={w['climate_res']:.2f}, n_fix={w['nitrogen_fix']:.2f}, "
            f"yield={w['yield']:.2f}, drought={w['drought_tol']:.2f})"
        )
    print(f"  {len(profile_names) + 1}. Custom Weights       (type your own 7 weights)")

    while True:
        raw = input("\n  Select scoring system (1-6 or name) [default: 1 (Balanced)]: ").strip()
        if not raw:
            return "Balanced", None

        # Check if the user typed a menu number (1 through 6)
        if raw.isdigit():
            choice = int(raw)
            if 1 <= choice <= len(profile_names):
                return profile_names[choice - 1], None
            if choice == len(profile_names) + 1:
                return "Custom", prompt_custom_weights()

        # Check if the user typed a profile name like "Max Yield" or "maximum yield"
        cleaned = raw.lower()
        if "max" in cleaned or "yield" in cleaned:
            return "Max Yield", None
        if "water" in cleaned:
            return "Water Conservation", None
        if "soil" in cleaned:
            return "Soil Health First", None
        if "climate" in cleaned:
            return "Climate Resilient", None
        if "bal" in cleaned:
            return "Balanced", None
        if "custom" in cleaned:
            return "Custom", prompt_custom_weights()

        print("  -> Could not match that profile. Enter a number 1-6 or a profile name.")


def prompt_custom_weights() -> dict[str, float]:
    """
    Ask the user to enter a weight for each of the 7 scoring factors.
    scoring.py automatically normalizes these so they add up to 1.0.
    """
    print("\n  Enter a weight for each factor (any positive numbers, they will be normalized to 1.0):")
    defaults = PROFILES["Balanced"]
    custom: dict[str, float] = {}
    for key in WEIGHT_KEYS:
        custom[key] = prompt_float(f"   - {key}", defaults[key])
    return custom


def display_results(result: dict[str, Any]) -> None:
    """Print the fetched NASA weather, USDA soil lab data, and ranked rotations."""
    coords = result["coordinates"]
    sources = result["data_sources"]
    soil = result["soil"]
    climate = result["climate"]

    print("\n" + "=" * 74)
    print(f"  MODEL RESULTS FOR ({coords['lat']}, {coords['lon']}) | PROFILE: {result['profile_used'].upper()}")
    print("=" * 74)

    # 1. Print NASA POWER weather summary and USDA SSURGO soil summary
    print(f"\n  [1] NASA POWER Weather Data (source: {sources['nasa_power']}, region: {climate.get('region_matched', 'NY')})")
    print(
        f"      Growing-Season Sunlight:      {climate.get('growing_season_solar_mj_m2_day', climate['allsky_sfc_sw_dwn_avg'])} MJ/m^2/day (Annual: {climate['allsky_sfc_sw_dwn_avg']})\n"
        f"      Wind Speed at 2m (WS2M):      {climate.get('growing_season_wind_m_s', climate['ws2m_avg_m_s'])} m/s\n"
        f"      Precipitation (Grow / Year):  {climate.get('growing_season_precip_mm')} mm (May-Sep) / {climate['annual_precip_mm']} mm/year\n"
        f"      Temp (Growing / Summer):      {climate.get('growing_season_temp_c')} C / {climate['summer_temp_c']} C\n"
        f"      Root-Zone Wetness & Drought:  GWETROOT={climate.get('growing_season_gwetroot')} | Moisture={climate['soil_moisture_avg']} | Drought={climate['drought_index']}\n"
        f"      2023->2024 Climate Trends:    Rain Trend={climate.get('precip_anom_trend')}% | Drought Trend={climate.get('drought_trend')}"
    )

    print(f"\n  [2] USDA SSURGO Soil Data (source: {sources['usda_soil']})")
    print(
        f"      Map Unit Name:      {soil['map_unit_name']} ({soil['drainage_class']})\n"
        f"      Organic Carbon:     {soil['organic_carbon_pct']}% (Organic Matter: {soil['organic_matter_pct']}%)\n"
        f"      Soil pH:            {soil['ph']} | Topsoil BD: {soil['bulk_density']} g/cm3 | Subsoil BD: {soil.get('subsoil_bulk_density')} g/cm3 | CEC: {soil['cec']}\n"
        f"      Texture (S/Si/C):   {soil['sand_pct']}% Sand / {soil['silt_pct']}% Silt / {soil['clay_pct']}% Clay\n"
        f"      Baseline Soil Score: {soil['baseline_soil_score']} (Drainage Score: {soil.get('drainage_score')})"
    )

    # 2. Print individual crop suitability scores for the user's selected crops
    print("\n  [3] Individual Crop Suitability on This Field:")
    print(f"      {'ID':<5} {'Crop Name':<42} {'SoilFit':>8} {'Drain':>7} {'Water':>7} {'Yield':>7}")
    print(f"      {'-' * 5} {'-' * 42} {'-' * 8} {'-' * 7} {'-' * 7} {'-' * 7}")
    for item in result["individual_crop_suitability"]:
        print(
            f"      {item['crop_id']:<5} {item['crop_name'][:42]:<42} "
            f"{item['soil_compatibility']:>8.3f} {item.get('drainage_suitability', 0.85):>7.3f} "
            f"{item['water_stress']:>7.3f} {item['yield_potential']:>7.3f}"
        )

    # 3. If the user entered 2+ specific crops, show the score for their exact sequence order
    user_seq = result.get("user_sequence_score")
    if user_seq is not None:
        print("\n  [4] Score for Your Exact Entered Sequence Order:")
        print(f"      Sequence:    {user_seq['seq_names']}")
        print(
            f"      Total Score: {user_seq['total_score']:.4f} "
            f"(Penalty Multiplier: {user_seq['penalty_multiplier']}, "
            f"Transition Score: {user_seq['transition_score']})"
        )

    # 4. Print the top-ranked multi-year crop rotations
    print(f"\n  [5] Top Recommended Rotations (out of {result['total_candidates_evaluated']} evaluated):")
    print(
        f"      {'Rank':<5} {'Rotation Sequence':<20} {'Total':>7} "
        f"{'SoilH':>6} {'Water':>6} {'ClimR':>6} {'N-Fix':>6} {'Yield':>6} {'Wind':>6} {'Sun':>6}"
    )
    print(
        f"      {'-' * 5} {'-' * 20} {'-' * 7} "
        f"{'-' * 6} {'-' * 6} {'-' * 6} {'-' * 6} {'-' * 6} {'-' * 6} {'-' * 6}"
    )
    for idx, rot in enumerate(result["recommended_rotations"], 1):
        print(
            f"      #{idx:<4} {rot['seq_ids']:<20} {rot['total_score']:>7.4f} "
            f"{rot['soil_health']:>6.3f} {rot['water_stress']:>6.3f} "
            f"{rot['climate_res']:>6.3f} {rot['nitrogen_fixation']:>6.3f} "
            f"{rot['yield_potential']:>6.3f} {rot['wind_safety']:>6.3f} {rot['sunlight_score']:>6.3f}"
        )
        print(f"            -> {rot['seq_names']}")
        prev_eff = rot.get("previous_crop_effect", {})
        if prev_eff.get("has_previous_crop"):
            prev_names_str = ", ".join(prev_eff.get("previous_crop_names", []))
            print(
                f"               [Prior Crop: {prev_names_str} -> Year 1 Effect: {prev_eff.get('year1_transition')} "
                f"| N-Carryover: +{prev_eff.get('prev_n_carryover_credit', 0.0):.3f} "
                f"| Soil Recovery: +{prev_eff.get('prev_soil_recovery_bonus', 0.0):.3f} "
                f"| Penalty: -{prev_eff.get('prev_penalty_applied', 0.0):.3f}]"
            )

    # 5. Show how the #1 winning rotation scores across all 5 preset profiles
    comparison = result.get("top_rotation_profile_comparison", {})
    if comparison and result["recommended_rotations"]:
        top_name = result["recommended_rotations"][0]["seq_names"]
        print(f"\n  [6] How #1 Rotation ({top_name}) Scores Across All 5 Profiles:")
        for pname, pscore in comparison.items():
            marker = " <-- (Selected)" if pname == result["profile_used"] else ""
            print(f"      - {pname:<20}: {pscore['total_score']:.4f}{marker}")


def run_interactive_tester() -> None:
    """Main interactive loop so you can test as many locations, crops, and profiles as you want."""
    catalog = load_crops()

    print("\n" + "=" * 74)
    print("  FIELD SHIFT - INTERACTIVE CROP ROTATION MODEL TESTER")
    print("=" * 74)

    while True:
        print("\n" + "=" * 74)
        print("  STEP 1: ENTER FARM COORDINATES (LATITUDE & LONGITUDE)")
        print("  (Examples: Finger Lakes NY = 42.70, -76.80 | Hudson Valley NY = 41.75, -74.08)")
        print("=" * 74)
        lat = prompt_float("  Enter Latitude ", 42.70, min_val=-90.0, max_val=90.0)
        lon = prompt_float("  Enter Longitude", -76.80, min_val=-180.0, max_val=180.0)

        previous_crops = prompt_previous_crop(catalog)
        selected_crops = prompt_crops(catalog)
        profile_name, custom_weights = prompt_scoring_profile()

        print("\n" + "=" * 74)
        print("  STEP 4: ROTATION SETTINGS")
        print("=" * 74)
        rotation_length = prompt_int("  How many years in the rotation?", default_val=3, min_val=2, max_val=5)
        top_n = prompt_int("  How many top recommendations to display?", default_val=5, min_val=1, max_val=15)

        print("\n  Fetching NASA POWER weather + USDA SSURGO soil data and scoring rotations...")
        payload = {
            "lat": lat,
            "lon": lon,
            "previous_crops": previous_crops,
            "selected_crops": selected_crops,
            "profile_name": profile_name,
            "custom_weights": custom_weights,
            "rotation_length": rotation_length,
            "top_n": top_n,
        }

        try:
            result = analyze_farm_request(payload)
            display_results(result)
        except Exception as exc:
            print(f"\n  [ERROR] Failed to run model: {exc}")

        again = input("\n  Would you like to test another location or crop setup? (y/n) [default: n]: ").strip().lower()
        if again not in ("y", "yes"):
            print("\n  Exiting interactive model tester.\n")
            break


if __name__ == "__main__":
    run_interactive_tester()
