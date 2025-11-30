# Quick Start Guide - Image Enhancement & Colorization GUI

## Installation

### Prerequisites
- Python 3.13
- pip package manager

### Setup

1. **Navigate to project directory:**
   ```powershell
   cd "c:\Users\zayya\Downloads\SEMESTER V\PCD\Project"
   ```

2. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

## Running the Application

### Launch GUI
```powershell
python gui.py
```

The Tkinter window will open with 4 tabs.

## Quick Workflow

### 1. Process a Single Image (Tab 1)
- **Load Image:** Click "Browse Image" → select any `.jpg`, `.png`, or `.bmp` file
- **Adjust Parameters:** Use sliders to customize:
  - `W` = LIP contrast power (higher = more contrast)
  - `E` = CST stretching strength
  - `k_log` = S-curve steepness
  - `smooth_sigma` = Smoothing intensity
  - `seed_ratio` = Percentage of pixels to use as color seeds (0.01-0.05 recommended)
  - `sigma` = Laplacian weight (controls color propagation)
- **Process:** Click "PROCESS IMAGE" (wait for completion)
- **Save:** Click "Save Output" → choose location
- **Preview:** Images shown side-by-side on canvas

### 2. Run Parameter Sweep (Tab 2)
- **Select Image:** Click "Browse Image" → choose test image
- **Set Ranges:** Use defaults or modify:
  - W values: `0 1 2 3 5 10` (6 combinations)
  - Seed ratios: `0.01 0.03 0.05` (3 combinations)
  - Sigma values: `3 5 10` (3 combinations)
  - Total: 54 combinations tested
- **Run:** Click "RUN PARAMETER SWEEP"
- **Wait:** Progress bar indicates processing
- **Results:** Saved to `results/param_sweep/results.csv`
- **Prompt:** After completion, will ask to save all 54 images

### 3. Analyze Results (Tab 3)
- **Load CSV:** Click "Browse CSV" → select `results.csv`
- **Generate Report:** Click "GENERATE SUMMARY"
- **View Statistics:**
  - PSNR range (min/max/mean/std/median)
  - Best parameters (highest PSNR)
  - Top 5 ranked combinations

### 4. Visualize Processing Stages (Tab 4)
- **Process Image First:** Complete Tab 1 workflow
- **View Stages:** Switch to Tab 4
- **Select Stage:**
  - Use radio buttons: Original → Enhanced → Colorized
  - Or drag slider (0=Original, 1=Enhanced, 2=Colorized)
- **Load CSV (Optional):** Click "Load CSV Results" to see best parameters

## Expected Results

### Tab 1 Output
- Original grayscale image (left canvas)
- Enhanced + colorized output (right canvas)
- Quick visual feedback on parameter effects

### Tab 2 Output
```
results/param_sweep/
  ├── results.csv
  └── images/ (54 processed variants)
```

### Tab 3 Output
```
PARAMETER SWEEP ANALYSIS SUMMARY
========================================
PSNR Statistics:
  Min:    28.45 dB
  Max:    35.67 dB
  Mean:   31.23 dB
  StdDev: 2.14 dB
  Median: 31.05 dB

BEST PARAMETERS:
  W:          3.0
  seed_ratio: 0.03
  sigma:      5.0
  PSNR:       35.67 dB
```

### Tab 4 Output
- Stage-by-stage image progression
- Image statistics (shape, data type, value range)
- Best parameters summary from CSV

## Tips & Tricks

### Faster Processing
- Reduce `seed_ratio` (0.01-0.02) for quicker colorization
- Use smaller images for testing parameters

### Better Quality
- Increase `W` for more contrast (3.0-5.0 typical)
- Fine-tune `sigma` based on desired color smoothness
  - Lower (3-5): Sharp color transitions
  - Higher (10+): Smooth, blended colors
- `seed_ratio` 0.03-0.05 provides good balance

### Batch Processing
- Use Tab 2 parameter sweep for comparison
- Export best results from CSV recommendations

## Troubleshooting

### "No image loaded" error
- Ensure image file is valid (check file extension)
- Try different image format (JPG, PNG, BMP)

### "Processing failed" error
- Check image dimensions (very large images may need downsampling)
- Verify all parameter values are reasonable
- Check available disk space for output files

### CSV not loading
- Ensure file is in correct CSV format with headers: W, seed_ratio, sigma, PSNR
- Check file path has no special characters

### Visualization tab empty
- Process an image in Tab 1 first to populate stages
- Switch back to Tab 4 after processing

## File Organization

```
Project Root/
├── gui.py                    ← Main GUI application
├── main.py                   ← CLI interface
├── enhance.py                ← Enhancement algorithms
├── colorize.py               ← Colorization solver
├── param_sweep.py            ← Batch parameter testing
├── plot_param_sweep.py       ← Visualization plotting
├── results_summary.py        ← Statistical analysis
├── utils.py                  ← Helper functions
├── requirements.txt          ← Dependencies
├── README.md                 ← Full documentation
├── GUI_IMPLEMENTATION.md     ← Technical details
│
├── datasets/
│   ├── grayscale/           ← Test images
│   ├── rgb/
│   └── color_reference/
│
├── outputs/
│   ├── enhanced_Y/          ← Processing cache
│   └── final_rgb/
│
└── results/
    └── param_sweep/         ← Sweep results
        └── results.csv
```

## Next Steps

1. **Test with Sample Image:**
   ```powershell
   # Copy a test image to project folder
   # Run GUI and process it
   ```

2. **Run Parameter Sweep:**
   - Use small image for quick 5-10 min analysis
   - Or use full dataset for comprehensive analysis

3. **Analyze Best Parameters:**
   - Load results CSV in Tab 3
   - Note best parameters
   - Re-process with those values in Tab 1

4. **Export Results:**
   - Save output from Tab 1
   - Export best combinations for presentation

---

**Questions?** Check README.md for full algorithm documentation and additional examples.
