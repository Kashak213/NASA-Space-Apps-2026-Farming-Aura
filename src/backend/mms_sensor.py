"""
Background serial reader for the Mobile Measurement Station (MMS).

Listens for live JSON telemetry from the 4 sensors on the Mobile Measurement
Station (soil moisture on A0, waterproof soil temperature on D2, air
temperature and humidity on D3, and surface rain detection on A1). If the MMS
is unplugged, get_mms_telemetry() safely reports connected=False so the rest of
the backend and frontend fall back to NASA POWER and USDA SSURGO data.
"""

from __future__ import annotations

import glob
import json
import os
import select
import threading
import time
from pathlib import Path
from typing import Any, Optional

try:
    import termios
except ImportError:
    termios = None

BASE_DIR = Path(__file__).resolve().parent
CACHE_PATH = BASE_DIR / "data" / "mms_latest.json"

# How many seconds a serial reading stays valid before we mark the MMS offline
STALE_TIMEOUT_SEC = 6.0

_lock = threading.Lock()
_reader_started = False

_mms_state: dict[str, Any] = {
    "station_name": "Mobile Measurement Station (MMS)",
    "connected": False,
    "port": None,
    "packet_count": 0,
    "last_update_ts": None,
    "status_message": "MMS offline (using satellite baseline)",
    "latest": {
        "soil_moisture_pct": None,
        "soil_moisture_raw": None,
        "soil_moisture_m3": None,
        "probe_mode": None,
        "soil_temp_c": None,
        "air_temp_c": None,
        "air_humidity_pct": None,
        "rain_intensity_pct": None,
        "rain_raw": None,
        "is_raining": False,
    },
}


def find_mms_serial_port() -> Optional[str]:
    """Scan standard USB serial device paths for the Mobile Measurement Station."""
    candidates = sorted(
        glob.glob("/dev/ttyACM*")
        + glob.glob("/dev/ttyUSB*")
        + glob.glob("/dev/cu.usbmodem*")
        + glob.glob("/dev/cu.usbserial*")
    )
    return candidates[0] if candidates else None


def _open_port_nonblocking(port_path: str) -> int:
    """Open the USB serial port at 9600 baud in raw non-blocking mode on Linux/macOS."""
    if termios is None:
        raise OSError("termios is not available on this OS")

    fd = os.open(port_path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    attrs = termios.tcgetattr(fd)
    attrs[0] = 0
    attrs[1] = 0
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attrs[3] = 0
    attrs[4] = termios.B9600
    attrs[5] = termios.B9600
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    return fd


def _pct_to_volumetric_moisture(moisture_pct: Optional[float]) -> Optional[float]:
    """
    Convert 0 to 100% capacitive moisture into volumetric root-zone soil
    moisture (m3/m3) between 0.12 (dry) and 0.48 (saturated) to match NASA SMAP
    and scoring.py units.
    """
    if moisture_pct is None:
        return None
    clamped = max(0.0, min(100.0, float(moisture_pct)))
    return round(0.12 + (clamped / 100.0) * 0.36, 3)


def _serial_worker() -> None:
    """Background loop that reads JSON lines from the MMS whenever it is plugged in."""
    fd: Optional[int] = None
    current_port: Optional[str] = None
    buf = b""

    while True:
        if fd is None:
            port_path = find_mms_serial_port()
            if not port_path:
                with _lock:
                    _mms_state["connected"] = False
                    _mms_state["port"] = None
                    _mms_state["status_message"] = "MMS offline (using satellite baseline)"
                time.sleep(2.0)
                continue

            try:
                fd = _open_port_nonblocking(port_path)
                current_port = port_path
                buf = b""
                with _lock:
                    _mms_state["port"] = current_port
                    _mms_state["status_message"] = f"MMS connected on {current_port}"
            except Exception:
                with _lock:
                    _mms_state["connected"] = False
                    _mms_state["port"] = None
                    _mms_state["status_message"] = "MMS offline (using satellite baseline)"
                time.sleep(2.0)
                continue

        try:
            if not current_port or not os.path.exists(current_port):
                raise OSError("MMS unplugged")

            r, _, _ = select.select([fd], [], [], 0.5)
            if r:
                try:
                    chunk = os.read(fd, 512)
                except BlockingIOError:
                    chunk = b""

                if chunk:
                    buf += chunk
                    while b"\n" in buf:
                        raw_line, buf = buf.split(b"\n", 1)
                        line = raw_line.decode("utf-8", errors="replace").strip()
                        if not line.startswith("{") or not line.endswith("}"):
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        if "status" in data and len(data) == 1:
                            continue

                        now_ts = time.time()
                        moist_pct = data.get("soil_moisture_pct")
                        moist_m3 = _pct_to_volumetric_moisture(moist_pct)
                        is_raining = bool(data.get("is_raining", False))
                        probe_mode = (
                            "wet"
                            if (moist_pct is not None and float(moist_pct) >= 35.0) or is_raining
                            else "dry"
                        )

                        with _lock:
                            _mms_state["connected"] = True
                            _mms_state["packet_count"] += 1
                            _mms_state["last_update_ts"] = now_ts
                            _mms_state["status_message"] = f"Live · Mobile Measurement Station ({current_port})"
                            latest = _mms_state["latest"]
                            for key in (
                                "soil_moisture_pct",
                                "soil_moisture_raw",
                                "soil_temp_c",
                                "air_temp_c",
                                "air_humidity_pct",
                                "rain_intensity_pct",
                                "rain_raw",
                            ):
                                if key in data:
                                    latest[key] = data[key]
                            latest["is_raining"] = is_raining
                            latest["soil_moisture_m3"] = moist_m3
                            latest["probe_mode"] = probe_mode

                        try:
                            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
                            CACHE_PATH.write_text(
                                json.dumps(
                                    {
                                        "timestamp": now_ts,
                                        "port": current_port,
                                        "latest": dict(_mms_state["latest"]),
                                    },
                                    indent=2,
                                ),
                                encoding="utf-8",
                            )
                        except Exception:
                            pass
                else:
                    time.sleep(0.05)
        except Exception:
            if fd is not None:
                try:
                    os.close(fd)
                except Exception:
                    pass
                fd = None
            with _lock:
                _mms_state["connected"] = False
                _mms_state["port"] = None
                _mms_state["status_message"] = "MMS offline (using satellite baseline)"
            time.sleep(1.5)


def start_mms_reader() -> None:
    """Start the background MMS serial reader thread once per process."""
    global _reader_started
    with _lock:
        if _reader_started:
            return
        _reader_started = True
    thread = threading.Thread(target=_serial_worker, daemon=True)
    thread.start()


def get_mms_telemetry(auto_start: bool = True) -> dict[str, Any]:
    """
    Return the current Mobile Measurement Station (MMS) status and sensor
    values. Automatically marks connected=False if no serial packet has arrived
    within STALE_TIMEOUT_SEC seconds.
    """
    if auto_start and not _reader_started:
        start_mms_reader()

    now_ts = time.time()
    with _lock:
        last_ts = _mms_state["last_update_ts"]
        is_fresh = bool(
            _mms_state["connected"]
            and last_ts is not None
            and (now_ts - float(last_ts)) <= STALE_TIMEOUT_SEC
        )
        return {
            "station_name": _mms_state["station_name"],
            "connected": is_fresh,
            "port": _mms_state["port"] if is_fresh else None,
            "packet_count": _mms_state["packet_count"],
            "last_update_ts": last_ts,
            "status_message": (
                _mms_state["status_message"]
                if is_fresh
                else "MMS offline (using satellite baseline)"
            ),
            "latest": dict(_mms_state["latest"]),
        }
