import os
from pathlib import Path


def _load_dotenv_file(env_path: Path | None = None) -> None:
    """Read key-value pairs from a local .env file into os.environ if not already set."""
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
    """Fetch a secret from environment variables, a local .env file, or Streamlit secrets."""
    _load_dotenv_file()

    env_val = os.environ.get(key_name)
    if env_val and env_val != f"your_{key_name.lower()}_here":
        return env_val

    # Check Streamlit secrets if the app is running inside Streamlit
    try:
        import streamlit as st

        if key_name in st.secrets:
            return str(st.secrets[key_name])
    except Exception:
        pass

    return default


def get_google_maps_api_key() -> str | None:
    """Return the Google Maps API key if configured, or None to fall back to free Leaflet tiles."""
    return get_secret("GOOGLE_MAPS_API_KEY")
