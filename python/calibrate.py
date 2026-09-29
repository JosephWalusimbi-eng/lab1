"""
Temperature calibration for the Lab 1 sensor node.

Step 1 - collect paired data (DHT11 vs reference):
    python calibrate.py collect --port COM3 --seconds 60
  Default reference = the LM35 wired to GPIO35 (ref_temp column of the CSV stream).
  For each point: put the LM35 right next to the DHT11, wait for both to settle,
  press Enter, and the script averages the RAW DHT11 and the LM35 over the window.
  Use >= 5 points spread over the range you can create (cool spot / room / near a
  laptop or warm hand / warm location).
  Use --manual to type a reading from an external thermometer instead.

Step 2 - fit the model and evaluate:
    python calibrate.py fit
  Fits  reference = gain * sensor + offset  (least squares), reports MAE/RMSE
  before and after (in-sample and leave-one-out), saves the model + figure.
  Copy CAL_GAIN / CAL_OFFSET into firmware/sensor_node/sensor_node.ino.
"""
import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CAL_CSV = ROOT / "data" / "raw" / "calibration_data.csv"
MODEL_JSON = ROOT / "data" / "processed" / "calibration_model.json"
FIG_PATH = ROOT / "figures" / "calibration_fit.png"
FIELDS = ["datetime", "reference_temp", "sensor_raw_mean", "sensor_raw_std", "n_samples"]


# ------------------------------------------------------------------ collect
def collect(args):
    from serial_utils import open_port, stream_rows

    CAL_CSV.parent.mkdir(parents=True, exist_ok=True)
    new_file = not CAL_CSV.exists()
    ser = open_port(args.port, args.baud)
    log = open(CAL_CSV.with_suffix(".log"), "a")
    rows = stream_rows(ser, log)

    with open(CAL_CSV, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        while True:
            if args.manual:
                ref = input("\nReference temperature in deg C (blank to finish): ").strip()
                if not ref:
                    break
                try:
                    ref = float(ref)
                except ValueError:
                    print("Not a number, try again.")
                    continue
            else:
                if input("\nPress Enter when both sensors have settled (q + Enter to finish): ").strip().lower() == "q":
                    break
                ref = None

            ser.reset_input_buffer()   # drop rows that piled up while waiting for Enter
            print(f"Averaging for {args.seconds} s ...")
            t_end = time.time() + args.seconds
            vals, refs = [], []
            while time.time() < t_end:
                r = next(rows)
                if r["valid"] == 1 and r["dht_fresh"] == 1:
                    vals.append(r["temp"])
                if not np.isnan(r["ref_temp"]):
                    refs.append(r["ref_temp"])
            if len(vals) < 3:
                print("Too few valid samples, point discarded (check the wiring).")
                continue
            if ref is None:
                if len(refs) < 3:
                    print("Too few LM35 samples, point discarded (check the LM35 wiring).")
                    continue
                ref = round(float(np.mean(refs)), 3)
            vals = np.array(vals)
            rec = {"datetime": datetime.now().isoformat(timespec="seconds"),
                   "reference_temp": ref,
                   "sensor_raw_mean": round(float(vals.mean()), 3),
                   "sensor_raw_std": round(float(vals.std(ddof=1)), 3),
                   "n_samples": len(vals)}
            writer.writerow(rec)
            fh.flush()
            print(f"  ref={ref:.2f}  sensor={rec['sensor_raw_mean']:.2f}  "
                  f"(std {rec['sensor_raw_std']:.2f}, n={len(vals)})")
    ser.close()
    print(f"Saved to {CAL_CSV}")


# ---------------------------------------------------------------------- fit
def metrics(err):
    err = np.asarray(err, float)
    return {"MAE": float(np.mean(np.abs(err))),
            "RMSE": float(np.sqrt(np.mean(err ** 2))),
            "bias": float(np.mean(err))}


def fit(args):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    from scipy import stats

    df = pd.read_csv(args.csv)
    x = df["sensor_raw_mean"].to_numpy(float)   # sensor (raw)
    y = df["reference_temp"].to_numpy(float)    # reference
    n = len(df)
    if n < 3:
        raise SystemExit("Need at least 3 calibration points (5+ recommended).")

    res = stats.linregress(x, y)
    gain, offset = float(res.slope), float(res.intercept)
    y_hat = gain * x + offset

    before = metrics(x - y)          # error of the uncalibrated sensor
    after = metrics(y_hat - y)       # error after calibration (in-sample)

    # Leave-one-out: a fairer estimate of error on unseen points
    loo_err = []
    for i in range(n):
        m = np.arange(n) != i
        if m.sum() >= 2:
            r = stats.linregress(x[m], y[m])
            loo_err.append(r.slope * x[i] + r.intercept - y[i])
    loo = metrics(loo_err) if loo_err else None

    model = {
        "equation": "temp_cal = gain * temp_raw + offset",
        "gain": gain, "offset": offset,
        "r_squared": float(res.rvalue ** 2),
        "gain_stderr": float(res.stderr),
        "n_points": n,
        "range_raw_C": [float(x.min()), float(x.max())],
        "before": before, "after_in_sample": after, "after_leave_one_out": loo,
    }
    MODEL_JSON.parent.mkdir(parents=True, exist_ok=True)
    MODEL_JSON.write_text(json.dumps(model, indent=2))

    # Figure: fit + residuals
    FIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    xs = np.linspace(x.min() - 0.5, x.max() + 0.5, 50)
    ax[0].scatter(x, y, label="calibration points")
    ax[0].plot(xs, xs, "--", color="gray", label="ideal (y = x)")
    ax[0].plot(xs, gain * xs + offset, label=f"fit: {gain:.4f}x + {offset:.3f}")
    ax[0].set(xlabel="Sensor raw temp (°C)", ylabel="Reference temp (°C)",
              title="Calibration fit")
    ax[0].legend(); ax[0].grid(alpha=.3)
    w = 0.35
    idx = np.arange(n)
    ax[1].bar(idx - w / 2, x - y, w, label="before")
    ax[1].bar(idx + w / 2, y_hat - y, w, label="after")
    ax[1].set_xticks(idx)
    ax[1].set_xticklabels(idx + 1)
    ax[1].axhline(0, color="k", lw=.8)
    ax[1].set(xlabel="Calibration point", ylabel="Error vs reference (°C)",
              title="Residual error")
    ax[1].legend(); ax[1].grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(FIG_PATH, dpi=150)

    print(f"Points: {n}   R^2 = {model['r_squared']:.4f}")
    print(f"Model : reference = {gain:.5f} * sensor + {offset:.5f}")
    print(f"Before: MAE={before['MAE']:.3f}  RMSE={before['RMSE']:.3f}  bias={before['bias']:+.3f}")
    print(f"After : MAE={after['MAE']:.3f}  RMSE={after['RMSE']:.3f}  (in-sample)")
    if loo:
        print(f"LOO   : MAE={loo['MAE']:.3f}  RMSE={loo['RMSE']:.3f}")
    print(f"Reduction: MAE {100*(1-after['MAE']/before['MAE']):.1f} %, "
          f"RMSE {100*(1-after['RMSE']/before['RMSE']):.1f} %")
    print("\nPaste into sensor_node.ino:")
    print(f"const float CAL_GAIN   = {gain:.5f}f;")
    print(f"const float CAL_OFFSET = {offset:.5f}f;")
    print(f"\nSaved {MODEL_JSON} and {FIG_PATH}")


# --------------------------------------------------------------------- main
if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect", help="log sensor vs reference pairs")
    c.add_argument("--port", required=True, help="e.g. COM3 or /dev/ttyUSB0")
    c.add_argument("--baud", type=int, default=115200)
    c.add_argument("--seconds", type=int, default=60, help="averaging window per point")
    c.add_argument("--manual", action="store_true", help="type the reference reading instead of using the LM35")
    c.set_defaults(func=collect)
    f = sub.add_parser("fit", help="fit gain/offset and report MAE/RMSE")
    f.add_argument("--csv", default=str(CAL_CSV))
    f.set_defaults(func=fit)
    a = p.parse_args()
    a.func(a)
