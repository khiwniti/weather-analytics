"""ASOS Ground Observation Downloader

Downloads ASOS weather station observations from Iowa Mesonet.

Features:
- ~900 US airport stations
- Hourly observations
- Temperature, dewpoint, wind, pressure, visibility
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict
import urllib.request
import urllib.parse
import csv

logger = logging.getLogger(__name__)

IEM_ASOS_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"


def get_asos_stations() -> List[str]:
    """Get list of all ASOS station identifiers.

    Returns:
        List[str]: List of ICAO station codes
    """
    return [
        "KJFK",
        "KLAX",
        "KORD",
        "KDFW",
        "KATL",
        "KSFO",
        "KDEN",
        "KLAS",
        "KPHX",
        "KMIA",
        "KIAH",
        "KSEA",
        "KMCO",
        "KEWR",
        "KDTW",
        "KMSP",
        "KBOS",
        "KPHL",
        "KLGA",
        "KFLL",
        "KBWI",
        "KIAD",
        "KDCA",
        "KSAN",
        "KTampa",
        "KSTL",
        "KSLC",
        "KMDW",
        "KDAL",
        "KHOUs",
        "KHOU",
        "KOAK",
        "KCLE",
        "KCMH",
        "KIND",
        "KPDX",
        "KABQ",
        "KSJC",
        "KMCI",
        "KRSW",
    ]


def download_asos(
    station: str,
    start_date: datetime,
    end_date: datetime,
    output_dir: str = "/tmp/asos",
    variables: Optional[List[str]] = None,
) -> str:
    """Download ASOS observations from Iowa Mesonet.

    Args:
        station: ASOS station ID (e.g., "KJFK")
        start_date: Start date/time
        end_date: End date/time
        output_dir: Directory to save downloaded files
        variables: List of variables to download

    Returns:
        str: Path to downloaded CSV file
    """
    if variables is None:
        variables = ["tmpf", "dwpf", "sknt", "drct", "p01i", "mslp", "vsby"]

    station = station.upper()
    if not station.startswith("K") and not station.startswith("P"):
        station = "K" + station

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    params = {
        "station": station,
        "data": ",".join(variables),
        "year1": start_date.year,
        "month1": start_date.month,
        "day1": start_date.day,
        "hour1": start_date.hour,
        "year2": end_date.year,
        "month2": end_date.month,
        "day2": end_date.day,
        "hour2": end_date.hour,
        "tz": "UTC",
        "format": "comma",
        "missing": "M",
        "trace": "T",
        "direct": "yes",
    }

    url = f"{IEM_ASOS_URL}?{urllib.parse.urlencode(params)}"

    filename = (
        f"{station}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    )
    output_file = output_path / filename

    try:
        logger.info(f"Downloading ASOS data for {station}...")
        urllib.request.urlretrieve(url, output_file)
        logger.info(f"Downloaded: {output_file}")
        return str(output_file)

    except Exception as e:
        logger.error(f"Failed to download ASOS data: {e}")
        raise


def download_asos_batch(
    stations: List[str],
    start_date: datetime,
    end_date: datetime,
    output_dir: str = "/tmp/asos",
) -> Dict[str, str]:
    """Download ASOS data for multiple stations.

    Args:
        stations: List of ASOS station IDs
        start_date: Start date/time
        end_date: End date/time
        output_dir: Base output directory

    Returns:
        Dict[str, str]: Mapping of station to downloaded file path
    """
    results = {}

    for station in stations:
        try:
            station_dir = Path(output_dir) / station
            file_path = download_asos(
                station=station,
                start_date=start_date,
                end_date=end_date,
                output_dir=str(station_dir),
            )
            results[station] = file_path
        except Exception as e:
            logger.warning(f"Failed to download {station}: {e}")
            results[station] = None

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download ASOS observations")
    parser.add_argument(
        "--station",
        type=str,
        default="KJFK",
        help="ASOS station ID (e.g., KJFK)",
    )
    parser.add_argument(
        "--start",
        type=str,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        type=str,
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="/tmp/asos",
        help="Output directory",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.start:
        start_date = datetime.strptime(args.start, "%Y-%m-%d")
    else:
        start_date = datetime.utcnow() - timedelta(days=1)

    if args.end:
        end_date = datetime.strptime(args.end, "%Y-%m-%d")
    else:
        end_date = datetime.utcnow()

    file_path = download_asos(
        station=args.station,
        start_date=start_date,
        end_date=end_date,
        output_dir=args.output,
    )
    print(f"Downloaded: {file_path}")
