#!/usr/bin/env python3
import glob
import json
import os
import select
import termios
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8765

state_lock = threading.Lock()
telemetry_state = {
    "connected": False,
    "port": None,
    "packet_count": 0,
    "last_update_ts": None,
    "status_message": "Connecting...",
    "latest": {
        "soil_moisture_pct": None,
        "soil_moisture_raw": None,
        "soil_temp_c": None,
        "air_temp_c": None,
        "air_humidity_pct": None,
        "rain_intensity_pct": None,
        "rain_raw": None,
        "is_raining": False,
        "raw_json": "",
    },
}


def find_serial_port():
    ports = sorted(glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*"))
    return ports[0] if ports else None


def open_serial_nonblocking(port_path):
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


def serial_reader_loop():
    fd = None
    current_port = None
    buf = b""

    while True:
        if fd is None:
            port_path = find_serial_port()
            if not port_path:
                with state_lock:
                    telemetry_state["connected"] = False
                    telemetry_state["port"] = None
                    telemetry_state["status_message"] = "Waiting for /dev/ttyACM0..."
                time.sleep(1.5)
                continue
            try:
                fd = open_serial_nonblocking(port_path)
                current_port = port_path
                buf = b""
                with state_lock:
                    telemetry_state["connected"] = True
                    telemetry_state["port"] = current_port
                    telemetry_state["status_message"] = f"Connected ({current_port})"
            except Exception as exc:
                with state_lock:
                    telemetry_state["connected"] = False
                    telemetry_state["port"] = port_path
                    telemetry_state["status_message"] = f"Error: {exc}"
                time.sleep(1.5)
                continue

        try:
            if not os.path.exists(current_port):
                raise OSError("Device unplugged")
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

                        now_ts = time.time()
                        with state_lock:
                            if "status" in data and len(data) == 1:
                                telemetry_state["status_message"] = data["status"]
                                continue
                            telemetry_state["connected"] = True
                            telemetry_state["packet_count"] += 1
                            if telemetry_state["packet_count"] <= 3:
                                print(f"[Telemetry #{telemetry_state['packet_count']}] {line}", flush=True)
                            telemetry_state["last_update_ts"] = now_ts
                            telemetry_state["status_message"] = f"Connected ({current_port})"
                            for k in telemetry_state["latest"]:
                                if k in data:
                                    telemetry_state["latest"][k] = data[k]
                            telemetry_state["latest"]["raw_json"] = line
                else:
                    time.sleep(0.05)
        except Exception as exc:
            if fd is not None:
                try:
                    os.close(fd)
                except Exception:
                    pass
                fd = None
            with state_lock:
                telemetry_state["connected"] = False
                telemetry_state["status_message"] = f"Reconnecting ({exc})..."
            time.sleep(1.0)


DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Mobile Measurement Station (MMS) Readings</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 40px auto;
      max-width: 650px;
      background-color: #f9f9f9;
      color: #222;
    }
    h2 {
      margin-bottom: 5px;
    }
    .status {
      font-size: 14px;
      color: #555;
      margin-bottom: 20px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      border: 1px solid #ccc;
    }
    th, td {
      border: 1px solid #ccc;
      padding: 12px;
      text-align: left;
    }
    th {
      background-color: #eee;
    }
    .val {
      font-size: 18px;
      font-weight: bold;
    }
    pre {
      background: #eee;
      padding: 10px;
      border: 1px solid #ccc;
      overflow-x: auto;
      font-size: 13px;
    }
  </style>
</head>
<body>

  <h2>Farming Aura - Mobile Measurement Station (MMS) Demo</h2>
  <div class="status">
    Status: <span id="status">Connecting...</span> |
    Packets received: <span id="packets">0</span>
  </div>

  <table>
    <tr>
      <th>Sensor</th>
      <th>Pin</th>
      <th>Reading</th>
      <th>Raw / Details</th>
    </tr>
    <tr>
      <td>Soil Moisture</td>
      <td>A0</td>
      <td class="val" id="soil_moisture">--</td>
      <td id="soil_moisture_raw">--</td>
    </tr>
    <tr>
      <td>Soil Temperature (DS18B20)</td>
      <td>D2</td>
      <td class="val" id="soil_temp">--</td>
      <td id="soil_temp_f">--</td>
    </tr>
    <tr>
      <td>Air Temperature (DHT11)</td>
      <td>D3</td>
      <td class="val" id="air_temp">--</td>
      <td id="air_temp_f">--</td>
    </tr>
    <tr>
      <td>Air Humidity (DHT11)</td>
      <td>D3</td>
      <td class="val" id="air_hum">--</td>
      <td>Relative Humidity</td>
    </tr>
    <tr>
      <td>Rain Sensor</td>
      <td>A1</td>
      <td class="val" id="rain">--</td>
      <td id="rain_raw">--</td>
    </tr>
  </table>

  <h3>Latest Serial Output (9600 baud):</h3>
  <pre id="raw_json">Waiting for data...</pre>

  <script>
    async function updateReadings() {
      try {
        const res = await fetch('/api/telemetry');
        const data = await res.json();
        const d = data.latest;

        document.getElementById('status').textContent = data.status_message;
        document.getElementById('packets').textContent = data.packet_count;

        if (d.soil_moisture_pct !== null) {
          document.getElementById('soil_moisture').textContent = d.soil_moisture_pct + '%';
          document.getElementById('soil_moisture_raw').textContent = 'Raw: ' + d.soil_moisture_raw;
        }
        if (d.soil_temp_c !== null) {
          document.getElementById('soil_temp').textContent = d.soil_temp_c.toFixed(1) + ' °C';
          document.getElementById('soil_temp_f').textContent = ((d.soil_temp_c * 9/5) + 32).toFixed(1) + ' °F';
        }
        if (d.air_temp_c !== null) {
          document.getElementById('air_temp').textContent = d.air_temp_c.toFixed(1) + ' °C';
          document.getElementById('air_temp_f').textContent = ((d.air_temp_c * 9/5) + 32).toFixed(1) + ' °F';
        }
        if (d.air_humidity_pct !== null) {
          document.getElementById('air_hum').textContent = d.air_humidity_pct.toFixed(0) + '%';
        }
        if (d.rain_intensity_pct !== null) {
          const rainState = d.is_raining ? 'Raining' : 'Dry';
          document.getElementById('rain').textContent = rainState + ' (' + d.rain_intensity_pct + '%)';
          document.getElementById('rain_raw').textContent = 'Raw: ' + d.rain_raw;
        }
        if (d.raw_json) {
          document.getElementById('raw_json').textContent = d.raw_json;
        }
      } catch (err) {
        console.error(err);
      }
    }

    setInterval(updateReadings, 1000);
    updateReadings();
  </script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path.startswith("/api/telemetry"):
            with state_lock:
                payload = json.dumps(telemetry_state).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            body = DASHBOARD_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


if __name__ == "__main__":
    reader_thread = threading.Thread(target=serial_reader_loop, daemon=True)
    reader_thread.start()
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer((HOST, PORT), DashboardHandler)
    print(f"Farming Aura Live Weather Box Dashboard running at http://{HOST}:{PORT}", flush=True)
    server.serve_forever()
