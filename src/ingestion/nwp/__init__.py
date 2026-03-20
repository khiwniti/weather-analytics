"""
NWP (Numerical Weather Prediction) Data Ingestion Module

Handles downloading and processing of weather forecast model data:
- GFS (Global Forecast System)
- HRRR (High-Resolution Rapid Refresh)
- ECMWF (European Centre for Medium-Range Weather Forecasts)
"""

from .gfs_downloader import download_gfs, get_next_cycle_time, is_data_available
from .hrrr_downloader import download_hrrr

__all__ = [
    "download_gfs",
    "get_next_cycle_time",
    "is_data_available",
    "download_hrrr",
]
