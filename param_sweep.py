# param_sweep.py
# Simple script to sweep over W and seed_ratio, saving PSNR metrics (if original RGB available)
import os
import numpy as np
from utils import load_image, save_rgb, rgb_to_yuv, yuv_to_rgb
from enhance import enhance_grayscale
from colorize import sample_seeds_from_channel, solve_channel
from utils import ensure_dirs
from utils import save_gray
from utils import load_maybe_gray
from utils import is_grayscale_array
from utils import save_rgb
from utils import load_image
from utils import save_gray
from scipy import ndimage
import math

def psnr(a, b):
    a = np.clip(a,0,255).astype(np.float64)
    b = np.clip(b,0,255).astype(np.float64)
    mse = np.mean((a-b)**2)
    if mse == 0:
        return float("inf")
    return 20 * math.log10(255.0 / math.sqrt(mse))

def sweep(input_path, outdir, Ws=[0,1,2,3,5,10], seeds=[0.01,0.03,0.05], sigmas=[3,5,10]):
    ensure_dirs([outdir])
    img = load_image(input_path)
    Y, U_true, V_true = rgb_to_yuv(img)
    results = []
    total_combos = len(Ws) * len(seeds) * len(sigmas)
    combo_count = 0
    
    print(f"Starting parameter sweep: {total_combos} combinations")
    print("=" * 60)
    
    for W in Ws:
        Y_enh = enhance_grayscale(Y, W=W)
        for s in seeds:
            umask, uvals = sample_seeds_from_channel(U_true, seed_ratio=s)
            vmask, vvals = sample_seeds_from_channel(V_true, seed_ratio=s)
            for sigma in sigmas:
                combo_count += 1
                U_est = solve_channel(Y_enh, umask, uvals, sigma=sigma)
                V_est = solve_channel(Y_enh, vmask, vvals, sigma=sigma)
                rgb_out = yuv_to_rgb(Y_enh, U_est, V_est)
                score = psnr(img, rgb_out)
                results.append((W, s, sigma, score))
                print(f"[{combo_count}/{total_combos}] W={W}, seed={s:.3f}, sigma={sigma} -> PSNR={score:.4f}")
    
    # save CSV (always)
    import csv
    csv_path = os.path.join(outdir, "results.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["W", "seed_ratio", "sigma", "PSNR"])
        for r in results:
            writer.writerow(list(r))
    print("\n" + "=" * 60)
    print(f"✓ CSV results saved to: {csv_path}")
    print(f"Sweep finished. {total_combos} combinations tested.")
    
    # Ask user if they want to save images
    print("\n" + "=" * 60)
    response = input("Do you want to save output images for each parameter combination? (y/n): ").strip().lower()
    
    if response == 'y' or response == 'yes':
        print("Generating and saving images...")
        ensure_dirs([os.path.join(outdir, "images")])
        result_idx = 0
        for W in Ws:
            Y_enh = enhance_grayscale(Y, W=W)
            for s in seeds:
                umask, uvals = sample_seeds_from_channel(U_true, seed_ratio=s)
                vmask, vvals = sample_seeds_from_channel(V_true, seed_ratio=s)
                for sigma in sigmas:
                    U_est = solve_channel(Y_enh, umask, uvals, sigma=sigma)
                    V_est = solve_channel(Y_enh, vmask, vvals, sigma=sigma)
                    rgb_out = yuv_to_rgb(Y_enh, U_est, V_est)
                    fname = f"out_W{W}_seed{s:.3f}_sigma{sigma}.png"
                    save_rgb(os.path.join(outdir, "images", fname), rgb_out)
                    result_idx += 1
                    if result_idx % 10 == 0:
                        print(f"  Saved {result_idx}/{total_combos} images...")
        print(f"✓ All {total_combos} images saved to: {os.path.join(outdir, 'images')}")
    else:
        print("Skipped image generation.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Parameter sweep for enhancement + colorization")
    parser.add_argument("--input", required=True, help="Path to input RGB image")
    parser.add_argument("--output", default="results/param_sweep", help="Output directory for results (default: results/param_sweep)")
    parser.add_argument("--Ws", type=float, nargs='+', default=[0,1,2,3,5,10], help="W values to test")
    parser.add_argument("--seeds", type=float, nargs='+', default=[0.01,0.03,0.05], help="seed_ratio values to test")
    parser.add_argument("--sigmas", type=float, nargs='+', default=[3,5,10], help="sigma values to test")
    
    args = parser.parse_args()
    sweep(args.input, args.output, Ws=args.Ws, seeds=args.seeds, sigmas=args.sigmas)
