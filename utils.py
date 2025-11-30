# utils.py
import numpy as np
from PIL import Image
import os

def ensure_dirs(paths):
    for p in paths:
        os.makedirs(p, exist_ok=True)

def load_image(path):
    """
    Load image. Returns numpy array dtype float32.
    If single-channel image is loaded, returns HxW (2D).
    If color, returns HxWx3.
    """
    im = Image.open(path)
    im = im.convert("RGB")  # convert to RGB to make handling consistent
    arr = np.asarray(im).astype(np.float32)
    return arr

def load_maybe_gray(path):
    """
    Load and return either HxW grayscale (2D) or HxWx3 RGB (3D) depending on file.
    We'll use Pillow to inspect mode.
    """
    im = Image.open(path)
    if im.mode == "L":
        arr = np.asarray(im).astype(np.float32)
        return arr  # 2D
    else:
        im = im.convert("RGB")
        return np.asarray(im).astype(np.float32)

def save_rgb(path, arr):
    a = np.clip(arr, 0, 255).astype(np.uint8)
    Image.fromarray(a).save(path)

def save_gray(path, arr):
    a = np.clip(arr, 0, 255).astype(np.uint8)
    Image.fromarray(a).convert("L").save(path)

def is_grayscale_array(arr):
    """Detect whether an array is grayscale by shape (2D) or if 3D but all channels equal."""
    if arr.ndim == 2:
        return True
    if arr.ndim == 3:
        if np.allclose(arr[...,0], arr[...,1]) and np.allclose(arr[...,1], arr[...,2]):
            return True
    return False

# YUV conversion (BT.601 / simple)
def rgb_to_yuv(rgb):
    # rgb in float32 [0,255]
    R = rgb[...,0]; G = rgb[...,1]; B = rgb[...,2]
    Y = 0.299*R + 0.587*G + 0.114*B
    U = -0.14713*R - 0.28886*G + 0.436*B
    V = 0.615*R - 0.51499*G - 0.10001*B
    return Y, U, V

def yuv_to_rgb(Y, U, V):
    R = Y + 1.13983*V
    G = Y - 0.39465*U - 0.58060*V
    B = Y + 2.03211*U
    return np.stack([R, G, B], axis=-1)

def grayscale_from_rgb(rgb):
    Y, _, _ = rgb_to_yuv(rgb)
    return Y
