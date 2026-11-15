# Team API & `.env` Setup Guide (For Teammates & AI Coding Assistants)

> **Instructions for Teammate AI Assistants (Claude Code, Cursor, Cline, Antigravity, Copilot):**  
> Read this file and set up the local `.env` file in the repository root so both the **Google Maps JavaScript API** (satellite farm outline and field sector selector) and the **Google Gemini Flash-Lite API** (crop rotation explanations) work locally and on Hugging Face Spaces without ever leaking keys to GitHub.

---

## 1. Create Your Local `.env` File in the Repo Root

1. Check if `.env` already exists in the project root directory (next to `.env.example` and `requirements.txt`).
2. If `.env` does not exist yet, copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Ensure `.env` contains these exact 3 variables (paste the real keys sent in our team chat in place of the placeholders):
   ```env
   # Paste your real keys below (never commit .env to GitHub)
   GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-3.1-flash-lite-preview
   ```
4. Verify that `.env` is ignored by Git before making any commits:
   ```bash
   git status --short
   ```
   `.env` must **never** appear in `git status` or be staged with `git add -f`.

---

## 2. How the Codebase Reads `.env` (Python & Frontend)

Our helper module `src/config.py` automatically loads `.env` locally (and reads `os.environ` in Hugging Face Spaces) with zero extra setup:

- **`get_google_maps_api_key()`** in `src/config.py`:
  - Returns `GOOGLE_MAPS_API_KEY` (or `None` if still set to `your_google_maps_api_key_here`).
  - Exposed to the frontend via `GET /config` (`{"google_maps_api_key": ..., "has_google_maps_key": ...}`) in `src/backend/main.py` so the browser can load the interactive Google Maps Satellite (`hybrid`) view.
  - This key is locked in Google Cloud Console with HTTP Website Referrer restrictions (`http://localhost/*`, `http://127.0.0.1/*`, `https://*.hf.space/*`, and `https://huggingface.co/*`) and restricted only to `Maps JavaScript API`, `Geocoding API`, and `Places API (New)`.
- **`get_gemini_api_key()`** and **`get_gemini_model()`** in `src/config.py`:
  - Returns `GEMINI_API_KEY` (or `None` if unconfigured) and the target Flash-Lite model ID (`GEMINI_MODEL`, defaulting to `gemini-3.1-flash-lite-preview`, or `gemini-2.5-flash-lite` if overridden).
  - **Strict Security Rule for AI Assistants:** `GEMINI_API_KEY` is a **backend-only** secret. Never include `GEMINI_API_KEY` in the `GET /config` JSON response and never embed it in client-side HTML/JS. Always call Gemini from Python on the backend (`src/backend/main.py`) and return only the generated explanation text to the frontend. If `get_gemini_api_key()` returns `None`, automatically fall back to our built-in deterministic rotation explanations so the UI never crashes when a teammate runs offline.

---

## 3. Quick Verification Command for Teammates

After pasting the real keys into `.env`, run this one-liner from the repo root to confirm Python detects both keys:

```bash
python3 -c 'import sys; sys.path.insert(0, "src"); from config import get_google_maps_api_key, get_gemini_api_key, get_gemini_model; print("Google Maps Key Ready:", bool(get_google_maps_api_key()), "| Gemini Key Ready:", bool(get_gemini_api_key()), "| Model:", get_gemini_model())'
```

---

## 4. Hugging Face Spaces Deployment Secrets

When deploying to Hugging Face Spaces, **do not upload `.env`**. Instead, go to **Space -> Settings -> Variables and secrets -> New secret** and add:
- `GOOGLE_MAPS_API_KEY` = *(team Google Maps key)*
- `GEMINI_API_KEY` = *(team Gemini API key)*
- `GEMINI_MODEL` = `gemini-3.1-flash-lite-preview`
