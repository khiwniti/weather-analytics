"""
GFS (Global Forecast System) Data Downloader

Downloads GFS forecast data from NOAA NOMADS servers.

Features:
- Full global coverage (0.25° resolution)
- All 4 cycles (00Z, 06Z, 12Z, 18Z)
- All 384 forecast hours
- Smart scheduling with expected release times
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import requests

logger = logging.getLogger(__name__)

# GFS cycle availability (approximate times after cycle hour)
GFS_AVAILABILITY_DELAY = {
    "00": timedelta(hours=4, minutes=30),
    "06": timedelta(hours=4, minutes=30),
    "12": timedelta(hours=4, minutes=30),
    "18": timedelta(hours=4, minutes=30),
}

# NOMADS base URL
NOMADS_BASE_URL = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl"


def get_next_cycle_time(reference_time: Optional[datetime] = None) -> datetime:
    """
    Calculate the next expected GFS cycle time.

    GFS cycles are at 00Z, 06Z, 12Z, 18Z.
    Data is typically available ~4.5 hours after cycle time.

    Args:
        reference_time: Reference time (defaults to current UTC)

    Returns:
        datetime: Next expected cycle time when data should be available
    """
    if reference_time is None:
        reference_time = datetime.utcnow()

    # GFS cycle hours
    cycle_hours = [0, 6, 12, 18]

    # Find next cycle
    current_hour = reference_time.hour
    next_cycle_hour = None

    for hour in cycle_hours:
        if hour > current_hour:
            next_cycle_hour = hour
            break

    if next_cycle_hour is None:
        # Next cycle is tomorrow at 00Z
        next_cycle_time = reference_time.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
    else:
        next_cycle_time = reference_time.replace(
            hour=next_cycle_hour, minute=0, second=0, microsecond=0
        )

    # Add availability delay
    cycle_str = f"{next_cycle_time.hour:02d}"
    available_time = next_cycle_time + GFS_AVAILABILITY_DELAY.get(
        cycle_str, timedelta(hours=4, minutes=30)
    )

    return available_time


def is_data_available(cycle: str, date: Optional[datetime] = None) -> bool:
    """
    Check if GFS data is available for a specific cycle.

    Args:
        cycle: Cycle hour ("00", "06", "12", "18")
        date: Date for the cycle (defaults to today)

    Returns:
        bool: True if data is available
    """
    if date is None:
        date = datetime.utcnow()

    date_str = date.strftime("%Y%m%d")

    # Try to access NOMADS directory listing
    try:
        url = f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl?file=gfs.t{cycle}z.pgrb2.0p25.f000&lev_10_m_above_ground=on&var_UGRD=on&leftlon=0&rightlon=360&toplat=90&bottomlat=-90&dir=%2Fgfs.{date_str}%2F{cycle}%2Fatmos"
        response = requests.head(url, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.warning(f"Could not check data availability: {e}")
        return False


def download_gfs(
    cycle: str,
    forecast_hours: List[int],
    output_dir: str = "/tmp/gfs",
    variables: Optional[List[str]] = None,
    pressure_levels: Optional[List[int]] = None,
    bbox: Optional[tuple] = None,
) -> List[str]:
    """
    Download GFS forecast data from NOMADS.

    Args:
        cycle: Cycle hour ("00", "06", "12", "18")
        forecast_hours: List of forecast hours to download (0-384)
        output_dir: Directory to save downloaded files
        variables: List of surface variables to download
        pressure_levels: List of pressure levels (hPa)
        bbox: Bounding box (leftlon, rightlon, toplat, bottomlat)

    Returns:
        List[str]: Paths to downloaded files
    """
    from pathlib import Path
    import urllib.request

    # Default variables
    if variables is None:
        variables = ["TMP", "UGRD", "VGRD", "PRATE", "APCP"]

    if pressure_levels is None:
        pressure_levels = [1000, 925, 850, 700, 500, 300, 250, 200, 100, 50, 10]

    if bbox is None:
        bbox = (0, 360, 90, -90)  # Global

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Current date
    date = datetime.utcnow()
    date_str = date.strftime("%Y%m%d")

    downloaded_files = []

    # Download each forecast hour
    for fhr in forecast_hours:
        try:
            # Construct URL
            filename = f"gfs.t{cycle}z.pgrb2.0p25.f{fhr:03d}"
            url = f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl"

            params = {
                "file": filename,
                "leftlon": bbox[0],
                "rightlon": bbox[1],
                "toplat": bbox[2],
                "bottomlat": bbox[3],
                "dir": f"/gfs.{date_str}/{cycle}/atmos",
            }

            # Add variables
            for var in variables:
                params[f"var_{var}"] = "on"

            # Add pressure levels
            for level in pressure_levels:
                params[f"lev_{level}_mb"] = "on"

            # Add surface level
            params["lev_surface"] = "on"
            params["lev_2_m_above_ground"] = "on"
            params["lev_10_m_above_ground"] = "on"

            # Download file
            output_file = output_path / filename
            logger.info(f"Downloading GFS {cycle}Z F{fhr:03d}...")

            # Build query string
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            full_url = f"{url}?{query_string}"

            urllib.request.urlretrieve(full_url, output_file)
            downloaded_files.append(str(output_file))

            logger.info(f"Downloaded: {output_file}")

        except Exception as e:
            logger.error(f"Failed to download F{fhr:03d}: {e}")
            continue

    return downloaded_files


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download GFS data")
    parser.add_argument(
        "--cycle", type=str, required=True, help="Cycle hour (00, 06, 12, 18)"
    )
    parser.add_argument("--test", action="store_true", help="Download single test file")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.test:
        # Download just first 2 forecast hours for testing
        files = download_gfs(args.cycle, forecast_hours=[0, 1])
        print(f"Downloaded {len(files)} files")
    else:
        # Download all forecast hours
        files = download_gfs(args.cycle, forecast_hours=list(range(385)))
        print(f"Downloaded {len(files)} files")
