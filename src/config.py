import os
from pathlib import Path


# parse .env manually so we don't crash if someone forgot to pip install python-dotenv
def _load_dotenv_file(env_path: Path | None = None) -> None:
    if env_path is None:
        env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def get_secret(key_name: str, default: str | None = None) -> str | None:
    """Grab an API key from env vars, local .env, or Streamlit secrets."""
    _load_dotenv_file()

    env_val = os.environ.get(key_name)
    # ignore the placeholder string from .env.example
    if env_val and env_val != f"your_{key_name.lower()}_here":
        return env_val

    try:
        import streamlit as st

        if key_name in st.secrets:
            return str(st.secrets[key_name])
    except Exception:
        pass

    return default


def get_google_maps_api_key() -> str | None:
    """Returns Google Maps key if set, otherwise None so the UI falls back to free Leaflet tiles."""
    return get_secret("GOOGLE_MAPS_API_KEY")


def get_gemini_api_key() -> str | None:
    """Backend-only Gemini key. Never send this to the browser."""
    return get_secret("GEMINI_API_KEY")


def get_gemini_model() -> str:
    """Gemini model name, overridable with GEMINI_MODEL in .env."""
    return get_secret("GEMINI_MODEL") or "gemini-3.1-flash-lite-preview"
