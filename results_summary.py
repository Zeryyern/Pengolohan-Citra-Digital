import csv
import os
import numpy as np
from pathlib import Path
import argparse

def generate_summary(csv_path, output_dir=None):
    """
    Generate summary statistics from parameter sweep results CSV.
    
    Args:
        csv_path: Path to results.csv from param_sweep.py
        output_dir: Directory to save summary report (default: same as CSV)
    """
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    
    if output_dir is None:
        output_dir = os.path.dirname(csv_path)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Read CSV
    rows = []
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                'W': float(row['W']),
                'seed_ratio': float(row['seed_ratio']),
                'sigma': float(row['sigma']),
                'PSNR': float(row['PSNR'])
            })
    
    if len(rows) == 0:
        print("No data in CSV. Exiting.")
        return
    
    # Convert to numpy for analysis
    data = np.array([(r['W'], r['seed_ratio'], r['sigma'], r['PSNR']) for r in rows],
                    dtype=[('W', 'f4'), ('seed_ratio', 'f4'), ('sigma', 'f4'), ('PSNR', 'f4')])
    
    # Extract unique values
    W_values = sorted(set(r['W'] for r in rows))
    seed_values = sorted(set(r['seed_ratio'] for r in rows))
    sigma_values = sorted(set(r['sigma'] for r in rows))
    
    print("=" * 70)
    print("PARAMETER SWEEP ANALYSIS SUMMARY")
    print("=" * 70)
    print(f"\nTotal combinations tested: {len(rows)}")
    print(f"W values: {W_values}")
    print(f"Seed ratios: {seed_values}")
    print(f"Sigma values: {sigma_values}")
    
    # Overall statistics
    psnrs = [r['PSNR'] for r in rows]
    print(f"\nOverall PSNR Statistics:")
    print(f"  Min:    {min(psnrs):.4f} dB")
    print(f"  Max:    {max(psnrs):.4f} dB")
    print(f"  Mean:   {np.mean(psnrs):.4f} dB")
    print(f"  StdDev: {np.std(psnrs):.4f} dB")
    print(f"  Median: {np.median(psnrs):.4f} dB")
    
    # Best overall
    best_idx = np.argmax(psnrs)
    best_row = rows[best_idx]
    print(f"\n{'=' * 70}")
    print(f"BEST PARAMETERS (Highest PSNR):")
    print(f"  W:            {best_row['W']:.1f}")
    print(f"  seed_ratio:   {best_row['seed_ratio']:.3f}")
    print(f"  sigma:        {best_row['sigma']:.1f}")
    print(f"  PSNR:         {best_row['PSNR']:.4f} dB")
    print(f"{'=' * 70}")
    
    # Statistics by parameter
    print(f"\nPSNR Statistics by W:")
    for W in W_values:
        w_psnrs = [r['PSNR'] for r in rows if r['W'] == W]
        print(f"  W={W:>2.0f}: mean={np.mean(w_psnrs):.4f}, std={np.std(w_psnrs):.4f}, max={max(w_psnrs):.4f}")
    
    print(f"\nPSNR Statistics by seed_ratio:")
    for seed in seed_values:
        s_psnrs = [r['PSNR'] for r in rows if r['seed_ratio'] == seed]
        print(f"  seed={seed:.3f}: mean={np.mean(s_psnrs):.4f}, std={np.std(s_psnrs):.4f}, max={max(s_psnrs):.4f}")
    
    print(f"\nPSNR Statistics by sigma:")
    for sigma in sigma_values:
        sig_psnrs = [r['PSNR'] for r in rows if r['sigma'] == sigma]
        print(f"  sigma={sigma:>2.0f}: mean={np.mean(sig_psnrs):.4f}, std={np.std(sig_psnrs):.4f}, max={max(sig_psnrs):.4f}")
    
    # Top 5 combinations
    print(f"\n{'=' * 70}")
    print(f"TOP 5 PARAMETER COMBINATIONS:")
    top_5_indices = np.argsort(psnrs)[-5:][::-1]
    for rank, idx in enumerate(top_5_indices, 1):
        r = rows[idx]
        print(f"  {rank}. W={r['W']:>2.0f}, seed={r['seed_ratio']:.3f}, sigma={r['sigma']:>2.0f} → PSNR={r['PSNR']:.4f} dB")
    
    # Generate text report
    report_path = os.path.join(output_dir, "summary_report.txt")
    with open(report_path, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("PARAMETER SWEEP ANALYSIS SUMMARY\n")
        f.write("=" * 70 + "\n\n")
        
        f.write(f"Total combinations tested: {len(rows)}\n")
        f.write(f"W values: {W_values}\n")
        f.write(f"Seed ratios: {seed_values}\n")
        f.write(f"Sigma values: {sigma_values}\n\n")
        
        f.write(f"Overall PSNR Statistics:\n")
        f.write(f"  Min:    {min(psnrs):.4f} dB\n")
        f.write(f"  Max:    {max(psnrs):.4f} dB\n")
        f.write(f"  Mean:   {np.mean(psnrs):.4f} dB\n")
        f.write(f"  StdDev: {np.std(psnrs):.4f} dB\n")
        f.write(f"  Median: {np.median(psnrs):.4f} dB\n\n")
        
        f.write(f"{'=' * 70}\n")
        f.write(f"BEST PARAMETERS (Highest PSNR):\n")
        f.write(f"  W:            {best_row['W']:.1f}\n")
        f.write(f"  seed_ratio:   {best_row['seed_ratio']:.3f}\n")
        f.write(f"  sigma:        {best_row['sigma']:.1f}\n")
        f.write(f"  PSNR:         {best_row['PSNR']:.4f} dB\n")
        f.write(f"{'=' * 70}\n\n")
        
        f.write(f"PSNR Statistics by Parameter:\n\n")
        
        f.write(f"By W:\n")
        for W in W_values:
            w_psnrs = [r['PSNR'] for r in rows if r['W'] == W]
            f.write(f"  W={W:>2.0f}: mean={np.mean(w_psnrs):.4f}, std={np.std(w_psnrs):.4f}, max={max(w_psnrs):.4f}\n")
        
        f.write(f"\nBy seed_ratio:\n")
        for seed in seed_values:
            s_psnrs = [r['PSNR'] for r in rows if r['seed_ratio'] == seed]
            f.write(f"  seed={seed:.3f}: mean={np.mean(s_psnrs):.4f}, std={np.std(s_psnrs):.4f}, max={max(s_psnrs):.4f}\n")
        
        f.write(f"\nBy sigma:\n")
        for sigma in sigma_values:
            sig_psnrs = [r['PSNR'] for r in rows if r['sigma'] == sigma]
            f.write(f"  sigma={sigma:>2.0f}: mean={np.mean(sig_psnrs):.4f}, std={np.std(sig_psnrs):.4f}, max={max(sig_psnrs):.4f}\n")
        
        f.write(f"\n{'=' * 70}\n")
        f.write(f"TOP 5 PARAMETER COMBINATIONS:\n")
        for rank, idx in enumerate(top_5_indices, 1):
            r = rows[idx]
            f.write(f"  {rank}. W={r['W']:>2.0f}, seed={r['seed_ratio']:.3f}, sigma={r['sigma']:>2.0f} → PSNR={r['PSNR']:.4f} dB\n")
        
        f.write(f"\n{'=' * 70}\n")
        f.write(f"Generated: November 25, 2025\n")
    
    print(f"\n{'=' * 70}")
    print(f"✓ Summary report saved to: {report_path}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize parameter sweep results")
    parser.add_argument("--csv", required=True, help="Path to results.csv from param_sweep.py")
    parser.add_argument("--output", default=None, help="Output directory for report (default: same as CSV)")
    
    args = parser.parse_args()
    generate_summary(args.csv, args.output)
