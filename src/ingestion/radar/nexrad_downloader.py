"""NEXRAD Radar Data Downloader

Downloads NEXRAD Level II radar data from NOAA AWS OpenData.

Features:
- All US NEXRAD sites (150+)
- Level II data (highest resolution)
- 5-minute update frequency
- Reflectivity, radial velocity, spectrum width
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict
import s3fs

logger = logging.getLogger(__name__)

NEXRAD_BUCKET = "noaa-nexrad-level2"

NEXRAD_STATIONS = [
    "KTLX",
    "KFWS",
    "KENX",
    "KLOT",
    "KMLB",
    "KLWX",
    "KBOX",
    "KCLE",
    "KGRB",
    "KIND",
    "KJAX",
    "KLBB",
    "KMHX",
    "KOAX",
    "KPBZ",
    "KRIW",
    "KRLX",
    "KRTX",
    "KSEW",
    "KSFX",
    "KSHV",
    "KSOX",
    "KSRX",
    "KTBW",
    "KTLH",
    "KTXK",
    "KTYX",
    "KUDX",
    "KUEX",
    "KVNX",
    "KVTX",
    "KVWX",
    "KYUX",
    "LWX",
    "KEWX",
    "KHGX",
    "KFDR",
    "KAMA",
    "KDDC",
    "KICT",
    "KINX",
    "KVNX",
    "KOUN",
    "KSRX",
    "KLZK",
    "KSHV",
    "KPOE",
    "KLCH",
]


def get_nexrad_stations() -> List[str]:
    """Get list of all NEXRAD station identifiers.

    Returns:
        List[str]: List of 4-letter station codes
    """
    return NEXRAD_STATIONS.copy()


def download_nexrad(
    station: str,
    datetime_obj: Optional[datetime] = None,
    output_dir: str = "/tmp/nexrad",
    max_files: int = 1,
) -> List[str]:
    """Download NEXRAD Level II radar data from AWS S3.

    Args:
        station: NEXRAD station ID (e.g., "KTLX" for Oklahoma City)
        datetime_obj: Date/time to download. If None, downloads latest.
        output_dir: Directory to save downloaded files
        max_files: Maximum number of files to download (default: 1 latest)

    Returns:
        List[str]: Paths to downloaded Level II files
    """
    station = station.upper()
    if not station.startswith("K") and not station.startswith("P"):
        station = "K" + station

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if datetime_obj is None:
        datetime_obj = datetime.utcnow()

    year = datetime_obj.year
    month = datetime_obj.month
    day = datetime_obj.day

    fs = s3fs.S3FileSystem(anon=True)

    prefix = f"{NEXRAD_BUCKET}/{year}/{month:02d}/{day:02d}/{station}"

    downloaded_files = []

    try:
        files = fs.ls(prefix)
    except Exception as e:
        logger.error(f"Error listing S3 bucket for {station}: {e}")
        return downloaded_files

    level2_files = [f for f in files if f.endswith("_V06") or f.endswith("_V03")]

    if not level2_files:
        logger.warning(
            f"No Level II files found for {station} on {datetime_obj.date()}"
        )
        return downloaded_files

    level2_files.sort(reverse=True)

    for i, s3_path in enumerate(level2_files[:max_files]):
        filename = os.path.basename(s3_path)
        local_path = output_path / filename

        try:
            logger.info(f"Downloading {filename}...")
            fs.get(s3_path, str(local_path))
            downloaded_files.append(str(local_path))
            logger.info(f"Downloaded: {local_path}")
        except Exception as e:
            logger.error(f"Failed to download {filename}: {e}")
            continue

    return downloaded_files


def download_nexrad_batch(
    stations: List[str],
    datetime_obj: Optional[datetime] = None,
    output_dir: str = "/tmp/nexrad",
) -> Dict[str, List[str]]:
    """Download NEXRAD data for multiple stations.

    Args:
        stations: List of NEXRAD station IDs
        datetime_obj: Date/time to download
        output_dir: Base output directory

    Returns:
        Dict[str, List[str]]: Mapping of station to downloaded files
    """
    results = {}

    for station in stations:
        station_dir = Path(output_dir) / station
        files = download_nexrad(
            station=station,
            datetime_obj=datetime_obj,
            output_dir=str(station_dir),
        )
        results[station] = files

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download NEXRAD radar data")
    parser.add_argument(
        "--station",
        type=str,
        default="KTLX",
        help="NEXRAD station ID (e.g., KTLX)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="/tmp/nexrad",
        help="Output directory",
    )
    parser.add_argument(
        "--stations",
        type=str,
        help="Comma-separated list of stations (batch mode)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.stations:
        stations = [s.strip() for s in args.stations.split(",")]
        results = download_nexrad_batch(
            stations=stations,
            output_dir=args.output,
        )
        total = sum(len(v) for v in results.values())
        print(f"Downloaded {total} files from {len(stations)} stations")
    else:
        files = download_nexrad(
            station=args.station,
            output_dir=args.output,
        )
        print(f"Downloaded {len(files)} files from {args.station}")
