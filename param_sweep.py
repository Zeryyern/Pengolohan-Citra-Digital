# param_sweep.py (updated for multiple images)
import os
import numpy as np
import math
import csv
from utils import (
    ensure_dirs, load_image, rgb_to_yuv, yuv_to_rgb,
    save_rgb
)
from enhance import enhance_grayscale
from colorize import sample_seeds_from_channel, solve_channel


def psnr(a, b):
    a = np.clip(a, 0, 255).astype(np.float64)
    b = np.clip(b, 0, 255).astype(np.float64)
    mse = np.mean((a - b) ** 2)
    if mse == 0:
        return float("inf")
    return 20 * math.log10(255.0 / math.sqrt(mse))


def sweep_one_image(input_path, outdir, Ws, seeds, sigmas):
    ensure_dirs([outdir])
    
    # Load image
    img = load_image(input_path)
    Y, U_true, V_true = rgb_to_yuv(img)
    
    image_name = os.path.splitext(os.path.basename(input_path))[0]
    results = []

    total_combos = len(Ws) * len(seeds) * len(sigmas)
    print(f"\nProcessing image: {image_name}")
    print(f"Total combinations: {total_combos}")
    print("=" * 60)

    combo = 0
    for W in Ws:
        Y_enh = enhance_grayscale(Y, W=W)

        for s in seeds:
            umask, uvals = sample_seeds_from_channel(U_true, seed_ratio=s)
            vmask, vvals = sample_seeds_from_channel(V_true, seed_ratio=s)

            for sigma in sigmas:
                combo += 1

                U_est = solve_channel(Y_enh, umask, uvals, sigma=sigma)
                V_est = solve_channel(Y_enh, vmask, vvals, sigma=sigma)

                rgb_out = yuv_to_rgb(Y_enh, U_est, V_est)
                score = psnr(img, rgb_out)

                print(f"[{combo}/{total_combos}] W={W}, seed={s}, sigma={sigma} → PSNR={score:.4f}")

                results.append([image_name, W, s, sigma, score])

    # Save CSV for this image
    csv_path = os.path.join(outdir, f"{image_name}_results.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["image", "W", "seed_ratio", "sigma", "PSNR"])
        writer.writerows(results)

    print(f"✓ Saved CSV: {csv_path}")
    return csv_path



def sweep(images, outdir, Ws=[0, 1, 2, 3, 5, 10], seeds=[0.01, 0.03, 0.05], sigmas=[3, 5, 10]):
    ensure_dirs([outdir])
    
    all_csv_paths = []
    for img_path in images:
        csv_path = sweep_one_image(img_path, outdir, Ws, seeds, sigmas)
        all_csv_paths.append(csv_path)

    print("\n========================================")
    print("✓ All per-image sweeps complete!")
    print("CSV files:")
    for p in all_csv_paths:
        print(" -", p)
    print("========================================\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Parameter sweep for multiple RGB images")
    parser.add_argument("--inputs", nargs="+", required=True, help="Paths to input RGB images")
    parser.add_argument("--output", default="results/param_sweep", help="Directory to save results")
    parser.add_argument("--Ws", type=float, nargs="+", default=[0,1,2,3,5,10])
    parser.add_argument("--seeds", type=float, nargs="+", default=[0.01,0.03,0.05])
    parser.add_argument("--sigmas", type=float, nargs="+", default=[3,5,10])

    args = parser.parse_args()
    sweep(args.inputs, args.output, Ws=args.Ws, seeds=args.seeds, sigmas=args.sigmas)
