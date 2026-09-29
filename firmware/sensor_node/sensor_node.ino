/*
 * WSN Lab 1 - Multi-Sensor Edge Node (ESP32)
 * Sensors : DHT11 (temp/humidity, digital), LDR (analog), PIR (digital)
 * Edge    : validation, calibration, 5-sample moving average, rate of
 *           change, hysteresis threshold, event detection, LED status,
 *           buzzer (pulsing alarm while HIGH_TEMP, short chirp on motion event)
 * Output  : one CSV row per second over serial (115200 baud)
 *
 * CSV columns (first five match the lab guide example; ref_temp appended last):
 *   timestamp,temp,humidity,light,motion,
 *   temp_cal,temp_filt,delta_temp,status,valid,dht_fresh,event,ref_temp
 *
 *   timestamp  seconds since boot (3 decimals)
 *   temp       RAW DHT11 temperature (deg C)
 *   humidity   DHT11 relative humidity (%)
 *   light      LDR ADC reading normalised to 0..1
 *   motion     PIR digital output (0/1, raw)
 *   temp_cal   calibrated temperature = CAL_GAIN*temp + CAL_OFFSET
 *   temp_filt  5-sample moving average of temp_cal
 *   delta_temp temp_cal(t) - temp_cal(t-1) between fresh DHT samples
 *   status     NORMAL | MOTION | HIGH_TEMP | MOTION_AND_HIGH_TEMP | INVALID
 *   valid      1 if the DHT11 values passed all checks, else 0
 *   dht_fresh  1 if the DHT11 was read on this row, 0 if the last value is held
 *   event      1 on the row where status changes from NORMAL to non-NORMAL
 *   ref_temp   LM35 reference temperature (deg C), NaN if implausible; used only
 *              to calibrate the DHT11 (python/calibrate.py), not in the decision logic
 *
 * Lines beginning with '#' are comments and are ignored by the Python tools.
 * Invalid readings are NEVER dropped: the row is still printed (NaN + INVALID).
 *
 * Library: "DHT sensor library" by Adafruit (+ Adafruit Unified Sensor)
 */

#include <DHT.h>

// ---------------- PINS ----------------
#define DHT_PIN   4
#define DHT_TYPE  DHT11    // DHT22 if the sensor is the white 4-pin one
#define LDR_PIN   34   // ADC1 channel, input-only, safe with WiFi later
#define PIR_PIN   27
#define LED_PIN   2
#define BUZZER_PIN 25 // for high temperature alert
#define LM35_PIN  35   // ADC1 channel, input-only: LM35 reference thermometer (10 mV/degC)

// ---------------- CALIBRATION (paste values from calibrate.py) ----------------
// temp_cal = CAL_GAIN * temp_raw + CAL_OFFSET
const float CAL_GAIN   = 1.11587f;
const float CAL_OFFSET = -1.42758f;

// ---------------- TIMING ----------------
const uint32_t SAMPLE_INTERVAL_MS = 1000;  // main loop: 1 Hz
const uint32_t DHT_INTERVAL_MS    = 2000;  // DHT11 max rate ~0.5 Hz
const uint32_t PIR_WARMUP_MS      = 30000; // ignore PIR in status while it settles

// ---------------- VALIDATION LIMITS ----------------
const float TEMP_MIN = -40.0f, TEMP_MAX = 80.0f;   // wide sanity limits
const float HUM_MIN  = 0.0f,   HUM_MAX  = 100.0f;
const float MAX_TEMP_STEP = 5.0f;   // max plausible change between fresh reads (deg C)
const int   MAX_STEP_REJECTS = 3;   // after this many, accept the new level

// ---------------- DECISION THRESHOLDS ----------------
const float T_HIGH  = 35.0f;  // enter HIGH_TEMP above this
const float T_CLEAR = 34.5f;  // leave HIGH_TEMP below this (hysteresis)

// ---------------- LIGHT ----------------
const int   ADC_MAX = 4095;
const int   LDR_OVERSAMPLE = 8;

// ---------------- LM35 REFERENCE ----------------
const int   LM35_OVERSAMPLE = 32;
const float LM35_MV_PER_C   = 10.0f;   // LM35: 10 mV per deg C

// ---------------- MOVING AVERAGE ----------------
const int N_AVG = 5;
float avgBuf[N_AVG];
int   avgIdx = 0;
int   avgCount = 0;

// ---------------- STATE ----------------
DHT dht(DHT_PIN, DHT_TYPE);

uint32_t nextSample = 0;
uint32_t lastDhtMs = 0;
bool     dhtEverRead = false;

float rawT = NAN, hum = NAN, calT = NAN, filtT = NAN, prevCalT = NAN;
bool  haveAccepted = false;
bool  dhtOk = false;
int   stepRejects = 0;

bool  highTemp = false;
bool  prevActive = false;

uint32_t invalidCount = 0;

// Buzzer
const uint32_t ALARM_HALF_MS = 250;   // high-temp alarm beep half-period
const uint32_t CHIRP_MS      = 150;   // motion event chirp length
bool     buzzerAlarm = false;
uint32_t beepUntil   = 0;

// ---------------- HELPERS ----------------
bool plausible(float t, float h) {
  return !isnan(t) && !isnan(h) &&
         t >= TEMP_MIN && t <= TEMP_MAX &&
         h >= HUM_MIN && h <= HUM_MAX;
}

float pushAndAverage(float x) {
  avgBuf[avgIdx] = x;
  avgIdx = (avgIdx + 1) % N_AVG;
  if (avgCount < N_AVG) avgCount++;
  float s = 0;
  for (int i = 0; i < avgCount; i++) s += avgBuf[i];
  return s / avgCount;
}

// LM35 temperature in deg C. Attenuation 0 dB (about 0..950 mV) is the most linear ESP32
// ADC range and covers 0..~90 deg C. analogReadMilliVolts() applies the factory ADC calibration.
float readLM35() {
  long mvSum = 0;
  for (int i = 0; i < LM35_OVERSAMPLE; i++) mvSum += analogReadMilliVolts(LM35_PIN);
  float t = (mvSum / (float)LM35_OVERSAMPLE) / LM35_MV_PER_C;
  return (t >= 0.0f && t <= 100.0f) ? t : NAN;
}

void printFloat(float v, int decimals) {
  if (isnan(v)) Serial.print("NaN");
  else Serial.print(v, decimals);
}

// Non-blocking buzzer (active buzzer, driven HIGH = on):
//   HIGH_TEMP active -> repeating 250 ms on / 250 ms off alarm
//   motion-only event -> single short chirp
void updateBuzzer(uint32_t now) {
  bool on;
  if (buzzerAlarm)                          on = (now % (2 * ALARM_HALF_MS)) < ALARM_HALF_MS;
  else if ((int32_t)(beepUntil - now) > 0)  on = true;
  else                                      on = false;
  digitalWrite(BUZZER_PIN, on ? HIGH : LOW);
}

// ---------------- SETUP ----------------
void setup() {
  Serial.begin(115200);
  pinMode(LDR_PIN, INPUT);
  pinMode(PIR_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  analogReadResolution(12);
  analogSetPinAttenuation(LM35_PIN, ADC_0db);
  dht.begin();

  Serial.println("# ESP32 MULTI-SENSOR EDGE NODE - Lab 1");
  Serial.printf("# CAL_GAIN=%.5f CAL_OFFSET=%.5f\n", CAL_GAIN, CAL_OFFSET);
  Serial.println("# PIR warm-up: motion ignored in status for first 30 s");
  Serial.println("timestamp,temp,humidity,light,motion,temp_cal,temp_filt,delta_temp,status,valid,dht_fresh,event,ref_temp");

  delay(2000);                       // let the DHT11 settle
  nextSample = millis();
}

// ---------------- LOOP ----------------
void loop() {
  uint32_t now = millis();
  updateBuzzer(now);                 // runs every pass so beeps are not tied to the 1 Hz sample rate
  // Non-drifting scheduler (signed compare handles millis() rollover)
  if ((int32_t)(now - nextSample) < 0) return;
  nextSample += SAMPLE_INTERVAL_MS;

  // ---- LDR (oversampled, normalised 0..1) ----
  long adcSum = 0;
  for (int i = 0; i < LDR_OVERSAMPLE; i++) adcSum += analogRead(LDR_PIN);
  float light = (adcSum / (float)LDR_OVERSAMPLE) / ADC_MAX;

  // ---- LM35 reference ----
  float refT = readLM35();

  // ---- PIR ----
  int motion = digitalRead(PIR_PIN);

  // ---- DHT11 (read at most every 2 s) ----
  bool fresh = false;
  float deltaT = NAN;

  if (!dhtEverRead || (now - lastDhtMs) >= (DHT_INTERVAL_MS - 100)) {
    dhtEverRead = true;
    lastDhtMs = now;
    fresh = true;

    float t = dht.readTemperature();
    float h = dht.readHumidity();
    bool ok = plausible(t, h);

    // Rate-of-change plausibility check against last accepted value
    if (ok && haveAccepted && fabsf(t - rawT) > MAX_TEMP_STEP && stepRejects < MAX_STEP_REJECTS) {
      ok = false;
      stepRejects++;
    }

    if (ok) {
      stepRejects = 0;
      rawT = t;
      hum = h;
      calT = CAL_GAIN * rawT + CAL_OFFSET;
      filtT = pushAndAverage(calT);
      if (haveAccepted) deltaT = calT - prevCalT;   // first sample stays NaN
      prevCalT = calT;
      haveAccepted = true;
      dhtOk = true;
    } else {
      dhtOk = false;
      invalidCount++;
    }
  }

  // ---- LOCAL DECISION (uses calibrated temperature, with hysteresis) ----
  const char* status;
  int event = 0;
  bool pirReady = (now >= PIR_WARMUP_MS);

  if (!dhtOk) {
    status = "INVALID";
  } else {
    if (!highTemp && calT > T_HIGH) highTemp = true;
    else if (highTemp && calT < T_CLEAR) highTemp = false;

    bool mot = (motion == HIGH) && pirReady;
    if (highTemp && mot) status = "MOTION_AND_HIGH_TEMP";
    else if (highTemp)   status = "HIGH_TEMP";
    else if (mot)        status = "MOTION";
    else                 status = "NORMAL";

    bool active = (strcmp(status, "NORMAL") != 0);
    if (active && !prevActive) event = 1;          // rising edge = one event
    prevActive = active;
  }
  digitalWrite(LED_PIN, (dhtOk && prevActive) ? HIGH : LOW);
  buzzerAlarm = dhtOk && highTemp;
  if (event && !highTemp) beepUntil = millis() + CHIRP_MS;   // motion-only event: short chirp

  // ---- CSV OUTPUT (always a full 13-field row) ----
  Serial.printf("%lu.%03lu,", now / 1000, now % 1000);
  if (dhtOk) { printFloat(rawT, 2); Serial.print(","); printFloat(hum, 2); }
  else       { Serial.print("NaN,NaN"); }
  Serial.print(",");
  Serial.print(light, 4);
  Serial.print(",");
  Serial.print(motion);
  Serial.print(",");
  if (dhtOk) {
    printFloat(calT, 2);  Serial.print(",");
    printFloat(filtT, 2); Serial.print(",");
    if (fresh) printFloat(deltaT, 2); else Serial.print("NaN");
  } else {
    Serial.print("NaN,NaN,NaN");
  }
  Serial.print(",");
  Serial.print(status);
  Serial.print(",");
  Serial.print(dhtOk ? 1 : 0);
  Serial.print(",");
  Serial.print(fresh ? 1 : 0);
  Serial.print(",");
  Serial.print(event);
  Serial.print(",");
  printFloat(refT, 2);
  Serial.println();
}
