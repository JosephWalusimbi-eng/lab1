"""
LDR GRAPH ANALYSIS
Wireless Sensor Networks Lab 1

Purpose:
    Read the 600-row combined sensor dataset and generate a clear graph
    of the updated LDR light readings.

Expected repository layout:
    lab1/
      data/raw/WSN_Lab1_Combined_Updated_LDR.csv
      python/ldr_graph_analysis.py
      figures/

Run from the repository root:
    python python/ldr_graph_analysis.py

The x-axis uses sample number (1 to 600), because the corrected LDR
readings were merged by row order and their timestamps do not align
with the original sensor timestamps. The light values are normalised
readings from 0 to 1, not lux.
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# Find the repository folder from this script's location.
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
CSV_FILE = Path(__file__).resolve().parent / "WSN_Lab1_Combined_Updated_LDR.csv"
FIGURES_DIR = REPOSITORY_ROOT / "figures"
OUTPUT_GRAPH = FIGURES_DIR / "04_LDR_Light_Readings_600_Samples.png"


def main():
    if not CSV_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {CSV_FILE}\\n"
            "Make sure the updated CSV is in data/raw."
        )

    data = pd.read_csv(CSV_FILE)

    if "light" not in data.columns:
        raise ValueError("The dataset does not contain a 'light' column.")

    light = pd.to_numeric(data["light"], errors="coerce").dropna()
    if light.empty:
        raise ValueError("No valid numeric LDR readings were found.")

    # Use sample number because the corrected LDR data was aligned by row order.
    sample_number = range(1, len(light) + 1)

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(12, 5.5))
    plt.plot(sample_number, light, linewidth=1.5)
    plt.title("LDR Light Readings Across 600 Samples")
    plt.xlabel("Sample Number")
    plt.ylabel("Normalised Light Reading (0–1)")
    plt.xlim(1, len(light))
    plt.ylim(0, 1.05)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_GRAPH, dpi=200, bbox_inches="tight")
    plt.close()

    print(f"Dataset rows: {len(data)}")
    print(f"Valid LDR readings: {len(light)}")
    print(f"Minimum: {light.min():.4f}")
    print(f"Maximum: {light.max():.4f}")
    print(f"Mean: {light.mean():.4f}")
    print(f"Standard deviation: {light.std():.4f}")
    print(f"Graph saved to: {OUTPUT_GRAPH}")


if __name__ == "__main__":
    main()
