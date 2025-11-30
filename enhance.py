# enhance.py
import numpy as np
from scipy.ndimage import gaussian_filter

def contrast_stretching_cst(r, E=0.5):
    """
    Contrast Stretching Transformation (CST)
    Equation (1)
    """
    m = np.mean(r)
    scale = 128.0
    s = m + (r - m) / (1.0 + np.exp(-E * (r - m) / scale))
    return s

def logistic_s_curve(r, k=10.0):
    """
    Logistic S-Curve
    Equation (2)
    """
    r_norm = (r - 128.0) / 128.0
    l = 1.0 / (1.0 + np.exp(-k * r_norm))
    return l * 255.0

def lip_combine(s, l, W=1.0):
    """
    LIP Combination
    Equation (3) + Power (4)
    """
    L0 = 255.0
    p = (s + l - (s * l) / L0)
    p = np.maximum(p, 0.0)
    pW = np.power(p / L0, np.maximum(W, 1e-6)) * L0
    return pW

def adaptive_linear_stretch(pW):
    """
    Adaptive Stretch
    Equation (5)(6)(7)
    """
    pmin = pW.min()
    pmax = pW.max()
    if pmax - pmin < 1e-8:
        return np.clip(pW, 0, 255)
    alpha = 255.0 / (pmax - pmin)
    beta = -pmin * alpha
    n = alpha * pW + beta
    return np.clip(n, 0, 255)

def enhance_grayscale(Y, W=3.0, E=0.5, k_log=10.0, smooth_sigma=0.5):
    """
    Full Journal 1 Enhancement Pipeline
    """
    s = contrast_stretching_cst(Y, E=E)
    l = logistic_s_curve(Y, k=k_log)
    pW = lip_combine(s, l, W=W)

    if smooth_sigma and smooth_sigma > 0:
        pW = gaussian_filter(pW, sigma=smooth_sigma)

    n = adaptive_linear_stretch(pW)
    return n
