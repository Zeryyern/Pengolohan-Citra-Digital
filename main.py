# main.py -- unified program that handles RGB or grayscale input
import argparse
import os
from utils import ensure_dirs, load_maybe_gray, load_image, save_rgb, save_gray, is_grayscale_array, grayscale_from_rgb, rgb_to_yuv, yuv_to_rgb
from enhance import enhance_grayscale
from colorize import (
    solve_channel,
    sample_seeds_from_channel,
    generate_seeds_from_reference,
    generate_pseudocolor_seeds_from_colormap,
    sample_seeds_from_channel
)
import numpy as np

def prepare_folders():
    ensure_dirs([
        "datasets/rgb",
        "datasets/grayscale",
        "outputs/enhanced_Y",
        "outputs/final_rgb"
    ])

def process_rgb_input(img_arr, args):
    """
    Input: img_arr HxWx3 RGB float32
    Steps:
      - convert to YUV
      - enhance Y using Journal 1
      - sample seeds from true U,V (from original RGB) and solve for full U,V
      - reconstruct RGB
    """
    Y, U_true, V_true = rgb_to_yuv(img_arr)
    # enhance Y
    Y_enh = enhance_grayscale(Y, W=args.W, E=args.E, k_log=args.k_log, smooth_sigma=args.smooth_sigma)
    # sample seeds from true U,V
    umask, uvals = sample_seeds_from_channel(U_true, seed_ratio=args.seed_ratio, rng_seed=args.rng_seed)
    vmask, vvals = sample_seeds_from_channel(V_true, seed_ratio=args.seed_ratio, rng_seed=args.rng_seed+1)
    # solve
    U_est = solve_channel(Y_enh, umask, uvals, sigma=args.sigma)
    V_est = solve_channel(Y_enh, vmask, vvals, sigma=args.sigma)
    rgb_out = yuv_to_rgb(Y_enh, U_est, V_est)
    return Y_enh, rgb_out

def process_gray_input(gray_arr, args):
    """
    Input: gray_arr HxW floats
    Steps:
      - enhance grayscale Y
      - if reference provided, use reference to sample seeds
      - otherwise, generate pseudocolor seeds using a colormap
      - solve for U,V and reconstruct RGB
    """
    Y = gray_arr
    Y_enh = enhance_grayscale(Y, W=args.W, E=args.E, k_log=args.k_log, smooth_sigma=args.smooth_sigma)

    if args.reference is not None:
        ref = load_image(args.reference)
        # check size match
        if ref.shape[0] != Y.shape[0] or ref.shape[1] != Y.shape[1]:
            raise ValueError("Reference image must have the same dimensions as input grayscale image.")
        umask, uvals, vmask, vvals = generate_seeds_from_reference(Y_enh, ref, seed_ratio=args.seed_ratio, rng_seed=args.rng_seed)
    else:
        umask, uvals, vmask, vvals = generate_pseudocolor_seeds_from_colormap(Y_enh, cmap=args.cmap, seed_ratio=args.seed_ratio, rng_seed=args.rng_seed)

    U_est = solve_channel(Y_enh, umask, uvals, sigma=args.sigma)
    V_est = solve_channel(Y_enh, vmask, vvals, sigma=args.sigma)
    rgb_out = yuv_to_rgb(Y_enh, U_est, V_est)
    return Y_enh, rgb_out


def _process_and_save(input_path, img, args):
    """Helper to process a loaded image and save outputs to outputs/ folders.
    input_path: source path (used for output filenames)
    img: loaded array from load_maybe_gray()
    """
    # determine mode
    if isinstance(img, np.ndarray) and img.ndim == 2:
        mode = "grayscale"
    else:
        if is_grayscale_array(img):
            mode = "grayscale"
            img = img[...,0]
        else:
            mode = "rgb"

    if mode == "rgb":
        Y_enh, rgb_out = process_rgb_input(img, args)
    else:
        Y_enh, rgb_out = process_gray_input(img, args)

    base = os.path.basename(input_path)
    # save enhanced Y and final RGB to outputs
    save_gray(os.path.join("outputs/enhanced_Y", base), Y_enh)
    save_rgb(os.path.join("outputs/final_rgb", base.replace(".", "_color.")), rgb_out)
    print(f"Saved outputs for {base} to outputs/ folders")
    return

def main(args):
    prepare_folders()

    # If no input provided, process all images in datasets/grayscale/
    if args.input is None:
        # batch process folder
        folder = os.path.join("datasets", "grayscale")
        if not os.path.isdir(folder):
            raise FileNotFoundError(f"Default dataset folder not found: {folder}")
        files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'))]
        if len(files) == 0:
            raise FileNotFoundError(f"No image files found in default folder: {folder}")
        for fp in files:
            print(f"Processing {fp}")
            img = load_maybe_gray(fp)
            _process_and_save(fp, img, args)
        return

    # load image (grayscale or rgb)
    img = load_maybe_gray(args.input)

    # determine mode
    if isinstance(img, np.ndarray) and img.ndim == 2:
        mode = "grayscale"
    else:
        # check if RGB but actually grayscale
        if is_grayscale_array(img):
            mode = "grayscale"
            # convert to 2D
            img = img[...,0]
        else:
            mode = "rgb"

    print(f"Detected mode: {mode}")

    if mode == "rgb":
        Y_enh, rgb_out = process_rgb_input(img, args)
        # save
        if args.output:
            save_rgb(args.output, rgb_out)
            print(f"Saved final RGB to {args.output}")
        else:
            base = os.path.basename(args.input)
            save_gray(os.path.join("outputs/enhanced_Y", base), Y_enh)
            save_rgb(os.path.join("outputs/final_rgb", base), rgb_out)
            print("Saved enhanced Y and final RGB to outputs/")

    else:
        # grayscale
        Y_enh, rgb_out = process_gray_input(img, args)
        # always save to outputs folders
        base = os.path.basename(args.input)
        save_gray(os.path.join("outputs/enhanced_Y", base), Y_enh)
        save_rgb(os.path.join("outputs/final_rgb", base.replace(".", "_color.")), rgb_out)
        print("Saved enhanced Y and final RGB to outputs/")
        # also save to --output if requested
        if args.output:
            save_rgb(args.output, rgb_out)
            print(f"Also saved final RGB to {args.output}")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Unified enhancement + colorization (Journal1+Journal2)")
    p.add_argument("--input", default=None, help="Path to input image (RGB or grayscale). If omitted, process all images in datasets/grayscale/")
    p.add_argument("--output", default=None, help="(Optional) Path to save final RGB output")
    p.add_argument("--reference", default=None, help="(Optional) Path to reference RGB for color seeds (useful for grayscale inputs)")
    p.add_argument("--W", type=float, default=3.0, help="LIP power W")
    p.add_argument("--E", type=float, default=0.5, help="CST slope E")
    p.add_argument("--k_log", type=float, default=10.0, help="Logistic curve steepness")
    p.add_argument("--smooth_sigma", type=float, default=0.5, help="Gaussian smoothing sigma after LIP")
    p.add_argument("--seed_ratio", type=float, default=0.05, help="Fraction of pixels used as seeds (0..1)")
    p.add_argument("--sigma", type=float, default=5.0, help="Sigma parameter for weight function in color propagation")
    p.add_argument("--cmap", default="viridis", help="Colormap for pseudo-color seeds when grayscale has no reference")
    p.add_argument("--rng_seed", type=int, default=0, help="Random seed for reproducibility")
    args = p.parse_args()
    main(args)
    