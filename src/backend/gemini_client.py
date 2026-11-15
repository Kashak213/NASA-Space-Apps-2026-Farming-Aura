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
MODEL_CANDIDATES = ["gemini-flash-latest", "gemini-2.5-flash"]
_working_model = None

# same question twice gets the saved answer, which keeps us under the free tier rate limit
_answer_memory = {}

PROMPT = """You are helping a small farm in upstate New York understand a crop rotation dashboard.
Write for a farmer, in plain words, with no jargon and no markdown.
Use ONLY the numbers and names in the DATA below. Do not make up any numbers, dates or crops.

Return a JSON object with exactly these four string fields:
"why_line_1": one sentence on the main reason the recommended rotation scored well on this field. Mention one or two of its real scores.
"why_line_2": one sentence of practical advice for this rotation given the previous crop, the water limit and the MMS Mobile Measuring Station.
"temp_explanation": one or two sentences on what the summer temperature trend in the chart means for these crops.
"rain_explanation": one or two sentences on what the rainfall trend in the chart means for these crops.

Each field must be under 45 words.

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


def _read_json_text(text):
    """Gemini sometimes wraps JSON in a code fence, so cut down to the outer braces before parsing."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in the Gemini reply")
    return json.loads(text[start : end + 1])


def explain_dashboard(facts, timeout=12):
    """Send the dashboard facts to Gemini and return the four explanation strings, or None if it can't."""
    global _working_model

    api_key = get_secret("GEMINI_API_KEY")
    if not api_key:
        return None

    memory_key = json.dumps(facts, sort_keys=True)
    if memory_key in _answer_memory:
        return _answer_memory[memory_key]

    body = {
        "contents": [{"parts": [{"text": PROMPT.format(data=json.dumps(facts, indent=1))}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4},
    }

    forced_model = os.environ.get("GEMINI_MODEL") or get_secret("GEMINI_MODEL")
    if forced_model:
        models = [forced_model]
    elif _working_model:
        models = [_working_model]
    else:
        models = MODEL_CANDIDATES

    for model in models:
        try:
            reply = _post_json(GEMINI_URL.format(model=model), body, api_key, timeout)
            parts = reply["candidates"][0]["content"]["parts"]
            answer = _read_json_text("".join(p.get("text", "") for p in parts))
            wanted = ("why_line_1", "why_line_2", "temp_explanation", "rain_explanation")
            cleaned = {k: str(answer[k]).strip() for k in wanted}
            _working_model = model
            _answer_memory[memory_key] = cleaned
            return cleaned
        except urllib.error.HTTPError as err:
            # 404 means this model name doesn't exist anymore, so try the next one
            if err.code == 404:
                continue
            print(f"[gemini] request failed with HTTP {err.code}")
            return None
        except Exception as err:
            print(f"[gemini] could not get an explanation: {err}")
            return None

    print("[gemini] none of the model names worked, set GEMINI_MODEL in .env")
    return None


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
