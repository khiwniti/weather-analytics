"""GOES Satellite Data Downloader

Downloads GOES-16/17 ABI satellite data from NOAA AWS OpenData.

Features:
- GOES-16 (East) and GOES-17 (West) support
- All 16 ABI bands
- CONUS and Full Disk domains
- 5-minute update frequency
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
import s3fs

logger = logging.getLogger(__name__)

GOES_BUCKET = {
    "GOES-16": "noaa-goes16",
    "GOES-17": "noaa-goes17",
}

ABI_BANDS = list(range(1, 17))

DOMAINS = {
    "CONUS": "CONUS",
    "FullDisk": "F",
    "Mesoscale-1": "M1",
    "Mesoscale-2": "M2",
}


def get_goes_latest(
    satellite: str = "GOES-16",
    product: str = "ABI-L1b-RadC",
    domain: str = "CONUS",
) -> Optional[datetime]:
    """Get the latest available GOES data timestamp.

    Args:
        satellite: GOES-16 or GOES-17
        product: ABI product (ABI-L1b-RadC for CONUS)
        domain: CONUS, FullDisk, Mesoscale-1, Mesoscale-2

    Returns:
        datetime of latest available data, or None if unavailable
    """
    try:
        bucket = GOES_BUCKET.get(satellite)
        if not bucket:
            raise ValueError(f"Unknown satellite: {satellite}")

        fs = s3fs.S3FileSystem(anon=True)

        now = datetime.utcnow()
        date_path = now.strftime("%Y/%j")

        prefix = f"{bucket}/{product}/{date_path}"
        try:
            files = fs.ls(prefix)
            if files:
                latest_file = files[-1]
                filename = os.path.basename(latest_file)
                s = f"s{now.year}{now.strftime('%j')}"
                e = f"e{int(filename.split('_e')[1].split('.')[0]):06d}"
                scan_time = datetime.strptime(
                    f"{now.year}{now.strftime('%j')}{e[1:]}", "%Y%j%H%M%S"
                )
                return scan_time
        except Exception:
            pass

        return None

    except Exception as e:
        logger.error(f"Error getting latest GOES data: {e}")
        return None


def download_goes(
    satellite: str = "GOES-16",
    product: str = "ABI-L1b-RadC",
    domain: str = "CONUS",
    bands: Optional[List[int]] = None,
    datetime_obj: Optional[datetime] = None,
    output_dir: str = "/tmp/goes",
) -> List[str]:
    """Download GOES satellite data from AWS S3.

    Args:
        satellite: GOES-16 or GOES-17
        product: ABI product type
            - ABI-L1b-RadC: CONUS Radiance
            - ABI-L1b-RadF: Full Disk Radiance
            - ABI-L2-DSLC: Derived Stability
        domain: CONUS, FullDisk, Mesoscale-1, Mesoscale-2
        bands: List of ABI bands to download (1-16). If None, downloads all.
        datetime_obj: Specific datetime to download. If None, downloads latest.
        output_dir: Directory to save downloaded files

    Returns:
        List[str]: Paths to downloaded NetCDF files
    """
    bucket = GOES_BUCKET.get(satellite)
    if not bucket:
        raise ValueError(f"Unknown satellite: {satellite}. Use GOES-16 or GOES-17")

    if bands is None:
        bands = ABI_BANDS

    domain_code = DOMAINS.get(domain, "CONUS")
    if domain == "CONUS":
        product = "ABI-L1b-RadC"
    elif domain == "FullDisk":
        product = "ABI-L1b-RadF"

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if datetime_obj is None:
        datetime_obj = datetime.utcnow()

    year = datetime_obj.year
    day_of_year = datetime_obj.strftime("%j")
    hour = datetime_obj.hour

    fs = s3fs.S3FileSystem(anon=True)

    prefix = f"{bucket}/{product}/{year}/{day_of_year}/{hour:02d}"

    downloaded_files = []

    try:
        files = fs.ls(prefix)
    except Exception as e:
        logger.error(f"Error listing S3 bucket: {e}")
        return downloaded_files

    for band in bands:
        band_str = f"C{band:02d}"
        matching_files = [f for f in files if band_str in f and domain_code in f]

        if not matching_files:
            logger.warning(f"No files found for band {band} in {domain}")
            continue

        latest_file = matching_files[-1]
        filename = os.path.basename(latest_file)
        local_path = output_path / filename

        try:
            logger.info(f"Downloading {filename}...")
            fs.get(latest_file, str(local_path))
            downloaded_files.append(str(local_path))
            logger.info(f"Downloaded: {local_path}")
        except Exception as e:
            logger.error(f"Failed to download {filename}: {e}")
            continue

    return downloaded_files


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download GOES satellite data")
    parser.add_argument(
        "--satellite",
        type=str,
        default="GOES-16",
        choices=["GOES-16", "GOES-17"],
        help="Satellite to download",
    )
    parser.add_argument(
        "--domain",
        type=str,
        default="CONUS",
        choices=["CONUS", "FullDisk", "Mesoscale-1", "Mesoscale-2"],
        help="Domain to download",
    )
    parser.add_argument(
        "--bands",
        type=str,
        default="all",
        help="Bands to download (comma-separated or 'all')",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="/tmp/goes",
        help="Output directory",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    bands = None if args.bands == "all" else [int(b) for b in args.bands.split(",")]

    files = download_goes(
        satellite=args.satellite,
        domain=args.domain,
        bands=bands,
        output_dir=args.output,
    )
    print(f"Downloaded {len(files)} files")
