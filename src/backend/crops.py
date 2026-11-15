"""
Crop catalog, lookup helpers, constraint filters, and rotation generator.

Loads the 13 New York farm crop groups (forage hay, field grains, soybeans,
orchard fruits, grapes, berries, sugar maple, and vegetables) from
data/crops.json, looks up crop traits by ID or name, filters sequences by
farmer equipment or water limits, and generates candidate multi-year crop
rotations for scoring.py.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any, Optional

# Path to src/backend/data/crops.json
BASE_DIR = Path(__file__).resolve().parent
CROPS_JSON_PATH = BASE_DIR / "data" / "crops.json"

# Built-in fallback list of all 13 New York crops in case data/crops.json is missing or empty.
# Each crop includes water demand (mm), legume nitrogen fixation (0 to 1),
# drought tolerance (0 to 1), ideal soil pH and clay windows, typical yield (t/ha),
# root depth (m), and a soil building score (0 to 1).
DEFAULT_CROPS: list[dict[str, Any]] = [
    {
        "crop_id": "C01",
        "crop_name": "Hay & Alfalfa (Haylage)",
        "crop_type": "legume",
        "water_demand_mm": 580.0,
        "nitrogen_fixation": 0.85,
        "drought_tolerance": 0.55,
        "optimal_ph_min": 6.2,
        "optimal_ph_max": 7.5,
        "optimal_clay_min": 18.0,
        "optimal_clay_max": 40.0,
        "typical_yield_t_ha": 9.5,
        "root_depth_m": 2.8,
        "soil_building_score": 0.95,
    },
    {
        "crop_id": "C02",
        "crop_name": "Field Corn (Silage & Grain)",
        "crop_type": "grain",
        "water_demand_mm": 550.0,
        "nitrogen_fixation": 0.0,
        "drought_tolerance": 0.35,
        "optimal_ph_min": 5.8,
        "optimal_ph_max": 7.0,
        "optimal_clay_min": 20.0,
        "optimal_clay_max": 40.0,
        "typical_yield_t_ha": 11.0,
        "root_depth_m": 1.2,
        "soil_building_score": 0.25,
    },
    {
        "crop_id": "C03",
        "crop_name": "Soybeans & Small Grains",
        "crop_type": "legume",
        "water_demand_mm": 420.0,
        "nitrogen_fixation": 0.75,
        "drought_tolerance": 0.60,
        "optimal_ph_min": 6.0,
        "optimal_ph_max": 7.2,
        "optimal_clay_min": 18.0,
        "optimal_clay_max": 45.0,
        "typical_yield_t_ha": 4.2,
        "root_depth_m": 1.3,
        "soil_building_score": 0.85,
    },
    {
        "crop_id": "C04",
        "crop_name": "Apples",
        "crop_type": "orchard",
        "water_demand_mm": 500.0,
        "nitrogen_fixation": 0.0,
        "drought_tolerance": 0.55,
        "optimal_ph_min": 6.0,
        "optimal_ph_max": 7.0,
        "optimal_clay_min": 15.0,
        "optimal_clay_max": 35.0,
        "typical_yield_t_ha": 10.0,
        "root_depth_m": 2.0,
        "soil_building_score": 0.60,
    },
    {
        "crop_id": "C05",
        "crop_name": "Grapes (Juice & Wine)",
        "crop_type": "vineyard",
        "water_demand_mm": 380.0,
        "nitrogen_fixation": 0.0,
        "drought_tolerance": 0.75,
        "optimal_ph_min": 5.5,
        "optimal_ph_max": 7.0,
        "optimal_clay_min": 15.0,
        "optimal_clay_max": 35.0,
        "typical_yield_t_ha": 8.0,
        "root_depth_m": 2.2,
        "soil_building_score": 0.55,
    },
    {
        "crop_id": "C06",
        "crop_name": "Cherries, Peaches, Pears & Plums",
        "crop_type": "orchard",
        "water_demand_mm": 480.0,
        "nitrogen_fixation": 0.0,
        "drought_tolerance": 0.50,
        "optimal_ph_min": 6.0,
        "optimal_ph_max": 7.0,
        "optimal_clay_min": 15.0,
        "optimal_clay_max": 32.0,
        "typical_yield_t_ha": 8.5,
        "root_depth_m": 1.8,
        "soil_building_score": 0.55,
    },
    {
        "crop_id": "C07",
        "crop_name": "Berries",
        "crop_type": "berry",
        "water_demand_mm": 430.0,
        "nitrogen_fixation": 0.0,
        "drought_tolerance": 0.45,
        "optimal_ph_min": 4.8,
        "optimal_ph_max": 6.5,
        "optimal_clay_min": 12.0,
        "optimal_clay_max": 30.0,
        "typical_yield_t_ha": 6.5,
        "root_depth_m": 0.6,
        "soil_building_score": 0.50,
    },
    {
        "crop_id": "C08",
        "crop_name": "Sugar Maple (Maple Syrup)",
        "crop_type": "agroforestry",
        "water_demand_mm": 450.0,
        "nitrogen_fixation": 0.0,
        "drought_tolerance": 0.70,
        "optimal_ph_min": 5.5,
        "optimal_ph_max": 7.2,
        "optimal_clay_min": 15.0,
        "optimal_clay_max": 38.0,
        "typical_yield_t_ha": 4.5,
        "root_depth_m": 2.5,
        "soil_building_score": 0.90,
    },
    {
        "crop_id": "C09",
        "crop_name": "Cabbage",
        "crop_type": "vegetable",
        "water_demand_mm": 440.0,
        "nitrogen_fixation": 0.0,
        "drought_tolerance": 0.40,
        "optimal_ph_min": 6.0,
        "optimal_ph_max": 7.2,
        "optimal_clay_min": 18.0,
        "optimal_clay_max": 38.0,
        "typical_yield_t_ha": 11.5,
        "root_depth_m": 0.6,
        "soil_building_score": 0.30,
    },
    {
        "crop_id": "C10",
        "crop_name": "Onions",
        "crop_type": "root_veg",
        "water_demand_mm": 410.0,
        "nitrogen_fixation": 0.0,
        "drought_tolerance": 0.35,
        "optimal_ph_min": 6.0,
        "optimal_ph_max": 7.0,
        "optimal_clay_min": 12.0,
        "optimal_clay_max": 30.0,
        "typical_yield_t_ha": 10.5,
        "root_depth_m": 0.4,
        "soil_building_score": 0.25,
    },
    {
        "crop_id": "C11",
        "crop_name": "Potatoes",
        "crop_type": "root_veg",
        "water_demand_mm": 480.0,
        "nitrogen_fixation": 0.0,
        "drought_tolerance": 0.40,
        "optimal_ph_min": 5.2,
        "optimal_ph_max": 6.5,
        "optimal_clay_min": 12.0,
        "optimal_clay_max": 32.0,
        "typical_yield_t_ha": 11.8,
        "root_depth_m": 0.7,
        "soil_building_score": 0.20,
    },
    {
        "crop_id": "C12",
        "crop_name": "Sweet Corn, Snap Beans & Green Peas",
        "crop_type": "legume",
        "water_demand_mm": 430.0,
        "nitrogen_fixation": 0.65,
        "drought_tolerance": 0.50,
        "optimal_ph_min": 5.8,
        "optimal_ph_max": 7.0,
        "optimal_clay_min": 15.0,
        "optimal_clay_max": 38.0,
        "typical_yield_t_ha": 7.5,
        "root_depth_m": 0.9,
        "soil_building_score": 0.75,
    },
    {
        "crop_id": "C13",
        "crop_name": "Beets, Carrots, Squash & Pumpkins",
        "crop_type": "vegetable",
        "water_demand_mm": 400.0,
        "nitrogen_fixation": 0.0,
        "drought_tolerance": 0.55,
        "optimal_ph_min": 5.8,
        "optimal_ph_max": 7.0,
        "optimal_clay_min": 12.0,
        "optimal_clay_max": 35.0,
        "typical_yield_t_ha": 9.2,
        "root_depth_m": 0.9,
        "soil_building_score": 0.45,
    },
]

# Perennial tree, vine, berry, maple, and forage hay crops that require specialized
# harvesting gear rather than standard annual row-crop and vegetable equipment
NON_ROW_CROP_IDS: set[str] = {"C01", "C04", "C05", "C06", "C07", "C08"}

# Standard preset New York crop rotations to test or use as fallback
PRESET_ROTATIONS: list[list[str]] = [
    ["C02", "C03"],                # Field Corn (Silage & Grain) -> Soybeans & Small Grains
    ["C03", "C02", "C01"],         # Soybeans & Small Grains -> Field Corn -> Hay & Alfalfa
    ["C01", "C02", "C03"],         # Hay & Alfalfa -> Field Corn -> Soybeans & Small Grains
    ["C03", "C02", "C11"],         # Soybeans & Small Grains -> Field Corn -> Potatoes
    ["C12", "C09", "C10"],         # Sweet Corn, Snap Beans & Green Peas -> Cabbage -> Onions
    ["C03", "C11", "C13"],         # Soybeans & Small Grains -> Potatoes -> Beets, Carrots, Squash & Pumpkins
    ["C12", "C11", "C09"],         # Sweet Corn, Snap Beans & Green Peas -> Potatoes -> Cabbage
    ["C03", "C09", "C13"],         # Soybeans & Small Grains -> Cabbage -> Beets, Carrots, Squash & Pumpkins
    ["C12", "C10", "C13"],         # Sweet Corn, Snap Beans & Green Peas -> Onions -> Beets, Carrots, Squash & Pumpkins
    ["C02", "C12", "C13"],         # Field Corn -> Sweet Corn, Snap Beans & Green Peas -> Beets, Carrots, Squash & Pumpkins
    ["C04", "C07", "C05"],         # Apples -> Berries -> Grapes (Juice & Wine)
    ["C06", "C04", "C08"],         # Cherries, Peaches, Pears & Plums -> Apples -> Sugar Maple
]


def load_crops(filepath: Optional[Path] = None) -> list[dict[str, Any]]:
    """
    Load the crop catalog from data/crops.json. If the JSON file does not exist
    or is empty, return a copy of DEFAULT_CROPS so the backend never crashes.
    """
    target = filepath or CROPS_JSON_PATH
    if target.exists() and target.stat().st_size > 0:
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(data, list) and len(data) > 0:
                return data
        except Exception:
            pass
    return [dict(c) for c in DEFAULT_CROPS]


def get_crop_by_id(
    crop_id: str, crops: Optional[list[dict[str, Any]]] = None
) -> Optional[dict[str, Any]]:
    """
    Look up a single crop dictionary by its crop_id (for example 'C01' for Hay & Alfalfa).
    Returns None if the crop_id is not found.
    """
    catalog = crops if crops is not None else load_crops()
    target_id = crop_id.strip().upper()
    return next((c for c in catalog if str(c.get("crop_id", "")).upper() == target_id), None)


def get_crop_by_name(
    crop_name: str, crops: Optional[list[dict[str, Any]]] = None
) -> Optional[dict[str, Any]]:
    """
    Look up a single crop dictionary by its name (for example 'Apples' or
    'Grapes (Juice & Wine)'). Checks for an exact case-insensitive match first
    and falls back to a partial name match so searching 'Grapes' or 'Peaches'
    also finds the matching crop group.
    """
    catalog = crops if crops is not None else load_crops()
    target_name = crop_name.strip().lower()
    if not target_name:
        return None

    exact_match = next(
        (c for c in catalog if str(c.get("crop_name", "")).lower() == target_name),
        None,
    )
    if exact_match is not None:
        return exact_match

    return next(
        (c for c in catalog if target_name in str(c.get("crop_name", "")).lower()),
        None,
    )


def resolve_sequence_crops(
    seq_ids: list[str], crops: Optional[list[dict[str, Any]]] = None
) -> list[dict[str, Any]]:
    """
    Convert a list of crop IDs like ['C03', 'C02', 'C11'] into their full crop
    dictionaries so scoring.py can read their water demand, root depth, and yield.
    """
    catalog = crops if crops is not None else load_crops()
    resolved: list[dict[str, Any]] = []
    for cid in seq_ids:
        crop_obj = get_crop_by_id(cid, catalog)
        if crop_obj is not None:
            resolved.append(crop_obj)
    return resolved


def filter_rotations_by_constraints(
    rotations: list[list[str]],
    crops: Optional[list[dict[str, Any]]] = None,
    row_crop_only: bool = False,
    max_water_demand_mm: Optional[float] = None,
    excluded_crop_ids: Optional[set[str]] = None,
) -> list[list[str]]:
    """
    Filter out candidate rotations that do not fit a farmer's equipment or water
    budget. Setting row_crop_only=True removes perennial forage hay, orchard,
    vineyard, berry, and maple crops so only annual field and vegetable crops remain.
    """
    catalog = crops if crops is not None else load_crops()
    excluded = {cid.upper() for cid in (excluded_crop_ids or set())}
    if row_crop_only:
        excluded.update(NON_ROW_CROP_IDS)

    valid_sequences: list[list[str]] = []
    for seq in rotations:
        # Skip the rotation if any crop ID in the sequence is on the excluded list
        if any(cid.upper() in excluded for cid in seq):
            continue

        # If the farmer set a water cap, skip rotations containing a crop above that limit
        if max_water_demand_mm is not None:
            crop_objs = resolve_sequence_crops(seq, catalog)
            if any(float(c.get("water_demand_mm", 0.0)) > max_water_demand_mm for c in crop_objs):
                continue

        valid_sequences.append(seq)

    return valid_sequences


def generate_candidate_rotations(
    crops: Optional[list[dict[str, Any]]] = None,
    length: int = 3,
    row_crop_only: bool = True,
    max_water_demand_mm: Optional[float] = None,
    excluded_crop_ids: Optional[set[str]] = None,
) -> list[list[str]]:
    """
    Build valid N-year crop sequences from the crop catalog while skipping bad
    combinations before scoring. Skips planting the same crop or crop family
    back to back (including when the last year loops back to Year 1), requires
    at least one nitrogen-fixing legume or cover crop for soil nitrogen, requires
    at least one harvested cash crop for farm income, and caps zero-yield cover
    crops at 1 per rotation.
    """
    catalog = crops if crops is not None else load_crops()
    excluded = {cid.upper() for cid in (excluded_crop_ids or set())}
    if row_crop_only:
        excluded.update(NON_ROW_CROP_IDS)

    # Keep only crops that pass the equipment and water-demand rules
    usable_crops = [
        c
        for c in catalog
        if str(c.get("crop_id", "")).upper() not in excluded
        and (
            max_water_demand_mm is None
            or float(c.get("water_demand_mm", 0.0)) <= max_water_demand_mm
        )
    ]
    crop_ids = [str(c["crop_id"]) for c in usable_crops]
    crop_map = {str(c["crop_id"]): c for c in usable_crops}

    generated: list[list[str]] = []
    for combo in itertools.product(crop_ids, repeat=length):
        # Skip if the exact same crop appears two years in a row (including wrap-around)
        if any(combo[i] == combo[(i + 1) % length] for i in range(length)):
            continue

        # Skip if the same crop family (like two grains in a row) appears back to back
        if any(
            crop_map[combo[i]].get("crop_type")
            == crop_map[combo[(i + 1) % length]].get("crop_type")
            for i in range(length)
        ):
            continue

        c_objs = [crop_map[cid] for cid in combo]

        # Require at least one nitrogen-fixing legume or cover crop in the sequence
        if not any(
            float(c.get("nitrogen_fixation", 0.0)) >= 0.5 or c.get("crop_type") == "cover"
            for c in c_objs
        ):
            continue

        # Require at least one non-legume harvested crop so the rotation mixes functional types
        if not any(
            c.get("crop_type") in ("grain", "oilseed", "vegetable", "root_veg", "orchard", "vineyard", "berry")
            for c in c_objs
        ):
            continue

        # Allow at most one zero-yield cover crop in the rotation window
        if sum(1 for c in c_objs if float(c.get("typical_yield_t_ha", 0.0)) == 0.0) > 1:
            continue

        generated.append(list(combo))

    return generated
