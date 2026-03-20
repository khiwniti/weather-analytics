"""
HRRR (High-Resolution Rapid Refresh) Data Downloader

Downloads HRRR forecast data from NOAA NOMADS servers.

Features:
- Full CONUS coverage (3km resolution)
- Hourly updates (00-23Z)
- Up to 18-48 hour forecasts
- High-resolution for severe weather
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import requests

logger = logging.getLogger(__name__)

# HRRR availability delay (approximately 45-60 minutes after cycle)
HRRR_AVAILABILITY_DELAY = timedelta(minutes=45)

# NOMADS HRRR URL
NOMADS_HRRR_URL = "https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl"


def get_next_hrrr_cycle(reference_time: Optional[datetime] = None) -> datetime:
    """
    Calculate the next expected HRRR cycle time.

    HRRR runs hourly (00-23Z).
    Data is typically available ~45 minutes after cycle time.

    Args:
        reference_time: Reference time (defaults to current UTC)

    Returns:
        datetime: Next expected cycle time when data should be available
    """
    if reference_time is None:
        reference_time = datetime.utcnow()

    # HRRR runs every hour, next cycle is next hour
    next_hour = reference_time.hour + 1
    if next_hour >= 24:
        next_cycle_time = reference_time.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
    else:
        next_cycle_time = reference_time.replace(
            hour=next_hour, minute=0, second=0, microsecond=0
        )

    # Add availability delay
    available_time = next_cycle_time + HRRR_AVAILABILITY_DELAY

    return available_time


def is_hrrr_available(cycle: str, date: Optional[datetime] = None) -> bool:
    """
    Check if HRRR data is available for a specific cycle.

    Args:
        cycle: Cycle hour ("00" to "23")
        date: Date for the cycle (defaults to today)

    Returns:
        bool: True if data is available
    """
    if date is None:
        date = datetime.utcnow()

    date_str = date.strftime("%Y%m%d")

    try:
        url = f"https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl?file=hrrr.t{cycle}z.wrfsfcf00.grib2&lev_surface=on&var_TMP=on&leftlon=-130&rightlon=-60&toplat=55&bottomlat=20&dir=%2Fhrrr.{date_str}%2F{cycle}%2F"
        response = requests.head(url, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.warning(f"Could not check HRRR availability: {e}")
        return False


def download_hrrr(
    cycle: str,
    forecast_hours: Optional[List[int]] = None,
    output_dir: str = "/tmp/hrrr",
    domain: str = "CONUS",
    variables: Optional[List[str]] = None,
) -> List[str]:
    """
    Download HRRR forecast data from NOMADS.

    Args:
        cycle: Cycle hour ("00" to "23")
        forecast_hours: List of forecast hours (default 0-18)
        output_dir: Directory to save downloaded files
        domain: Geographic domain ("CONUS", "AK", "HI")
        variables: List of variables to download

    Returns:
        List[str]: Paths to downloaded files
    """
    from pathlib import Path
    import urllib.request

    # Default forecast hours (0-18)
    if forecast_hours is None:
        forecast_hours = list(range(19))

    # Default variables
    if variables is None:
        variables = ["TMP", "DPT", "UGRD", "VGRD", "REF", "PRECIP"]

    # Domain bounding boxes
    domains = {
        "CONUS": (-130, -60, 55, 20),
        "AK": (-180, -130, 72, 50),
        "HI": (-165, -150, 25, 18),
    }
    bbox = domains.get(domain, domains["CONUS"])

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
            # HRRR filenames
            filename = f"hrrr.t{cycle}z.wrfsfcf{fhr:02d}.grib2"
            url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl"

            params = {
                "file": filename,
                "leftlon": bbox[0],
                "rightlon": bbox[1],
                "toplat": bbox[2],
                "bottomlat": bbox[3],
                "dir": f"/hrrr.{date_str}/{cycle}/",
            }

            # Add variables
            for var in variables:
                params[f"var_{var}"] = "on"

            # Add levels
            params["lev_surface"] = "on"
            params["lev_2_m_above_ground"] = "on"
            params["lev_10_m_above_ground"] = "on"

            # Download file
            output_file = output_path / filename
            logger.info(f"Downloading HRRR {cycle}Z F{fhr:02d}...")

            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            full_url = f"{url}?{query_string}"

            urllib.request.urlretrieve(full_url, output_file)
            downloaded_files.append(str(output_file))

            logger.info(f"Downloaded: {output_file}")

        except Exception as e:
            logger.error(f"Failed to download F{fhr:02d}: {e}")
            continue

    return downloaded_files


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download HRRR data")
    parser.add_argument("--cycle", type=str, required=True, help="Cycle hour (00-23)")
    parser.add_argument("--test", action="store_true", help="Download single test file")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.test:
        files = download_hrrr(args.cycle, forecast_hours=[0, 1])
        print(f"Downloaded {len(files)} files")
    else:
        files = download_hrrr(args.cycle)
        print(f"Downloaded {len(files)} files")
