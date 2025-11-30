# colorize.py
import numpy as np
from scipy.sparse import lil_matrix, csr_matrix, diags
from scipy.sparse.linalg import spsolve, lsqr
from tqdm import tqdm

def get_4_neighbors(h, w):
    # returns neighbor lists for each pixel index
    neigh = [[] for _ in range(h*w)]
    for y in range(h):
        for x in range(w):
            i = y*w + x
            if x > 0: neigh[i].append(i-1)
            if x < w-1: neigh[i].append(i+1)
            if y > 0: neigh[i].append(i-w)
            if y < h-1: neigh[i].append(i+w)
    return neigh

def build_linear_system(Y, known_mask, known_vals, sigma=5.0):
    """
    Build A x = b for Levin-style color propagation.
    - Y: HxW luminance
    - known_mask: HxW boolean (True where the chroma value is known / seed)
    - known_vals: HxW float values at seeds (0 elsewhere)
    - sigma: controls weight sensitivity
    """
    h, w = Y.shape
    N = h*w
    neigh = get_4_neighbors(h,w)
    A = lil_matrix((N, N), dtype=np.float32)
    b = np.zeros(N, dtype=np.float32)

    Yf = Y.flatten()
    known_mask_f = known_mask.flatten()
    known_vals_f = known_vals.flatten()

    for i in range(N):
        if known_mask_f[i]:
            A[i, i] = 1.0
            b[i] = known_vals_f[i]
        else:
            wsum = 0.0
            weights = []
            yi = Yf[i]
            for j in neigh[i]:
                yj = Yf[j]
                wij = np.exp(-((yi - yj)**2) / (2.0 * (sigma**2) + 1e-12))
                weights.append((j, wij))
                wsum += wij
            if wsum < 1e-12:
                # fallback: simple Laplacian
                A[i, i] = 1.0
                for j in neigh[i]:
                    A[i, j] = -1.0 / len(neigh[i])
            else:
                A[i, i] = 1.0
                for j, wij in weights:
                    A[i, j] = -wij / (wsum + 1e-12)
            b[i] = 0.0
    return csr_matrix(A), b

def solve_channel(Y, seeds_mask, seeds_vals, sigma=5.0):
    """
    Solve for a single chroma channel (U or V).
    seeds_mask, seeds_vals are HxW arrays.
    """
    A, b = build_linear_system(Y, seeds_mask, seeds_vals, sigma=sigma)
    # Add regularization to avoid singular matrix (use sparse diagonal for efficiency)
    reg_diag = diags([1e-6] * A.shape[0], offsets=0, format='csr')
    A_reg = A + reg_diag
    try:
        x = spsolve(A_reg, b)
    except RuntimeError as e:
        # Fallback: use least-squares (more robust)
        result = lsqr(A_reg, b, atol=1e-6, btol=1e-6)
        x = result[0]
    return x.reshape(Y.shape)

def sample_seeds_from_channel(channel, seed_ratio=0.05, rng_seed=0):
    """
    Randomly sample pixels from a true chroma channel to use as seeds.
    Returns mask and values.
    """
    h,w = channel.shape
    N = h*w
    n_seeds = max(1, int(N * seed_ratio))
    rng = np.random.default_rng(rng_seed)
    idx = rng.choice(N, size=n_seeds, replace=False)
    mask = np.zeros(N, dtype=bool)
    vals = np.zeros(N, dtype=np.float32)
    mask[idx] = True
    vals[idx] = channel.flatten()[idx]
    return mask.reshape((h,w)), vals.reshape((h,w))

def generate_seeds_from_reference(Y, ref_rgb, seed_ratio=0.05, rng_seed=0):
    """
    Given a reference RGB image aligned with Y (same size),
    extract its U,V and sample seeds from them.
    If ref_rgb is None, returns None.
    """
    if ref_rgb is None:
        return None, None, None, None
    from utils import rgb_to_yuv
    Yr, Ur, Vr = rgb_to_yuv(ref_rgb)
    umask, uvals = sample_seeds_from_channel(Ur, seed_ratio=seed_ratio, rng_seed=rng_seed)
    vmask, vvals = sample_seeds_from_channel(Vr, seed_ratio=seed_ratio, rng_seed=rng_seed+1)
    return umask, uvals, vmask, vvals

def generate_pseudocolor_seeds_from_colormap(Y, cmap='viridis', seed_ratio=0.05, rng_seed=0):
    """
    For pure grayscale input: create a synthetic color reference by mapping Y through a matplotlib colormap,
    then sample seeds from that synthetic chroma. This produces plausible-looking color but is only heuristic.
    """
    import matplotlib
    import matplotlib.cm as cm
    norm = matplotlib.colors.Normalize(vmin=0, vmax=255)
    mapper = cm.get_cmap(cmap)
    rgba = mapper(norm(Y.astype(np.float32)))  # HxWx4 in 0..1
    rgb = (rgba[...,:3] * 255.0).astype(np.float32)
    from utils import rgb_to_yuv
    _, Uc, Vc = rgb_to_yuv(rgb)
    umask, uvals = sample_seeds_from_channel(Uc, seed_ratio=seed_ratio, rng_seed=rng_seed)
    vmask, vvals = sample_seeds_from_channel(Vc, seed_ratio=seed_ratio, rng_seed=rng_seed+1)
    return umask, uvals, vmask, vvals
