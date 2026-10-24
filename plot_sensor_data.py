#!/usr/bin/env python3
import argparse
import csv
import os
import matplotlib.pyplot as plt


def plot_csv(csv_path: str, output_path: str = None) -> str:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Input file not found: {csv_path}")

    times = []
    distances = []
    valids = []

    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            times.append(float(row["t"]))
            distances.append(float(row["distance_m"]))
            v_raw = str(row["valid"]).strip().lower()
            valids.append(1 if v_raw in ("true", "1", "yes", "t") else 0)

    if not times:
        raise ValueError(f"No data points found in {csv_path}")

    fig, ax1 = plt.subplots(figsize=(10, 6))

    color_dist = "#1f77b4"
    ax1.set_xlabel("Time (t / s)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Distance (m)", color=color_dist, fontsize=11, fontweight="bold")
    line1 = ax1.plot(times, distances, color=color_dist, linewidth=2, label="Distance (m)")
    ax1.tick_params(axis="y", labelcolor=color_dist)
    ax1.grid(True, linestyle="--", alpha=0.6)

    color_valid = "#2ca02c"
    ax2 = ax1.twinx()
    ax2.set_ylabel("Valid (1 / 0)", color=color_valid, fontsize=11, fontweight="bold")
    line2 = ax2.step(times, valids, where="post", color=color_valid, linestyle=":", linewidth=1.5, label="Valid")
    ax2.set_ylim(-0.1, 1.1)
    ax2.set_yticks([0, 1])
    ax2.set_yticklabels(["False (0)", "True (1)"])
    ax2.tick_params(axis="y", labelcolor=color_valid)

    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper right")

    base_name = os.path.basename(csv_path)
    plt.title(f"Sensor Data Plot — {base_name}", fontsize=13, fontweight="bold")

    if output_path is None:
        base, _ = os.path.splitext(csv_path)
        output_path = f"{base}.png"

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Graphic visualization tool for sensor CSV data (t, distance_m, valid)")
    parser.add_argument("csv_file", help="Path to input CSV file (e.g. data/sensor.csv)")
    parser.add_argument("-o", "--output", default=None, help="Output image file path (defaults to <csv_basename>.png)")
    args = parser.parse_args()

    out_file = plot_csv(args.csv_file, args.output)
    print(f"Plot saved to: {out_file}")


if __name__ == "__main__":
    main()
