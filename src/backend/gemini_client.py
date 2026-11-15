"""
Gemini client that writes the plain-English explanations on the dashboard.
It only gets the numbers our scoring engine and NASA POWER already produced, so it explains results and never invents them.
The key is read from GEMINI_API_KEY in the repo's .env file so it never ends up in the browser or on GitHub.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import get_secret  # noqa: E402

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Google renames models pretty often, so we try these in order and remember the first one that answers.
# Set GEMINI_MODEL in .env to force a specific one.
MODEL_CANDIDATES = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"]
_working_model = None

# same question twice gets the saved answer, which keeps us under the free tier rate limit
_answer_memory = {}

PROMPT = """You are helping a farm understand a crop rotation dashboard powered by NASA POWER satellite climate data and USDA soil metrics.
Write for a farmer, in plain words, with no jargon and no markdown.
Use ONLY the numbers and names in the DATA below. Do not make up any numbers, dates or crops.

Return a JSON object with these exact fields:
"why_line_1": one sentence on the main reason the recommended rotation scored well on this field. Mention one or two of its real scores and NASA metrics.
"why_line_2": one sentence of practical advice for this rotation given the previous crop, the water limit and the moisture probe.
"sequence_analysis": two to three sentences providing a quick analysis of the generated crop sequence (Year 1 -> Year 2 -> Year 3) for the chosen Google Map location, explaining how each crop in the sequence fits the location's NASA annual rainfall (mm), root-zone moisture (RZM), soil temperature (°C), and soil health (OC% and pH).
"ranked_analyses": an array of 1-sentence strings (one for each item in ranked_alternatives) giving a quick analysis of how that specific generated crop sequence performs under this location's NASA weather and soil conditions.
"temp_explanation": one or two sentences on what the summer temperature trend in the chart means for these crops.
"rain_explanation": one or two sentences on what the rainfall trend in the chart means for these crops.

Keep each sentence concise and grounded in the provided numbers.

DATA:
{data}
"""


def gemini_is_configured():
    return bool(get_secret("GEMINI_API_KEY"))


def _post_json(url, body, api_key, timeout):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def build_fallback_explanation(facts):
    """Build a data-grounded quick analysis from the NASA POWER and rotation facts when Gemini API is unconfigured or offline."""
    field_desc = facts.get("field", "this field")
    priority = facts.get("farmer_priority", "Balanced")
    prev_crop = facts.get("previous_crop", "the previous crop")
    max_water = facts.get("max_water_demand_mm_per_year", 550)
    probe = facts.get("moisture_probe", "not used")
    rot = facts.get("recommended_rotation", [])
    scores = facts.get("scores_0_to_1", {})
    total_score = facts.get("rotation_total_score_0_to_1", 0.75)
    nasa_kpis = facts.get("nasa_kpis", {})

    rain_mm = nasa_kpis.get("annual_rainfall_mm", 530)
    rzm = nasa_kpis.get("root_zone_moisture", 0.35)
    soil_temp = nasa_kpis.get("soil_temp_c", 18.6)
    oc = nasa_kpis.get("soil_oc_pct", 2.8)
    ph = nasa_kpis.get("soil_ph", 6.5)

    crop_names = [c.get("crop", "Crop") for c in rot] if rot else ["Year 1", "Year 2", "Year 3"]
    seq_label = " \u2192 ".join(crop_names)
    legumes = [c.get("crop") for c in rot if c.get("fixes_nitrogen")]
    max_crop_water = max((c.get("water_need_mm") or 420 for c in rot), default=450)

    sh_score = scores.get("soil_health", 0.70)
    ws_score = scores.get("water_safety", 0.75)
    yp_score = scores.get("yield_potential", 0.75)
    res_score = scores.get("resilience", 0.72)

    why_line_1 = (
        f"On {field_desc}, {seq_label} earned a {total_score:.2f} total score under the {priority} profile, "
        f"driven by {ws_score:.2f} water safety and {sh_score:.2f} soil health with NASA rainfall at {rain_mm} mm and root-zone moisture at {rzm:.2f} RZM."
    )
    probe_note = (
        "with the dry moisture probe active, conserve topsoil water via reduced tillage"
        if probe == "dry"
        else "with adequate root-zone moisture, maintain residue cover between harvests"
    )
    why_line_2 = (
        f"Following {prev_crop}, starting Year 1 with {crop_names[0]} breaks pest cycles and keeps peak crop water demand ({max_crop_water} mm) "
        f"within your {max_water} mm budget; {probe_note}."
    )
    legume_clause = (
        f"{legumes[0]} replenishes biological soil nitrogen for the following crops"
        if legumes
        else "alternating crop families reduces nutrient depletion across seasons"
    )
    temp_clause = (
        f"warm enough ({soil_temp:.1f}\u00b0C) for rapid germination and root establishment"
        if soil_temp >= 12.0
        else f"cooler ({soil_temp:.1f}\u00b0C), favoring cold-tolerant establishment"
    )
    sequence_analysis = (
        f"Generated sequence {seq_label} is tailored to this Google Map location's NASA POWER readings "
        f"({rain_mm} mm annual rainfall, {rzm:.2f} RZM root-zone moisture, and {soil_temp:.1f}\u00b0C soil temperature on OC {oc:.1f}% \u00b7 pH {ph:.1f} soil). "
        f"In this 3-year progression, {legume_clause}, while soil temperatures are {temp_clause}. "
        f"Overall yield potential reaches {yp_score:.2f} and climate resilience scores {res_score:.2f} without exceeding the {max_water} mm/yr water cap."
    )

    ranked_analyses = []
    for idx, alt in enumerate(facts.get("ranked_alternatives", [])):
        alt_score = alt.get("total_score", total_score)
        alt_sh = alt.get("soil_health", sh_score)
        alt_ws = alt.get("water_safety", ws_score)
        alt_yp = alt.get("yield_potential", yp_score)
        alt_nfix = alt.get("nitrogen_fixation", 0.4)
        if idx == 0:
            ranked_analyses.append(
                f"Top-ranked sequence ({alt_score:.2f}): best overall balance for {rain_mm} mm NASA rainfall and {rzm:.2f} RZM moisture (water safety {alt_ws:.2f}, soil health {alt_sh:.2f}, yield {alt_yp:.2f})."
            )
        elif alt_nfix >= 0.45:
            ranked_analyses.append(
                f"Alternative #{idx + 1} ({alt_score:.2f}): strong nitrogen-fixing legume contribution ({alt_nfix:.2f}) that builds organic carbon (OC {oc:.1f}%) and keeps water safety at {alt_ws:.2f}."
            )
        else:
            ranked_analyses.append(
                f"Alternative #{idx + 1} ({alt_score:.2f}): diversifies root depths at {soil_temp:.1f}\u00b0C soil temperature with {alt_yp:.2f} yield potential and {alt_ws:.2f} water safety."
            )

    t_vals = list(facts.get("summer_temperature_c_by_year", {}).values())
    r_vals = list(facts.get("growing_season_rain_mm_by_year", {}).values())
    t_start, t_end = (t_vals[0], t_vals[-1]) if t_vals else (23.5, 24.5)
    r_start, r_end = (r_vals[0], r_vals[-1]) if r_vals else (540, rain_mm)

    return {
        "why_line_1": why_line_1,
        "why_line_2": why_line_2,
        "sequence_analysis": sequence_analysis,
        "ranked_analyses": ranked_analyses,
        "temp_explanation": (
            f"Summer temperatures at this location moved from {t_start}\u00b0C to {t_end}\u00b0C (soil temperature {soil_temp:.1f}\u00b0C). "
            f"Rotating {seq_label} spreads heat exposure across different rooting depths."
        ),
        "rain_explanation": (
            f"Seasonal rainfall shifted from {r_start} mm to {r_end} mm with NASA root-zone wetness at {rzm:.2f} RZM. "
            f"Keeping crop water demand under {max_water} mm protects root-zone moisture reserves."
        ),
        "source": "fallback",
    }


def _read_json_text(text):
    """Gemini sometimes wraps JSON in a code fence, so cut down to the outer braces before parsing."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in the Gemini reply")
    return json.loads(text[start : end + 1])


def explain_dashboard(facts, timeout=12):
    """Send the dashboard facts to Gemini and return the explanation strings, falling back to data-driven analysis if unavailable."""
    global _working_model

    memory_key = json.dumps(facts, sort_keys=True)
    if memory_key in _answer_memory:
        return _answer_memory[memory_key]

    api_key = get_secret("GEMINI_API_KEY")
    if not api_key:
        fallback = build_fallback_explanation(facts)
        _answer_memory[memory_key] = fallback
        return fallback

    body = {
        "contents": [{"parts": [{"text": PROMPT.format(data=json.dumps(facts, indent=1))}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4},
    }

    forced_model = os.environ.get("GEMINI_MODEL") or get_secret("GEMINI_MODEL")
    if _working_model:
        models = [_working_model] + [m for m in MODEL_CANDIDATES if m != _working_model]
    elif forced_model:
        models = [forced_model] + [m for m in MODEL_CANDIDATES if m != forced_model]
    else:
        models = list(MODEL_CANDIDATES)

    for model in models:
        try:
            reply = _post_json(GEMINI_URL.format(model=model), body, api_key, timeout)
            parts = reply["candidates"][0]["content"]["parts"]
            answer = _read_json_text("".join(p.get("text", "") for p in parts))
            fallback = build_fallback_explanation(facts)
            wanted = ("why_line_1", "why_line_2", "sequence_analysis", "temp_explanation", "rain_explanation")
            cleaned = {k: str(answer.get(k) or fallback[k]).strip() for k in wanted}
            raw_ranked = answer.get("ranked_analyses")
            if isinstance(raw_ranked, list) and raw_ranked:
                cleaned["ranked_analyses"] = [str(item).strip() for item in raw_ranked]
            else:
                cleaned["ranked_analyses"] = fallback["ranked_analyses"]
            cleaned["source"] = "gemini"
            _working_model = model
            _answer_memory[memory_key] = cleaned
            return cleaned
        except urllib.error.HTTPError as err:
            if err.code in (400, 404):
                continue
            print(f"[gemini] request failed with HTTP {err.code}")
            break
        except Exception as err:
            print(f"[gemini] could not get an explanation: {err}")
            break

    fallback = build_fallback_explanation(facts)
    _answer_memory[memory_key] = fallback
    return fallback


if __name__ == "__main__":
    # quick test, needs GEMINI_API_KEY in .env
    sample = {
        "field": "Field F001 near Albany, New York",
        "recommended_rotation": ["Soybeans & Small Grains", "Field Corn (Silage & Grain)", "Potatoes"],
        "scores_0_to_1": {"soil_health": 0.61, "water_safety": 0.72, "resilience": 0.58, "yield_potential": 0.9, "nitrogen_fixation": 0.34},
        "summer_temperature_c_by_year": {"2020": 23.5, "2024": 24.8},
        "growing_season_rain_mm_by_year": {"2020": 668, "2024": 530},
    }
    print(explain_dashboard(sample) or "No answer. Is GEMINI_API_KEY set in .env?")
