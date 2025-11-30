import csv
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
import argparse

def plot_sweep(csv_path, out_dir):
    """Plot parameter sweep results from CSV."""
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    
    # Read CSV (format: W, seed_ratio, sigma, PSNR)
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
    
    # Extract unique values
    W_values = sorted(set(r['W'] for r in rows))
    seed_values = sorted(set(r['seed_ratio'] for r in rows))
    sigma_values = sorted(set(r['sigma'] for r in rows))
    
    print(f"Found {len(rows)} records")
    print(f"W values: {W_values}")
    print(f"Seed values: {seed_values}")
    print(f"Sigma values: {sigma_values}")
    print("=" * 60)
    
    # Chart 1: PSNR vs W (averaged)
    fig, ax = plt.subplots(figsize=(10, 6))
    W_psnrs = defaultdict(list)
    for r in rows:
        W_psnrs[r['W']].append(r['PSNR'])
    
    Ws = sorted(W_psnrs.keys())
    avg_psnrs = [np.mean(W_psnrs[W]) for W in Ws]
    ax.plot(Ws, avg_psnrs, marker='o', linewidth=2, markersize=8, color='blue')
    ax.set_xlabel('W (LIP Power)', fontsize=12)
    ax.set_ylabel('Average PSNR (dB)', fontsize=12)
    ax.set_title('PSNR vs LIP Power W (averaged over seed_ratio and sigma)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'psnr_vs_W_avg.png'), dpi=150)
    print('✓ Saved: psnr_vs_W_avg.png')
    plt.close()
    
    # Chart 2: PSNR vs seed_ratio (averaged)
    fig, ax = plt.subplots(figsize=(10, 6))
    seed_psnrs = defaultdict(list)
    for r in rows:
        seed_psnrs[r['seed_ratio']].append(r['PSNR'])
    
    seeds = sorted(seed_psnrs.keys())
    avg_psnrs = [np.mean(seed_psnrs[s]) for s in seeds]
    ax.plot(seeds, avg_psnrs, marker='s', linewidth=2, markersize=8, color='green')
    ax.set_xlabel('Seed Ratio', fontsize=12)
    ax.set_ylabel('Average PSNR (dB)', fontsize=12)
    ax.set_title('PSNR vs Seed Ratio (averaged over W and sigma)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'psnr_vs_seed_avg.png'), dpi=150)
    print('✓ Saved: psnr_vs_seed_avg.png')
    plt.close()
    
    # Chart 3: PSNR vs sigma (averaged)
    fig, ax = plt.subplots(figsize=(10, 6))
    sigma_psnrs = defaultdict(list)
    for r in rows:
        sigma_psnrs[r['sigma']].append(r['PSNR'])
    
    sigmas = sorted(sigma_psnrs.keys())
    avg_psnrs = [np.mean(sigma_psnrs[s]) for s in sigmas]
    ax.plot(sigmas, avg_psnrs, marker='^', linewidth=2, markersize=8, color='red')
    ax.set_xlabel('Sigma', fontsize=12)
    ax.set_ylabel('Average PSNR (dB)', fontsize=12)
    ax.set_title('PSNR vs Sigma (averaged over W and seed_ratio)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'psnr_vs_sigma_avg.png'), dpi=150)
    print('✓ Saved: psnr_vs_sigma_avg.png')
    plt.close()
    
    # Chart 4: Heatmap - W vs seed_ratio (fixed sigma)
    if len(sigma_values) > 0:
        for sigma in [sigma_values[0]]:  # Show first sigma
            fig, ax = plt.subplots(figsize=(10, 6))
            psnr_matrix = np.zeros((len(seed_values), len(W_values)))
            
            for i, seed in enumerate(seed_values):
                for j, W in enumerate(W_values):
                    matching = [r for r in rows if r['W'] == W and r['seed_ratio'] == seed and r['sigma'] == sigma]
                    if matching:
                        psnr_matrix[i, j] = matching[0]['PSNR']
            
            im = ax.imshow(psnr_matrix, cmap='RdYlGn', aspect='auto', origin='lower')
            ax.set_xticks(range(len(W_values)))
            ax.set_yticks(range(len(seed_values)))
            ax.set_xticklabels([f'{w:.0f}' for w in W_values])
            ax.set_yticklabels([f'{s:.3f}' for s in seed_values])
            ax.set_xlabel('W (LIP Power)', fontsize=12)
            ax.set_ylabel('Seed Ratio', fontsize=12)
            ax.set_title(f'PSNR Heatmap: W vs Seed Ratio (sigma={sigma})', fontsize=14, fontweight='bold')
            
            # Add text annotations
            for i in range(len(seed_values)):
                for j in range(len(W_values)):
                    if psnr_matrix[i, j] > 0:
                        text = ax.text(j, i, f'{psnr_matrix[i, j]:.2f}',
                                      ha="center", va="center", color="black", fontsize=9)
            
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label('PSNR (dB)', fontsize=11)
            plt.tight_layout()
            plt.savefig(os.path.join(out_dir, f'psnr_heatmap_W_seed_sigma{sigma}.png'), dpi=150)
            print(f'✓ Saved: psnr_heatmap_W_seed_sigma{sigma}.png')
            plt.close()
    
    print("=" * 60)
    print(f'✓ All charts saved to: {out_dir}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot parameter sweep results")
    parser.add_argument("--csv", default="results/param_sweep/results.csv", help="Path to results CSV file")
    parser.add_argument("--output", default="results/param_sweep", help="Output directory for charts")
    
    args = parser.parse_args()
    plot_sweep(args.csv, args.output)
