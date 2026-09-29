"""Shared serial helpers for the Lab 1 sensor node CSV stream."""
import time
import serial  # pip install pyserial

COLUMNS = ["timestamp", "temp", "humidity", "light", "motion", "temp_cal",
           "temp_filt", "delta_temp", "status", "valid", "dht_fresh", "event", "ref_temp"]
INT_COLS = {"motion", "valid", "dht_fresh", "event"}
HEADER = ",".join(COLUMNS)


def open_port(port, baud=115200, settle_s=2.0):
    """Open the serial port. Opening usually resets the ESP32, so wait a bit."""
    ser = serial.Serial(port, baud, timeout=2)
    time.sleep(settle_s)
    ser.reset_input_buffer()
    return ser


def parse_line(line):
    """Return (row_dict, None) for a good data line, else (None, reason)."""
    if not line:
        return None, "empty"
    if line.startswith("#"):
        return None, "comment"
    if line.startswith("timestamp,"):
        return None, "header"
    parts = line.split(",")
    if len(parts) != len(COLUMNS):
        return None, "bad_field_count"
    try:
        row = {}
        for name, val in zip(COLUMNS, parts):
            if name == "status":
                row[name] = val
            elif name in INT_COLS:
                row[name] = int(val)
            else:
                row[name] = float(val)  # accepts "NaN"
        return row, None
    except ValueError:
        return None, "parse_error"


def stream_rows(ser, log_fh=None):
    """Yield parsed rows forever. Comments and malformed lines go to log_fh
    (recorded, never silently discarded)."""
    while True:
        raw = ser.readline().decode("utf-8", errors="replace").strip()
        row, reason = parse_line(raw)
        if row is not None:
            yield row
        elif log_fh is not None and reason not in ("empty", "header"):
            log_fh.write(f"[{reason}] {raw}\n")
            log_fh.flush()
