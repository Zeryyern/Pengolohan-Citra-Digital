# plot_param_sweep.py (FINAL FIXED VERSION)
import os
import csv
import glob
import numpy as np
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_all_csv(patterns):
    rows = []
    for pattern in patterns:
        files = glob.glob(pattern)
        if not files:
            print(f"⚠ No CSV files matched pattern: {pattern}")
        for path in files:
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    rows.append({
                        "image": r["image"],
                        "W": float(r["W"]),
                        "seed_ratio": float(r["seed_ratio"]),
                        "sigma": float(r["sigma"]),
                        "PSNR": float(r["PSNR"])
                    })
    return rows


def compute_best_params_per_image(rows):
    best = {}
    for r in rows:
        img = r["image"]
        if img not in best or r["PSNR"] > best[img]["PSNR"]:
            best[img] = r
    return best


def compute_global_best(rows):
    return max(rows, key=lambda r: r["PSNR"])


def average_psnr_by_param(rows, key):
    groups = defaultdict(list)
    for r in rows:
        groups[r[key]].append(r["PSNR"])
    X = sorted(groups.keys())
    Y = [np.mean(groups[x]) for x in X]
    return X, Y


def plot_curve(x, y, xlabel, ylabel, title, save_path):
    plt.figure(figsize=(8, 5))
    plt.plot(x, y, marker="o")
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    print(f"✓ Saved plot: {save_path}")


def generate_plots(rows, outdir):
    # Plot vs W
    X, Y = average_psnr_by_param(rows, "W")
    plot_curve(X, Y, "W", "PSNR (dB)", "PSNR vs W", os.path.join(outdir, "psnr_vs_W.png"))

    # Plot vs seed ratio
    X, Y = average_psnr_by_param(rows, "seed_ratio")
    plot_curve(X, Y, "Seed Ratio", "PSNR (dB)", "PSNR vs Seed Ratio", os.path.join(outdir, "psnr_vs_seed.png"))

    # Plot vs sigma
    X, Y = average_psnr_by_param(rows, "sigma")
    plot_curve(X, Y, "Sigma", "PSNR (dB)", "PSNR vs Sigma", os.path.join(outdir, "psnr_vs_sigma.png"))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Plot sweep results for multiple images")
    parser.add_argument("--csvs", nargs="+", required=True, help="List of CSV file patterns (use quotes)")
    parser.add_argument("--output", default="results/param_sweep", help="Output directory for charts")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    rows = load_all_csv(args.csvs)

    if not rows:
        raise RuntimeError("No CSV rows found. Check your --csvs pattern!")

    # Best per image
    best_per_image = compute_best_params_per_image(rows)
    print("\n===== Best Parameters Per Image =====")
    for img, r in best_per_image.items():
        print(img, "→", r)

    # Global best
    best_global = compute_global_best(rows)
    print("\n===== Global Best Parameter Set =====")
    print(best_global)

    # Create plots
    generate_plots(rows, args.output)

    print("\nAll plots saved.")
