# WSN Lab 1 - Multi-Sensor Edge Node (ESP32)

Low-cost sensing node: DHT11 (temperature/humidity), LDR (light), PIR (motion).
The ESP32 validates, calibrates and filters the data locally, makes a simple status decision,
and streams a timestamped CSV over serial for analysis in Python.

Repository: https://github.com/JosephWalusimbi-eng/lab1

## Repository structure
```
lab1/
├── firmware/sensor_node/sensor_node.ino   ESP32 firmware
├── simulation/                            Wokwi project (diagram.json, libraries.txt, wokwi.toml)
├── python/
│   ├── serial_utils.py                    shared serial/CSV parsing
│   ├── acquisition.ipynb                  logs >= 600 rows to data/raw/
│   ├── calibrate.py                       collect + fit temperature calibration
│   ├── analysis.ipynb                     statistics + plots + processed data
│   └── requirements.txt
├── data/raw/  data/processed/             raw logs, calibration data, processed outputs, fitted model
├── figures/                               generated plots
├── docs/                                  circuit_diagram.png, lab_report.docx -> export lab_report.pdf
└── README.md
```

## Wiring (ESP32 DevKit, 3.3 V logic)
| Sensor | Sensor pin | ESP32 |
|---|---|---|
| DHT11 | VCC / DATA / GND | 3V3 / GPIO4 / GND (10 kΩ pull-up DATA→3V3 if bare sensor) |
| LDR divider | LDR between 3V3 and node, 1 kΩ node→GND, node → | GPIO34 (ADC1) |
| PIR (HC-SR501) | VCC / OUT / GND | 5V (VIN) / GPIO27 / GND. OUT is 3.3 V level on HC-SR501; verify with a multimeter first |
| LED + 220 Ω | anode via resistor / cathode | GPIO2 / GND |
| LM35 (reference) | +Vs / Vout / GND | 5V (VIN) / GPIO35 (ADC1, 10 mV/°C) / GND. Vout stays below 1 V so it is safe for the 3.3 V ADC |
| Active buzzer | + / − | GPIO25 / GND (driven HIGH = on; a passive buzzer would need `tone()`) |

Power off before rewiring. Never feed a 5 V signal into a GPIO.

## Setup
1. Arduino IDE -> install ESP32 board package. Libraries: **DHT sensor library** and **Adafruit Unified Sensor**.
2. Open `firmware/sensor_node/sensor_node.ino`, select your ESP32 board and port, upload.
3. Serial Monitor at 115200 baud: you should see `#` comment lines, the CSV header, then one row per second.
4. `cd python && pip install -r requirements.txt`, then close the Serial Monitor before using Python.

## Reproduce the results
1. **Baseline + characterization:** run `python/acquisition.ipynb` (set `PORT`). It saves >= 600 rows to `data/raw/sensor_log_<time>.csv`.
   Keep 5+ minutes stable, then do the controlled changes (LDR dark/room/bright, PIR walk-in, DHT11 in different locations). Note the times.
2. **Calibrate temperature:**
   ```
   cd python
   python calibrate.py collect --port COM3 --seconds 60   # LM35 is the reference; press Enter per point, 5+ points
   # (use --manual to type a reading from an external thermometer instead)
   python calibrate.py fit
   ```
   Copy the printed `CAL_GAIN` / `CAL_OFFSET` into the firmware, re-upload, and log again.
   Output: `data/raw/calibration_data.csv`, `data/processed/calibration_model.json`, `figures/calibration_fit.png`.
3. **Analyse:** run `python/analysis.ipynb`. Outputs go to `data/processed/` and `figures/`.

## CSV format
`timestamp,temp,humidity,light,motion,temp_cal,temp_filt,delta_temp,status,valid,dht_fresh,event,ref_temp`

| Column | Meaning |
|---|---|
| timestamp | seconds since boot |
| temp | raw DHT11 temperature (°C) |
| humidity | relative humidity (%) |
| light | LDR ADC / 4095 (0-1) |
| motion | PIR output (0/1) |
| temp_cal | `CAL_GAIN * temp + CAL_OFFSET` |
| temp_filt | 5-sample moving average of `temp_cal` |
| delta_temp | `temp_cal(t) - temp_cal(t-1)` between fresh DHT reads |
| status | NORMAL, MOTION, HIGH_TEMP, MOTION_AND_HIGH_TEMP, INVALID |
| valid | 1 if DHT11 passed validation |
| dht_fresh | 1 if DHT11 was actually read this row (it runs at 0.5 Hz, other rows hold the last value) |
| event | 1 on the row where status leaves NORMAL |
| ref_temp | LM35 reference temperature (°C, NaN if implausible); used only for calibration |

## Edge processing implemented
- Validation: NaN, range (temp -40..80 °C, RH 0..100 %), rate-of-change limit (5 °C between reads). Invalid rows are kept and flagged, never deleted.
- Calibration (linear gain/offset), 5-sample moving average, rate of change.
- Decision: HIGH_TEMP above `T_HIGH` on calibrated temperature with 0.5 °C hysteresis (`T_HIGH` is 35.0 °C in the firmware for lab-room testing; the guide's example uses 30.0 °C, so set it to whichever value you demonstrate); PIR ignored for the first 30 s (warm-up).
- LED on for any non-NORMAL, non-INVALID status.
- Buzzer (non-blocking): pulsing 250 ms on / 250 ms off while HIGH_TEMP is active; one 150 ms chirp on a motion-only event.

## Simulation
Live project: https://wokwi.com/projects/476511793297040385
Wokwi: create an ESP32 project, paste `simulation/diagram.json` and `libraries.txt`, and the `.ino` as `sketch.ino`.
The Wokwi diagram uses a DHT22 part; the real prototype and the firmware use a DHT11 (`DHT_TYPE DHT11` in the sketch), same pin and library. Part/pin names are from memory and untested in Wokwi: if a connection is flagged, re-attach it in the editor.
In Wokwi, set `#define DHT_TYPE DHT22` in the pasted `sketch.ino` (the simulated part is a DHT22; DHT11 decoding would give NaN). The NTC sensor on GPIO35 stands in for the LM35: its voltage is not 10 mV/°C, so the simulated `ref_temp` is not a real temperature.
The Wokwi buzzer only sounds with `tone()`; with `digitalWrite` it may stay silent in the simulator (the real active buzzer works). Check the LED/serial output there instead.

## Known limitations
- The reference is an LM35 read by the ESP32 ADC, not a traceable thermometer: LM35 accuracy is about ±0.5 °C and the ESP32 ADC adds error at these low voltages, so calibrated accuracy is limited to roughly ±1 °C.
- The LDR saturates (reads ~1.0) in room light with the 1 kΩ divider resistor used in the recorded log and was left unchanged; it only responds when strongly shaded.
- The DHT11 has ~0.5 Hz maximum rate, so `temp`/`humidity` are held on alternate rows (`dht_fresh = 0`).

## Circuit diagram
`docs/circuit_diagram.png` is generated by `python/make_circuit_diagram.py`.
