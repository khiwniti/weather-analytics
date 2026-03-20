"""
RAPIDS Processing Module

GPU-accelerated data processing for weather data using NVIDIA RAPIDS.
"""

from .grib_to_zarr import convert_grib_to_zarr, upload_to_s3
from .terrain_features import compute_slope, compute_aspect

__all__ = [
    "convert_grib_to_zarr",
    "upload_to_s3",
    "compute_slope",
    "compute_aspect",
]
