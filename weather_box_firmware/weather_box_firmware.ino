#include <OneWire.h>
#include <DallasTemperature.h>
#include <DHT.h>

// Sensor pin wiring on the Mobile Measurement Station (MMS)
#define PIN_SOIL_MOISTURE A0   // Capacitive soil moisture probe v1.2 (analog)
#define PIN_RAIN_ANALOG   A1   // Raindrop sensor pad AO / S (analog)
#define PIN_DS18B20       2    // DS18B20 waterproof soil temperature probe (1-Wire digital)
#define PIN_DHT11         3    // DHT11 air temperature and humidity sensor (digital)
#define PIN_RAIN_DIGITAL  4    // Raindrop sensor DO pin (digital, optional)

#define DHTTYPE DHT11

// Raw analog calibration values measured with our sensors
// Capacitive soil moisture probe v1.2 readings in dry air vs water
const int SOIL_AIR_RAW   = 520;  // 0% moisture when dry in air
const int SOIL_WATER_RAW = 280;  // 100% moisture when dipped in water up to the white line

// Rain sensor pad readings (stays around 20-60 when dry and rises past 260 when wet)
const int RAIN_DRY_RAW   = 60;   // 0% rain on a dry pad
const int RAIN_WET_RAW   = 270;  // 100% rain on a wet pad

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
  // Read capacitive soil moisture on A0 and scale it from 0 to 100%
  int rawMoisture = analogRead(PIN_SOIL_MOISTURE);
  int soilMoisturePct = map(rawMoisture, SOIL_AIR_RAW, SOIL_WATER_RAW, 0, 100);
  soilMoisturePct = constrain(soilMoisturePct, 0, 100);

  // Read DS18B20 waterproof soil temperature probe on D2
  soilTempSensor.requestTemperatures();
  float soilTempC = soilTempSensor.getTempCByIndex(0);

  // Read DHT11 air temperature and relative humidity on D3
  float airHumidityPct = dht.readHumidity();
  float airTempC       = dht.readTemperature();

  // Read raindrop pad on A1 and flag rain when wet percentage passes 15%
  int rawRain      = analogRead(PIN_RAIN_ANALOG);
  int rainPct      = map(rawRain, RAIN_DRY_RAW, RAIN_WET_RAW, 0, 100);
  rainPct          = constrain(rainPct, 0, 100);
  bool isRaining   = (rainPct > 15);

  // Print one JSON line over USB serial every 2 seconds for the Python backend
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
