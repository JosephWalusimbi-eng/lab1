"""Generates docs/lab_report.docx: a draft technical report. Fill every [TODO], then export to PDF."""
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches, RGBColor

ROOT = Path(__file__).resolve().parent.parent
d = Document()
d.styles["Normal"].font.name = "Calibri"
d.styles["Normal"].font.size = Pt(11)


def todo(text):
    p = d.add_paragraph()
    r = p.add_run("[TODO] " + text)
    r.font.color.rgb = RGBColor(0xC0, 0, 0)
    r.italic = True


def H(t, level=1):
    d.add_heading(t, level=level)


def P(t):
    d.add_paragraph(t)


def B(t):
    d.add_paragraph(t, style="List Bullet")


d.add_heading("Laboratory 1: Design, Implementation and Calibration of a Multi-Sensor Edge Node", 0)
P("Wireless Sensor Networks - Laboratory Report")
todo("Team members (names, student IDs), date, course code.")

H("1. Objective and Competency")
P("The objective was to build a low-cost ESP32 sensor node that acquires measurements from three sensing "
  "modalities, validates and calibrates them, performs basic processing locally (moving average, rate of change, "
  "threshold/event detection), makes a local decision, and streams a machine-readable, timestamped CSV for "
  "analysis in Python. The competency demonstrated is the end-to-end design of a reliable, reproducible edge "
  "sensing node, from hardware interfacing to data-quality-aware analysis.")

H("2. System Architecture and Hardware")
P("The node has five subsystems: (1) sensing (DHT11 temperature/humidity on GPIO4, LDR resistor divider on ADC1 "
  "GPIO34, HC-SR501 PIR on GPIO27, plus an LM35 analog temperature sensor on ADC1 GPIO35 used as the calibration reference); (2) processing (ESP32 firmware: validation, calibration, filtering, decision); "
  "(3) local indication (status LED on GPIO2, active buzzer on GPIO25); (4) communication (USB serial, 115200 baud "
  "CSV, one row per second); (5) analysis (Python/Jupyter on a PC).")
d.add_picture(str(ROOT / "docs" / "circuit_diagram.png"), width=Inches(6.2))
P("Figure 1: Wiring diagram.")
todo("Add a photo of the real prototype and state the exact ESP32 board used.")

H("3. Sensor Interfaces and Sampling Design")
B("DHT11: single-wire digital protocol; the sensor supports at most about 0.5 Hz, so it is read every 2 s and the "
  "last value is held on the other rows (column dht_fresh marks genuine reads).")
B("LDR: analog voltage divider read by the 12-bit ADC, 8x oversampled and normalised to 0..1.")
B("PIR: digital output read every cycle; ignored in the status logic for the first 30 s while it settles.")
B("Simulation (Wokwi, https://wokwi.com/projects/476511793297040385): the same firmware runs in the simulator with two changes: DHT_TYPE DHT22, because Wokwi's "
  "sensor is a DHT22 (with DHT11 decoding it returned wrong values), and calibration disabled (gain 1.0, offset 0.0) "
  "since the fitted values belong to the physical DHT11. An analog NTC sensor stands in for the LM35, so its "
  "ref_temp is not a real temperature. Wokwi's online compile was delayed at times by a busy build queue.")
B("Main loop: 1 Hz using a non-drifting millis() scheduler that is safe across timer rollover.")
P("CSV columns: timestamp,temp,humidity,light,motion,temp_cal,temp_filt,delta_temp,status,valid,dht_fresh,event. "
  "The first five match the lab guide example.")

H("4. Sensor Characterization and Data Quality")
P("Data set: one 10 minute log (17:15:37 to 17:25:36, 600 rows at 1 Hz), all rows valid (0 invalid DHT reads, "
  "0 rows flagged INVALID), 19 events, 574 NORMAL and 26 MOTION rows. Whole-run statistics (from analysis.ipynb):")
tt = d.add_table(rows=1, cols=6)
tt.style = "Table Grid"
for i, h in enumerate(["Quantity", "n", "Mean", "Min", "Max", "Std"]):
    tt.rows[0].cells[i].text = h
for r in [("Raw temperature (degC)", 300, 30.39, 30.30, 30.50, 0.057),
          ("Calibrated temperature (degC)", 300, 32.48, 32.38, 32.61, 0.065),
          ("Filtered temperature (degC)", 300, 32.48, 32.38, 32.61, 0.063),
          ("Humidity (%)", 300, 54.15, 53.50, 54.60, 0.431),
          ("Light (0-1)", 600, 1.000, 1.000, 1.000, 0.000),
          ("PIR (0/1)", 600, 0.043, 0, 1, 0.204),
          ("LM35 reference (degC)", 600, 32.22, 31.86, 32.78, 0.11)]:
    c = tt.add_row().cells
    for i, v in enumerate(r):
        c[i].text = v if isinstance(v, str) else (str(v) if isinstance(v, int) else f"{v:.3f}")
P("Table 2: Descriptive statistics of the 10 minute log (the DHT rows count only its 300 fresh readings).")
P("Baseline: in the first 5 minutes (first 300 rows) the calibrated temperature was 32.52 degC (std 0.05, range "
  "32.49-32.61), humidity 54.52 % (std 0.05, range 54.40-54.60) and the LM35 read 32.24 degC (std 0.12). The "
  "baseline was not perfectly undisturbed: the PIR triggered on 13 rows in that window (10 events, for example at "
  "17:19:52-17:20:03) because of movement in the room.")
P("LDR: with the 1 kOhm divider resistor (node to GND) the LDR output sat at the ADC full scale in this log: light = 1.0000 on all 600 "
  "rows (minimum = maximum = 1.0, std 0), including the LDR test period, so no dark / room / bright "
  "response could be measured. In an earlier short test it dipped only slightly (to about 0.94) when partly covered. The "
  "LDR circuit was left unchanged. A healthy divider with a 1 kOhm resistor would read well below full scale in room light, so the saturation points to a wiring or connection fault that should be checked. This is reported "
  "as a limitation and not as a measured response.")
P("To show the intended behaviour of the light channel, the Wokwi simulation was used (simulated, ideal "
  "photoresistor module, not measured hardware data). Changing its illumination slider changes the light value "
  "reported by the firmware: 0.9875 at 0.2 lux (dark), 0.3509 at 240 lux (room) and 0.0095 at 75858 lux (bright). "
  "In this module the output falls as the illumination rises (Figure 2).")
d.add_picture(str(ROOT / "docs" / "sim_ldr_composite.png"), width=Inches(4.6))
P("Figure 2: Wokwi simulation of the light channel: 0.2 lux (top, light = 0.9875), 240 lux (middle, 0.3509) and "
  "75858 lux (bottom, 0.0095).")
P("PIR: it produced 26 motion rows in 18 separate bursts, mostly 1-2 s long, spread across the run (for example "
  "at 17:15:46, 17:16:47 and 17:18:24, a cluster at 17:19:52-17:20:03, and 17:25:24-17:25:30). Every burst was "
  "recorded as a MOTION status with an event flag on its first row. Exact walk-in times were not logged separately, "
  "so a one-to-one match of triggers to deliberate walk-ins (repeatability) and any false triggers cannot be stated.")
P("DHT: over the 10 minutes the raw temperature stayed within 30.3-30.5 degC and humidity within 53.5-54.6 %, "
  "so the environment was stable and the sensor showed no invalid reads (0 of 300 fresh reads). The sensor is slow "
  "and coarse (0.1 degC steps, 2 s update). The raw DHT read about 2 degC below the LM35 (bias), which the calibration below corrects.")
P("Invalid-data handling was not exercised in the 10 minute log (0 invalid reads), so it was demonstrated in the "
  "Wokwi simulation by disconnecting the DHT22 data wire: every row is still printed, with NaN in the DHT fields, "
  "status INVALID and valid = 0, and the light and PIR columns keep updating (Figure 3). Invalid rows are "
  "flagged, not dropped.")
d.add_picture(str(ROOT / "simulation" / "sim_dht_disconnected_invalid.png"), width=Inches(5.0))
P("Figure 3: Wokwi simulation with the DHT22 data wire disconnected: rows are kept as INVALID with valid = 0 and NaN values.")
P("Calibration: no calibrated thermometer was available, so a second sensor, an LM35 (10 mV/degC), read by the ESP32 "
  "ADC (0 dB attenuation, factory-calibrated millivolt readout, 32x oversampling) was used as the reference and is "
  "logged in the ref_temp column. Both sensors were placed together at several temperatures; calibrate.py averages "
  "each for 60 s and fits temp_cal = gain * temp + offset by least squares. Limitation: the LM35 has a typical "
  "accuracy of about +/-0.5 degC and the ESP32 ADC adds error at low voltages, so this is a comparison with a "
  "second sensor, not a traceable reference, and the calibrated accuracy is limited to roughly +/-1 degC.")
pts = [(1, 33.43, 31.61, 0.03, 31), (2, 35.20, 33.15, 0.20, 30), (3, 35.85, 33.03, 0.16, 30),
       (4, 37.88, 34.52, 0.48, 30), (5, 39.25, 36.46, 0.19, 30), (6, 39.50, 37.05, 0.09, 30)]
t = d.add_table(rows=1, cols=6)
t.style = "Table Grid"
for i, h in enumerate(["Point", "LM35 reference (degC)", "DHT raw (degC)", "Error = raw - ref (degC)", "DHT std (degC)", "n"]):
    t.rows[0].cells[i].text = h
for n, ref, raw, sd, cnt in pts:
    c = t.add_row().cells
    for i, v in enumerate([str(n), f"{ref:.2f}", f"{raw:.2f}", f"{raw - ref:+.2f}", f"{sd:.2f}", str(cnt)]):
        c[i].text = v
P("Table 1: Calibration points (each is a 60 s average, sensors side by side).")
P("Fitted model (least squares, 6 points, R^2 = 0.957): temp_cal = 1.11587 * temp_raw - 1.42758. "
  "Before calibration the DHT read 2.55 degC low on average (MAE 2.55, RMSE 2.60). After calibration the "
  "in-sample MAE is 0.40 degC and RMSE 0.46 degC; with leave-one-out validation MAE is 0.60 degC and RMSE 0.68 degC. "
  "See figures/calibration_fit.png.")
P("Excluded point: a seventh point (LM35 36.50 degC, DHT 35.67 degC) was recorded but excluded from the fit because "
  "the temperature was still changing during its 60 s window (DHT std 1.01 degC, about 2x-30x larger than the other "
  "points), so the two sensors were not at the same, steady temperature. Including it would have given a gain of "
  "1.024 and an offset of +1.47 degC with R^2 = 0.86. It is recorded here rather than silently dropped.")
P("Validity range: the calibration points span only about 31.6 to 37.0 degC (raw DHT readings), roughly 33.4 to "
  "39.5 degC on the LM35. The calibration is therefore valid only in about that range. Outside it the calibrated "
  "value is an extrapolation of the fitted line and its error is not known, and it should not be trusted, for "
  "example at normal room temperature (about 20-25 degC) or below.")

H("5. Edge Processing and Local Decision Logic")
B("Validation: NaN check, range check (temperature -40..80 C, humidity 0..100 %), and rate-of-change plausibility "
  "(5 C between reads). Invalid readings are never dropped: the row is still emitted as NaN with status INVALID "
  "and valid=0, following the lab guidance to record unexpected behaviour.")
B("Calibration: temp_cal = gain * temp + offset.")
B("Five-sample moving average of the calibrated temperature (temp_filt).")
B("Rate of change delta_temp = temp_cal(t) - temp_cal(t-1) between fresh samples.")
B("Decision: HIGH_TEMP when temp_cal exceeds the threshold, with 0.5 C hysteresis to prevent chatter; MOTION from "
  "the PIR; combined status MOTION_AND_HIGH_TEMP; INVALID if the DHT11 fails validation. An event is the row "
  "where the status leaves NORMAL.")
B("Indicators: LED on for any active status; buzzer pulses 250 ms on / 250 ms off during HIGH_TEMP and gives one "
  "150 ms chirp on a motion-only event (non-blocking, so it does not disturb the 1 Hz sampling).")
P("Threshold: the firmware uses T_HIGH = 35.0 degC (clear at 34.5 degC), set above the room temperature so the "
  "node does not alarm continuously; the guide example uses 30.0 degC. During bench testing with a temporary "
  "threshold of 30 degC the HIGH_TEMP status, LED and pulsing buzzer were observed to work. The 10 minute log has no HIGH_TEMP rows because the calibrated temperature "
  "(about 32.5 degC) stayed below 35 degC. The threshold logic was demonstrated in the Wokwi simulation instead "
  "(Figures 4 to 7).")
d.add_picture(str(ROOT / "simulation" / "sim_hysteresis_34_8C_high_temp.png"), width=Inches(5.2))
P("Figure 4: Wokwi simulation, DHT22 set to 34.8 degC: the status is still HIGH_TEMP (LED on, buzzer active) "
  "because the hysteresis only clears it below 34.5 degC.")
d.add_picture(str(ROOT / "simulation" / "sim_normal_29_2C_filter_lag.png"), width=Inches(5.2))
P("Figure 5: Wokwi simulation after the temperature is lowered to 29.2 degC: the status returns to NORMAL, and "
  "temp_filt (27.76, then 28.62) is still catching up with temp_cal (29.20), showing the lag of the 5-sample "
  "moving average.")
d.add_picture(str(ROOT / "simulation" / "sim_pir_motion_event.png"), width=Inches(5.2))
P("Figure 6: Wokwi simulation, PIR triggered after the 30 s warm-up: the row changes to MOTION and event = 1 on "
  "its first row (351.530 s).")
d.add_picture(str(ROOT / "simulation" / "sim_motion_and_high_temp.png"), width=Inches(5.2))
P("Figure 7: Wokwi simulation with DHT22 at 43.3 degC and the PIR triggered: the status is MOTION_AND_HIGH_TEMP.")

H("6. Python Data Analysis and Visualization")
P("acquisition.ipynb logs at least 600 rows to data/raw/. analysis.ipynb computes the number and duration of "
  "observations, mean/min/max, standard deviation, number of invalid measurements and number of events, and "
  "produces the required plots.")
for fig, cap in [("01_temperature_vs_time.png", "Figure 8: Temperature vs time (raw, calibrated, LM35 reference)."),
                 ("02_humidity_vs_time.png", "Figure 9: Humidity vs time."),
                 ("03_raw_vs_filtered.png", "Figure 10: Calibrated temperature and its 5-sample moving average."),
                 ("04_light_vs_time.png", "Figure 11: LDR light vs time (saturated at 1.0 throughout)."),
                 ("05_motion_events.png", "Figure 12: PIR motion and detected events."),
                 ("calibration_fit.png", "Figure 13: Calibration fit (DHT raw vs LM35) and residual errors.")]:
    d.add_picture(str(ROOT / "figures" / fig), width=Inches(6.0))
    P(cap)

H("7. Discussion and Engineering Interpretation")
H("Engineering analysis questions", 2)
qa = [
    ("1. Major subsystems and roles",
     "Sensing (DHT11, LDR, PIR) converts physical quantities to signals; the ESP32 samples, validates, "
     "calibrates, filters and decides; the LED/buzzer give local feedback; the serial link provides the "
     "machine-readable stream; Python performs analysis and visualization."),
    ("2. Effective sampling rate of each sensor",
     "LDR and PIR: 1 Hz (main loop). DHT11: 0.5 Hz, since it is read every 2 s. Measured over the "
     "10 minute log: 1.002 Hz for the main loop (LDR and PIR) and 0.501 Hz for fresh, valid DHT readings."),
    ("3. Which sensor showed the greatest variability and why",
     "Among the sensors that responded, humidity varied most in relative terms (std 0.43 % over 54 %) followed by "
     "temperature (std 0.06-0.07 degC); the DHT also has only 0.1 degC resolution and updates every 2 s. The PIR "
     "is binary and event-driven (26 active rows, 18 bursts), so a standard deviation says little about it. The "
     "LDR showed no variability at all, because it was saturated at 1.0, which is a measurement limitation and "
     "not a property of the light."),
    ("4. Systematic error revealed by calibration",
     "The DHT read consistently lower than the LM35 reference: on average 2.55 degC low over the 31.6-37.0 degC range "
     "(a mostly negative bias). The fitted model is temp_cal = 1.11587 * temp_raw - 1.42758: the gain of about 1.12 "
     "shows a scale error (the gap widens as the temperature rises), and the offset of -1.43 degC is a constant shift. "
     "Valid only within the calibrated range (about 31.6-37.0 degC raw); outside it the result is an extrapolation."),
    ("5. Did calibration reduce MAE and RMSE, and by how much",
     "Yes. MAE fell from 2.55 to 0.40 degC (84 % reduction) and RMSE from 2.60 to 0.46 degC (82 %) in-sample. With "
     "leave-one-out validation, a fairer estimate for unseen points, MAE is 0.60 degC and RMSE 0.68 degC. These "
     "errors are relative to the LM35, which itself has an accuracy of about +/-0.5 degC."),
    ("6. Effect of filtering on noise and responsiveness",
     "The 5-sample moving average reduces sample-to-sample noise (the std of successive differences "
     "fell by 69.5 % in the log, since the DHT output moves in 0.1 degC steps) but adds lag of about (N-1)/2 samples, i.e. about "
     "4 s at the 2 s DHT11 rate, so fast changes appear later."),
    ("7. What to process locally and what to transmit",
     "Process locally: validation, calibration, filtering and threshold decisions - these are cheap and let the "
     "node act with no network. Transmit: compact summaries, status changes/events and periodic filtered "
     "values; raw data only when diagnosing a fault or when needed for model training."),
    ("8. Energy if every raw measurement were transmitted",
     "The radio dominates the energy budget: an ESP32 draws on the order of 100-250 mA while its Wi-Fi radio "
     "transmits, versus far less for sensing and computation, so transmitting every sample keeps the radio "
     "active much more of the time and shortens battery life. Sending only events and periodic summaries lets "
     "the radio sleep between transmissions. [TODO quote exact figures from the ESP32 datasheet with a citation.]"),
]
for q, a in qa:
    p = d.add_paragraph()
    p.add_run(q).bold = True
    P(a)

H("8. Limitations and Recommended Improvements")
B("The reference is an LM35 read by the ESP32 ADC, not a traceable thermometer (about +/-1 degC overall); a "
  "calibrated thermometer or ice-point/boiling-point checks would give a stronger reference.")
B("The calibration covers only about 31.6-37.0 degC (6 points, one excluded), so it is not validated at normal room "
  "temperature or outside that range; extend it with points over the whole intended operating range.")
B("Only three sensors; the DHT11 is slow (sampled every 2 s) and coarse (datasheet accuracy about +/-2 degC and +/-5 % RH, 0-50 degC range), so the calibration mainly corrects its bias.")
B("The LDR is uncalibrated and saturates near 1.0 in room light with the 1 kOhm divider used; check the wiring and use a resistor near the LDR's room-light resistance "
  "or a logarithmic mapping.")
B("The PIR needs a 30 s warm-up and has a limited, environment-dependent range.")
B("Data leaves the node only over a wired serial link with no buffering; add a local buffer and MQTT for "
  "wireless operation.")
B("Only one 10 minute log was recorded, at one room temperature (about 32 degC); no dark/bright LDR data and no "
  "walk-in timings were logged separately.")

H("9. Advanced Challenge (optional)")
P("Data-volume estimate for changing the sampling interval from 1 s to 5 s: one CSV row is about 62 bytes, so "
  "1 Hz gives 86 400 rows/day (about 5.4 MB/day) and 0.2 Hz gives 17 280 rows/day (about 1.1 MB/day), i.e. five "
  "times less data. Radio and CPU active time drop roughly in proportion, so communication energy drops by up "
  "to about five times, less the fixed sleep-current floor.")
P("The IMU, local data buffer and MQTT items of the advanced challenge were not implemented.")

H("10. Conclusion")
P("A three-modality ESP32 edge node (DHT temperature/humidity, LDR, PIR) with LM35 reference, validation, "
  "calibration, 5-sample filtering, rate of change, hysteresis threshold, event detection, LED and buzzer was built "
  "and used to log 600 valid rows at 1 Hz with a timestamped CSV and Python analysis. Calibration against the LM35 "
  "cut the DHT temperature error from 2.55 to 0.40 degC (MAE, in-sample; 0.60 degC leave-one-out) but is valid only "
  "for about 31.6-37.0 degC. The LDR saturated and could not be characterised, the PIR produced 18 motion bursts "
  "(19 events overall), and the 10 minute log contained no invalid readings. Main lessons: validation must keep "
  "invalid data visible, the reference sensor limits the achievable accuracy, and sensor ranges must be matched "
  "to the circuit (LDR divider).")

H("11. References")
for r in ['Espressif Systems, "ESP32 Series Datasheet," [TODO year, URL].',
          'Aosong Electronics, "DHT11 Humidity and Temperature Sensor Datasheet," [TODO year].',
          "HC-SR501 PIR Motion Sensor Datasheet, [TODO source/year].",
          'Adafruit Industries, "DHT sensor library," GitHub repository, [TODO URL, access date].']:
    d.add_paragraph(r, style="List Number")

H("12. Repository Link and File Structure")
todo("GitHub repository URL.")
P("lab1/ firmware/sensor_node/ (ESP32 sketch), simulation/ (Wokwi), python/ (acquisition.ipynb, analysis.ipynb, "
  "calibrate.py), data/raw and data/processed, figures/, docs/ (circuit_diagram.png, lab_report.pdf), README.md.")

d.save(ROOT / "docs" / "lab_report.docx")
print("saved")
