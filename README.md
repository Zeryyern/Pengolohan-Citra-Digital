# Image Enhancement & Colorization Pipeline

A comprehensive image processing pipeline that combines **grayscale image enhancement** (Journal 1) with **chroma propagation-based colorization** (Journal 2).

## Features

### From Journal 1: Grayscale Enhancement
- **Contrast Stretching Transformation (CST)** — normalizes intensity range
- **Logistic S-Curve Transformation** — applies adaptive sigmoid curvature
- **Logarithmic Image Processing (LIP) Combination** — fuses CST and logistic outputs with power control
- **Adaptive Linear Stretching** — final normalization with dynamic range optimization
- **Optional Gaussian Smoothing** — reduces noise

### From Journal 2: Colorization via Chroma Propagation
- **YUV Color Space Conversion** — decomposes RGB into luminance (Y) and chroma (U, V)
- **Chrominance Seed Sampling** — extracts sparse color anchors from reference or pseudo-colors
- **Weighted Laplacian System** — propagates color based on luminance similarity:
  - Weight function: $w_{ij} = \exp\left(-\frac{(Y_i - Y_j)^2}{2\sigma^2}\right)$
- **Sparse Linear Solver** — solves Laplacian-based optimization with regularization fallback
- **RGB Reconstruction** — combines enhanced Y with estimated U, V channels

### General Processing
- **Automatic grayscale/RGB detection** — handles both input types
- **Flexible seeding strategies**:
  - Reference-guided (sample colors from reference RGB image)
  - Pseudo-color generation (synthetic colormap-based seeds)
  - Random sampling from true chroma (for parameter analysis)
- **Parameter sweep analysis** — systematically test W, seed_ratio, sigma combinations
- **Visualization & charting** — generate analysis plots from results

---

## Installation

### Requirements
- Python 3.13+
- opencv-python
- numpy
- scipy
- Pillow
- scikit-image
- matplotlib

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import cv2, numpy, scipy, PIL, skimage, matplotlib; print('All packages OK')"
```

---

## Project Structure

```
.
├── main.py                    # Main pipeline (enhancement + colorization)
├── enhance.py                 # Grayscale enhancement functions
├── colorize.py                # Colorization via chroma propagation
├── utils.py                   # I/O and color space conversions
├── param_sweep.py             # Parameter sweep for analysis
├── plot_param_sweep.py        # Visualization of sweep results
├── results_summary.py         # Generate summary statistics
├── datasets/
│   ├── grayscale/            # Input grayscale images
│   ├── rgb/                  # Input RGB images (optional)
│   └── color_reference/      # Reference images for color extraction
├── outputs/
│   ├── enhanced_Y/           # Enhanced grayscale (luminance only)
│   └── final_rgb/            # Colorized RGB outputs
├── results/
│   ├── param_sweep/          # Parameter sweep results
│   └── full_param_sweep/     # Full 3-parameter sweep results
└── README.md                  # This file
```

---

## Usage

### 1. Basic Colorization (Single Image)

Process a single grayscale image with default parameters:

```bash
python main.py --input datasets/grayscale/image4253.jpg
```

**Output:**
- `outputs/enhanced_Y/image4253.jpg` — enhanced grayscale
- `outputs/final_rgb/image4253_color.jpg` — colorized RGB

### 2. Colorization with Custom Output Path

```bash
python main.py --input datasets/grayscale/image4253.jpg --output results/my_output.jpg
```

### 3. Colorization with Reference Image

Use color information from a reference RGB image:

```bash
python main.py --input datasets/grayscale/image4253.jpg \
                --reference datasets/color_reference/ref.jpg \
                --seed_ratio 0.05
```

### 4. Tune Enhancement Parameters

Adjust LIP power (W) and logistic steepness (E):

```bash
python main.py --input datasets/grayscale/image4253.jpg \
                --W 2.0 \
                --E 0.5 \
                --seed_ratio 0.05 \
                --sigma 5.0
```

**Parameters:**
- `--W` (float, default=3.0) — LIP power (higher = more contrast enhancement)
- `--E` (float, default=0.5) — CST slope steepness
- `--k_log` (float, default=10.0) — Logistic curve steepness
- `--smooth_sigma` (float, default=0.5) — Gaussian smoothing after LIP
- `--seed_ratio` (float, default=0.05) — Fraction of pixels as color seeds [0, 1]
- `--sigma` (float, default=5.0) — Laplacian weight sensitivity (higher = more smoothing)
- `--cmap` (str, default="viridis") — Colormap for pseudo-color seeds (grayscale-only mode)

### 5. Parameter Sweep Analysis

Run comprehensive parameter analysis to find optimal settings:

```bash
python param_sweep.py --input datasets/grayscale/image4253.jpg \
                      --output results/full_param_sweep \
                      --Ws 0 1 2 3 5 10 \
                      --seeds 0.01 0.03 0.05 \
                      --sigmas 3 5 10
```

**Output:**
- `results/full_param_sweep/results.csv` — PSNR results for all 54 combinations
- When prompted, choose whether to save 54 output images per combination

**Typical workflow:**
1. Run sweep to get CSV results
2. Answer **n** to skip image generation (saves time)
3. Proceed to visualization

### 6. Visualize Parameter Sweep Results

Create charts from sweep results:

```bash
python plot_param_sweep.py --csv results/full_param_sweep/results.csv \
                           --output results/full_param_sweep
```

**Generated charts:**
- `psnr_vs_W_avg.png` — PSNR vs LIP power W
- `psnr_vs_seed_avg.png` — PSNR vs seed ratio
- `psnr_vs_sigma_avg.png` — PSNR vs sigma parameter
- `psnr_heatmap_W_seed_sigma*.png` — 2D heatmap of W vs seed_ratio

### 7. Summarize Parameter Sweep Results

Generate statistics and best-parameter recommendations:

```bash
python results_summary.py --csv results/full_param_sweep/results.csv
```

**Output:**
- Best parameters (highest PSNR)
- Mean and std PSNR by parameter
- Top 5 parameter combinations
- Summary table saved to `summary_report.txt`

---

## Algorithm Overview

### Enhancement Pipeline (Journal 1)

**Input:** Grayscale image Y ∈ [0, 255]

1. **CST (Contrast Stretching):**
   ```
   s = m + (Y - m) / (1 + exp(-E*(Y - m)/scale))
   ```
   where m = mean(Y), E = slope parameter

2. **Logistic S-Curve:**
   ```
   l = 1 / (1 + exp(-k * (Y_norm))) * 255
   ```
   where k = steepness, Y_norm = (Y - 128) / 128

3. **LIP Fusion with Power W:**
   ```
   p = ((s + l - s*l/L₀) / L₀)^W * L₀
   ```
   where L₀ = 255 (dynamic range)

4. **Adaptive Stretching:**
   ```
   n = (p - p_min) * 255 / (p_max - p_min)
   ```
   Normalized to [0, 255]

**Output:** Enhanced grayscale Y_enh ∈ [0, 255]

### Colorization Pipeline (Journal 2)

**Input:** Enhanced grayscale Y_enh, sparse chroma seeds (mask, values)

1. **Build Weighted Laplacian:**
   - For each pixel i, compute weights to 4-neighbors j:
   ```
   w_ij = exp(-(Y_enh[i] - Y_enh[j])² / (2σ²))
   ```
   - Construct system: A·x = b where x = chroma channel

2. **Solve with Regularization:**
   - Add Tikhonov regularization: (A + λI)·x = b (λ = 1e-6)
   - Use direct solver (spsolve) or fallback to least-squares (lsqr)

3. **Reconstruct RGB:**
   ```
   RGB = YUV_to_RGB(Y_enh, U_est, V_est)
   ```

**Output:** Colorized RGB image ∈ [0, 255]³

---

## Example Workflows

### Workflow 1: Quick Colorization
```bash
# Process one image with defaults
python main.py --input datasets/grayscale/my_image.jpg
```

### Workflow 2: Find Best Parameters
```bash
# Run parameter sweep
python param_sweep.py --input datasets/grayscale/my_image.jpg \
                      --output results/sweep

# Plot results
python plot_param_sweep.py --csv results/sweep/results.csv --output results/sweep

# Summarize findings
python results_summary.py --csv results/sweep/results.csv

# Use best parameters for final processing
python main.py --input datasets/grayscale/my_image.jpg \
               --W <best_W> --seed_ratio <best_seed> --sigma <best_sigma> \
               --output results/final_output.jpg
```

### Workflow 3: Batch Process Dataset
```bash
# (Hardcode DEFAULT_DATASET in main.py, then)
python main.py
# Processes all images in datasets/grayscale/ automatically
```

---

## Configuration

### Hard-coded Defaults (edit main.py)

```python
# Line ~15-17 in main.py:
DEFAULT_INPUT = None  # e.g., 'datasets/grayscale/image4253.jpg'
DEFAULT_DATASET = None  # e.g., 'datasets/grayscale'
```

Set these to auto-run without CLI arguments:
- `DEFAULT_INPUT = 'datasets/grayscale/image4253.jpg'` → process single file
- `DEFAULT_DATASET = 'datasets/grayscale'` → process all files in folder

---

## Results & Analysis

### PSNR Interpretation

- **Higher PSNR** = closer match to original = better reconstruction quality
- Typical range: 15–25 dB for lossy colorization
- Use PSNR to compare parameter sets on **validation images**

### Best Practices

1. **Parameter Sweep on Representative Image:**
   - Use a median-quality grayscale image (not too easy, not too hard)

2. **Validate on Test Set:**
   - Run final pipeline on entire dataset with best parameters

3. **Visual Inspection:**
   - Always check output images for color believability
   - High PSNR doesn't guarantee visually pleasing results

4. **Document Your Choices:**
   - Save sweep results and top-5 combinations
   - Include in final report

---

## Troubleshooting

### Issue: "RuntimeError: failed to factorize matrix"
**Solution:** Already handled with regularization + fallback solver. If still occurs, increase `--seed_ratio` (e.g., 0.1 instead of 0.05).

### Issue: Output images look washed out or wrong colors
**Solution:**
- Adjust `--W` (try 1.0 or 2.0 instead of 3.0)
- Increase `--seed_ratio` for denser color anchors
- Use a reference image with `--reference`

### Issue: Processing takes too long
**Solution:**
- Reduce image size (pre-resize input images)
- Use fewer parameters in sweep (`--Ws 1 2 3` instead of all 6)
- Skip image generation during sweep (answer **n** to prompt)

---

## Dependencies & Requirements

See `requirements.txt`:
```
opencv-python>=4.5.0
numpy>=1.21.0
scipy>=1.7.0
Pillow>=8.0.0
scikit-image>=0.18.0
matplotlib>=3.4.0
```

---

## Author & Citation

**Project:** Image Enhancement & Colorization (PCD Course)
**Algorithms:** Based on two research journals (Journal 1 & Journal 2)

---

## License

This project is for educational purposes. Modify and use freely for your coursework.

---

## Contact & Support

For issues or questions, review:
- `main.py` for pipeline orchestration
- `enhance.py` for enhancement details
- `colorize.py` for colorization details
- `utils.py` for I/O and color conversions

---

**Last Updated:** November 25, 2025
