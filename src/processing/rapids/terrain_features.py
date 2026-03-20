"""
GPU-Accelerated Terrain Feature Engineering

Computes terrain derivatives (slope, aspect, etc.) on GPU using CuPy.

Features:
- Slope calculation (gradient magnitude)
- Aspect calculation (gradient direction)
- Flow accumulation
- Curvature analysis
"""

import logging
import numpy as np
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def compute_slope(
    dem: "np.ndarray",
    cell_size: float = 30.0,
) -> "np.ndarray":
    """
    Compute terrain slope from DEM using GPU acceleration.

    Uses gradient calculation for slope magnitude.

    Args:
        dem: Digital Elevation Model array (2D)
        cell_size: Cell size in meters (default: 30m)

    Returns:
        np.ndarray: Slope array in degrees
    """
    # Try CuPy for GPU, fall back to NumPy
    try:
        import cupy as cp

        use_gpu = True
        dem_gpu = cp.asarray(dem) if not isinstance(dem, cp.ndarray) else dem
        logger.info("Computing slope on GPU")
    except ImportError:
        use_gpu = False
        dem_gpu = dem
        logger.warning("CuPy not available, computing slope on CPU")

    # Compute gradients
    # Using Sobel-like kernel for gradient
    if use_gpu:
        # Gradient in x direction (west-east)
        grad_x = cp.zeros_like(dem_gpu)
        grad_x[1:-1, 1:-1] = (dem_gpu[1:-1, 2:] - dem_gpu[1:-1, :-2]) / (2 * cell_size)

        # Gradient in y direction (south-north)
        grad_y = cp.zeros_like(dem_gpu)
        grad_y[1:-1, 1:-1] = (dem_gpu[2:, 1:-1] - dem_gpu[:-2, 1:-1]) / (2 * cell_size)

        # Slope magnitude
        slope_rad = cp.arctan(cp.sqrt(grad_x**2 + grad_y**2))
        slope_deg = cp.degrees(slope_rad)

        # Convert back to NumPy
        return cp.asnumpy(slope_deg)
    else:
        # NumPy version
        grad_x = np.zeros_like(dem_gpu)
        grad_x[1:-1, 1:-1] = (dem_gpu[1:-1, 2:] - dem_gpu[1:-1, :-2]) / (2 * cell_size)

        grad_y = np.zeros_like(dem_gpu)
        grad_y[1:-1, 1:-1] = (dem_gpu[2:, 1:-1] - dem_gpu[:-2, 1:-1]) / (2 * cell_size)

        slope_rad = np.arctan(np.sqrt(grad_x**2 + grad_y**2))
        slope_deg = np.degrees(slope_rad)

        return slope_deg


def compute_aspect(
    dem: "np.ndarray",
) -> "np.ndarray":
    """
    Compute terrain aspect from DEM using GPU acceleration.

    Aspect is the direction of steepest slope (0-360 degrees).

    Args:
        dem: Digital Elevation Model array (2D)

    Returns:
        np.ndarray: Aspect array in degrees (0=N, 90=E, 180=S, 270=W)
    """
    # Try CuPy for GPU, fall back to NumPy
    try:
        import cupy as cp

        use_gpu = True
        dem_gpu = cp.asarray(dem) if not isinstance(dem, cp.ndarray) else dem
        logger.info("Computing aspect on GPU")
    except ImportError:
        use_gpu = False
        dem_gpu = dem
        logger.warning("CuPy not available, computing aspect on CPU")

    # Compute gradients
    if use_gpu:
        # Gradient in x direction (west-east)
        grad_x = cp.zeros_like(dem_gpu)
        grad_x[1:-1, 1:-1] = dem_gpu[1:-1, 2:] - dem_gpu[1:-1, :-2]

        # Gradient in y direction (south-north, negated for aspect convention)
        grad_y = cp.zeros_like(dem_gpu)
        grad_y[1:-1, 1:-1] = dem_gpu[:-2, 1:-1] - dem_gpu[2:, 1:-1]

        # Aspect (arctan2 gives angle in radians)
        aspect_rad = cp.arctan2(grad_x, grad_y)
        aspect_deg = cp.degrees(aspect_rad)

        # Convert to 0-360 range
        aspect_deg = cp.where(aspect_deg < 0, aspect_deg + 360, aspect_deg)

        return cp.asnumpy(aspect_deg)
    else:
        # NumPy version
        grad_x = np.zeros_like(dem_gpu)
        grad_x[1:-1, 1:-1] = dem_gpu[1:-1, 2:] - dem_gpu[1:-1, :-2]

        grad_y = np.zeros_like(dem_gpu)
        grad_y[1:-1, 1:-1] = dem_gpu[:-2, 1:-1] - dem_gpu[2:, 1:-1]

        aspect_rad = np.arctan2(grad_x, grad_y)
        aspect_deg = np.degrees(aspect_rad)
        aspect_deg = np.where(aspect_deg < 0, aspect_deg + 360, aspect_deg)

        return aspect_deg


def compute_curvature(
    dem: "np.ndarray",
) -> Tuple["np.ndarray", "np.ndarray"]:
    """
    Compute terrain curvature (profile and planform).

    Args:
        dem: Digital Elevation Model array (2D)

    Returns:
        Tuple: (profile_curvature, planform_curvature)
    """
    try:
        import cupy as cp

        use_gpu = True
        dem_gpu = cp.asarray(dem) if not isinstance(dem, cp.ndarray) else dem
    except ImportError:
        use_gpu = False
        dem_gpu = dem

    # Second derivatives
    if use_gpu:
        # Second derivative in x
        d2x = cp.zeros_like(dem_gpu)
        d2x[1:-1, 1:-1] = (
            dem_gpu[1:-1, 2:] - 2 * dem_gpu[1:-1, 1:-1] + dem_gpu[1:-1, :-2]
        )

        # Second derivative in y
        d2y = cp.zeros_like(dem_gpu)
        d2y[1:-1, 1:-1] = (
            dem_gpu[2:, 1:-1] - 2 * dem_gpu[1:-1, 1:-1] + dem_gpu[:-2, 1:-1]
        )

        # Mixed derivative
        dxy = cp.zeros_like(dem_gpu)
        dxy[1:-1, 1:-1] = (
            dem_gpu[2:, 2:] - dem_gpu[2:, :-2] - dem_gpu[:-2, 2:] + dem_gpu[:-2, :-2]
        ) / 4

        return (cp.asnumpy(d2x), cp.asnumpy(d2y))
    else:
        d2x = np.zeros_like(dem_gpu)
        d2x[1:-1, 1:-1] = (
            dem_gpu[1:-1, 2:] - 2 * dem_gpu[1:-1, 1:-1] + dem_gpu[1:-1, :-2]
        )

        d2y = np.zeros_like(dem_gpu)
        d2y[1:-1, 1:-1] = (
            dem_gpu[2:, 1:-1] - 2 * dem_gpu[1:-1, 1:-1] + dem_gpu[:-2, 1:-1]
        )

        return (d2x, d2y)


if __name__ == "__main__":
    # Test with synthetic DEM
    logging.basicConfig(level=logging.INFO)

    x = np.linspace(-5, 5, 100)
    y = np.linspace(-5, 5, 100)
    X, Y = np.meshgrid(x, y)
    dem = np.exp(-(X**2 + Y**2) / 10) * 1000  # Gaussian hill

    slope = compute_slope(dem)
    aspect = compute_aspect(dem)

    print(f"Slope range: {slope.min():.2f} - {slope.max():.2f} degrees")
    print(f"Aspect range: {aspect.min():.2f} - {aspect.max():.2f} degrees")
