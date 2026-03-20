"""
RAPIDS GPU Setup Module

Provides utilities for initializing and verifying GPU access for
weather data processing.
"""

import os
import sys


def check_gpu_available():
    """
    Check if GPU is available for RAPIDS processing.

    Returns:
        bool: True if GPU is available, False otherwise
    """
    try:
        import cupy as cp

        return cp.cuda.is_available()
    except ImportError:
        print("CuPy not installed. Install RAPIDS via conda:")
        print(
            "conda create -n weather-rapids -c rapidsai -c conda-forge -c nvidia rapids=24.12 python=3.11 cuda-version=12"
        )
        return False
    except Exception as e:
        print(f"GPU check failed: {e}")
        return False


def get_gpu_info():
    """
    Get GPU device information.

    Returns:
        dict: GPU device information or None if not available
    """
    if not check_gpu_available():
        return None

    import cupy as cp

    device = cp.cuda.Device()
    return {
        "name": device.name.decode() if isinstance(device.name, bytes) else device.name,
        "compute_capability": device.compute_capability,
        "total_memory": device.mem_info[1],
        "free_memory": device.mem_info[0],
    }


def init_gpu():
    """
    Initialize GPU for RAPIDS processing.

    Returns:
        bool: True if initialization successful
    """
    if not check_gpu_available():
        return False

    import cupy as cp

    # Warm up GPU
    cp.cuda.Stream.null.synchronize()
    print(f"GPU initialized: {get_gpu_info()}")
    return True


if __name__ == "__main__":
    if check_gpu_available():
        print("GPU available: Yes")
        info = get_gpu_info()
        if info:
            print(f"Device: {info['name']}")
            print(
                f"Memory: {info['free_memory'] / 1e9:.2f} GB free / {info['total_memory'] / 1e9:.2f} GB total"
            )
        sys.exit(0)
    else:
        print("GPU available: No")
        sys.exit(1)
