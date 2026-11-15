#include <OneWire.h>
#include <DallasTemperature.h>
#include <DHT.h>

// ==================== PIN DEFINITIONS ====================
#define PIN_SOIL_MOISTURE A0   // Capacitive Soil Moisture v1.2 (Analog)
#define PIN_RAIN_ANALOG   A1   // Raindrop Sensor AO / S (Analog)
#define PIN_DS18B20       2    // DS18B20 Waterproof Soil Temp Probe (1-Wire Digital)
#define PIN_DHT11         3    // DHT11 Air Temp & Humidity (Digital)
#define PIN_RAIN_DIGITAL  4    // Raindrop Sensor DO (Digital, Optional)

#define DHTTYPE DHT11

// ==================== CALIBRATION CONSTANTS ====================
// Capacitive Soil Moisture v1.2 calibrated to your sensor:
const int SOIL_AIR_RAW   = 520;  // 0% moisture (dry in air)
const int SOIL_WATER_RAW = 280;  // 100% moisture (submerged in water up to white line)

// Rain Sensor calibrated to your sensor (low ~20-60 when dry, rises to ~260+ when wet):
const int RAIN_DRY_RAW   = 60;   // 0% rain (dry pad)
const int RAIN_WET_RAW   = 270;  // 100% rain (wet pad)

OneWire oneWire(PIN_DS18B20);
DallasTemperature soilTempSensor(&oneWire);
DHT dht(PIN_DHT11, DHTTYPE);

void setup() {
  Serial.begin(9600);
  pinMode(PIN_RAIN_DIGITAL, INPUT);
  soilTempSensor.begin();
  dht.begin();
  delay(1000);
  Serial.println("{\"status\":\"Farming Aura Mobile Measurement Station (MMS) Initialized\"}");
}

void loop() {
  // 1. Read Capacitive Soil Moisture (A0)
  int rawMoisture = analogRead(PIN_SOIL_MOISTURE);
  int soilMoisturePct = map(rawMoisture, SOIL_AIR_RAW, SOIL_WATER_RAW, 0, 100);
  soilMoisturePct = constrain(soilMoisturePct, 0, 100);

  // 2. Read DS18B20 Soil Temperature (D2)
  soilTempSensor.requestTemperatures();
  float soilTempC = soilTempSensor.getTempCByIndex(0);

  // 3. Read DHT11 Air Temperature & Relative Humidity (D3)
  float airHumidityPct = dht.readHumidity();
  float airTempC       = dht.readTemperature();

  // 4. Read Raindrop Sensor (A1)
  int rawRain      = analogRead(PIN_RAIN_ANALOG);
  int rainPct      = map(rawRain, RAIN_DRY_RAW, RAIN_WET_RAW, 0, 100);
  rainPct          = constrain(rainPct, 0, 100);
  bool isRaining   = (rainPct > 15);

  // 5. Emit single-line JSON for Python / Streamlit backend
  Serial.print("{\"soil_moisture_pct\":");
  Serial.print(soilMoisturePct);
  Serial.print(",\"soil_moisture_raw\":");
  Serial.print(rawMoisture);
  Serial.print(",\"soil_temp_c\":");
  if (soilTempC == DEVICE_DISCONNECTED_C || soilTempC < -50.0) {
    Serial.print("null");
  } else {
    Serial.print(soilTempC, 2);
  }
  Serial.print(",\"air_temp_c\":");
  if (isnan(airTempC)) {
    Serial.print("null");
  } else {
    Serial.print(airTempC, 1);
  }
  Serial.print(",\"air_humidity_pct\":");
  if (isnan(airHumidityPct)) {
    Serial.print("null");
  } else {
    Serial.print(airHumidityPct, 1);
  }
  Serial.print(",\"rain_intensity_pct\":");
  Serial.print(rainPct);
  Serial.print(",\"rain_raw\":");
  Serial.print(rawRain);
  Serial.print(",\"is_raining\":");
  Serial.print(isRaining ? "true" : "false");
  Serial.println("}");

  delay(2000);
}
