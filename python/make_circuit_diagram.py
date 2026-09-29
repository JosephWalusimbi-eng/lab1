"""Draws docs/circuit_diagram.png (wiring diagram of the Lab 1 sensor node)."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

OUT = Path(__file__).resolve().parent.parent / "docs" / "circuit_diagram.png"
fig, ax = plt.subplots(figsize=(13, 8.5))
ax.set_xlim(0, 13); ax.set_ylim(0, 8.5); ax.axis("off")

def box(x, y, w, h, title, fc):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec="black", lw=1.5))
    ax.text(x + w / 2, y + h - 0.25, title, ha="center", va="top", weight="bold", fontsize=11)

def wire(pts, color, label=None):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=color, lw=2, solid_capstyle="round")
    if label:
        ax.text(pts[len(pts) // 2 - 1][0] + 0.1, pts[len(pts) // 2 - 1][1] + 0.08, label, fontsize=8, color=color)

# ESP32
box(5, 1.2, 3, 6.2, "ESP32 DevKit", "#e8f0fe")
pins_left  = {"3V3": 6.6, "GPIO4": 5.6, "GPIO34": 4.6, "GPIO27": 3.6, "GND": 2.0}
pins_right = {"GPIO2": 5.6, "GPIO25": 4.2, "GND": 2.0}
for n, y in pins_left.items():
    ax.plot(5, y, "ko"); ax.text(5.1, y, n, va="center", fontsize=9)
for n, y in pins_right.items():
    ax.plot(8, y, "ko"); ax.text(7.9, y, n, va="center", ha="right", fontsize=9)

# DHT11
box(0.4, 5.2, 2.6, 2.4, "DHT11", "#fff4d6")
for i, n in enumerate(["VCC", "DATA", "GND"]):
    ax.text(2.9, 7.0 - i * 0.55, n, ha="right", fontsize=9)
wire([(3.0, 7.0), (4.2, 7.0), (4.2, 6.6), (5, 6.6)], "red", "3V3")
wire([(3.0, 6.45), (5, 6.45), (5, 5.6)], "green", "DATA -> GPIO4")
ax.text(1.7, 5.35, "10k pull-up DATA-3V3 (bare sensor)", ha="center", fontsize=7.5)
wire([(3.0, 5.9), (3.6, 5.9), (3.6, 2.0), (5, 2.0)], "black", "GND")

# LDR divider
box(0.4, 2.6, 2.6, 1.9, "LDR divider", "#e6f7e6")
ax.text(1.7, 3.55, "3V3 - LDR - node - 1k - GND", ha="center", fontsize=8.5)
wire([(3.0, 3.2), (4.2, 3.2), (4.2, 4.6), (5, 4.6)], "orange", "node -> GPIO34")

# PIR
box(0.4, 0.2, 2.6, 1.9, "PIR HC-SR501", "#f3e6f7")
ax.text(1.7, 0.95, "VCC 5V(VIN)  OUT  GND", ha="center", fontsize=8.5)
wire([(3.0, 1.3), (4.4, 1.3), (4.4, 3.6), (5, 3.6)], "blue", "OUT -> GPIO27")

# LED
box(9.6, 5.0, 3.0, 2.2, "LED + 220 ohm", "#fde8e8")
ax.text(11.1, 5.9, "GPIO2 - 220R - LED(A)\nLED(C) - GND", ha="center", fontsize=8.5)
wire([(8, 5.6), (9.6, 5.6)], "purple", "GPIO2")

# Buzzer
box(9.6, 2.6, 3.0, 2.0, "Active buzzer", "#fdf1e0")
ax.text(11.1, 3.5, "(+) -> GPIO25\n(-) -> GND", ha="center", fontsize=8.5)
wire([(8, 4.2), (9.6, 4.2)], "brown", "GPIO25")

# LM35 reference
box(9.6, 0.4, 3.0, 1.8, "LM35 (reference)", "#e6eef7")
ax.text(11.1, 1.05, "+Vs 5V(VIN)   GND\nVout -> GPIO35", ha="center", fontsize=8.5)
ax.plot(8, 3.0, "ko"); ax.text(7.9, 3.0, "GPIO35", va="center", ha="right", fontsize=9)
wire([(8, 3.0), (8.8, 3.0), (8.8, 1.5), (9.6, 1.5)], "teal", "Vout -> GPIO35")

wire([(8, 2.0), (9.0, 2.0), (9.0, 3.0), (9.6, 3.0)], "black", "GND")
ax.text(6.5, 0.6, "All sensors share the ESP32 GND. Logic is 3.3 V: never feed 5 V into a GPIO.\n"
        "PIR OUT is 3.3 V level on the HC-SR501 (verify with a multimeter).", ha="center", fontsize=9, style="italic")
ax.set_title("Lab 1 - Multi-Sensor Edge Node: wiring diagram", fontsize=14, weight="bold")
fig.savefig(OUT, dpi=150, bbox_inches="tight")
print("wrote", OUT)
