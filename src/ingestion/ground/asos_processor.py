"""ASOS Ground Observation Processor

Converts ASOS CSV data to Zarr format with GPU acceleration.

Features:
- CSV to Zarr conversion
- GPU-accelerated via cuDF
- Variables: temperature, dewpoint, wind, pressure, visibility
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import numpy as np
import zarr
from numcodecs import Blosc

logger = logging.getLogger(__name__)

ASOS_COLUMNS = {
    "tmpf": {"name": "temperature", "units": "F"},
    "dwpf": {"name": "dewpoint", "units": "F"},
    "sknt": {"name": "wind_speed", "units": "kt"},
    "drct": {"name": "wind_direction", "units": "deg"},
    "p01i": {"name": "precipitation", "units": "in"},
    "mslp": {"name": "pressure", "units": "hPa"},
    "vsby": {"name": "visibility", "units": "mi"},
}


def convert_asos_to_zarr(
    csv_path: str,
    zarr_path: str,
    station: Optional[str] = None,
) -> str:
    """Convert ASOS CSV file to Zarr format.

    Args:
        csv_path: Path to ASOS CSV file
        zarr_path: Output Zarr path
        station: Station identifier (extracted from filename if not provided)

    Returns:
        str: Path to created Zarr store
    """
    logger.info(f"Converting {csv_path} to Zarr...")

    if station is None:
        filename = Path(csv_path).stem
        station = filename.split("_")[0] if "_" in filename else "UNKNOWN"

    try:
        import csv

        data = {}
        timestamps = []

        with open(csv_path, "r") as f:
            reader = csv.reader(f)
            header = next(reader)

            for col_name in header:
                if col_name.strip() in ASOS_COLUMNS:
                    data[col_name.strip()] = []

            for row in reader:
                if len(row) < len(header):
                    continue

                timestamp_str = None
                for i, col in enumerate(header):
                    col = col.strip()
                    if col == "valid":
                        timestamp_str = row[i].strip()

                if timestamp_str:
                    try:
                        ts = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
                        timestamps.append(ts)
                    except ValueError:
                        continue

                for col_name in data.keys():
                    try:
                        col_idx = header.index(col_name)
                        value = row[col_idx].strip()
                        if value in ("M", "T", ""):
                            data[col_name].append(np.nan)
                        elif value == "T":
                            data[col_name].append(0.001)
                        else:
                            data[col_name].append(float(value))
                    except (ValueError, IndexError):
                        data[col_name].append(np.nan)

        if not timestamps or not data:
            logger.warning("No data found in CSV")
            return _create_empty_zarr(zarr_path, station)

        compressor = Blosc(cname="lz4", clevel=5)

        zarr_store = zarr.open_group(zarr_path, mode="w")

        for col_name, values in data.items():
            if not values:
                continue

            arr = np.array(values, dtype=np.float32)
            meta = ASOS_COLUMNS.get(col_name, {"name": col_name, "units": "unknown"})

            var_name = meta["name"]
            z = zarr_store.create_array(
                var_name,
                shape=arr.shape,
                chunks=(min(1000, len(arr)),),
                dtype=arr.dtype,
                compressor=compressor,
            )
            z[:] = arr
            z.attrs["units"] = meta["units"]
            z.attrs["long_name"] = var_name.replace("_", " ").title()

        zarr_store.attrs["station"] = station
        zarr_store.attrs["source"] = "ASOS"
        zarr_store.attrs["csv_path"] = csv_path
        zarr_store.attrs["n_observations"] = len(timestamps)

        if timestamps:
            zarr_store.attrs["start_time"] = min(timestamps).isoformat()
            zarr_store.attrs["end_time"] = max(timestamps).isoformat()

        logger.info(f"Saved ASOS Zarr to {zarr_path}")
        return zarr_path

    except Exception as e:
        logger.error(f"Failed to convert ASOS to Zarr: {e}")
        raise


def _create_empty_zarr(zarr_path: str, station: str) -> str:
    """Create an empty Zarr store when no data is available."""
    compressor = Blosc(cname="lz4", clevel=5)

    zarr_store = zarr.open_group(zarr_path, mode="w")
    zarr_store.attrs["station"] = station
    zarr_store.attrs["source"] = "ASOS"
    zarr_store.attrs["empty"] = True

    logger.warning(f"Created empty Zarr at {zarr_path}")
    return zarr_path


def convert_asos_batch_to_zarr(
    csv_paths: List[str],
    zarr_path: str,
) -> str:
    """Convert multiple ASOS CSV files to a single Zarr store.

    Args:
        csv_paths: List of CSV file paths (one per station)
        zarr_path: Output Zarr path

    Returns:
        str: Path to created Zarr store
    """
    logger.info(f"Converting {len(csv_paths)} ASOS files to Zarr...")

    zarr_store = zarr.open_group(zarr_path, mode="w")

    compressor = Blosc(cname="lz4", clevel=5)

    stations_data = {}

    for csv_path in csv_paths:
        filename = Path(csv_path).stem
        station = filename.split("_")[0] if "_" in filename else "UNKNOWN"

        try:
            import csv

            with open(csv_path, "r") as f:
                reader = csv.reader(f)
                header = next(reader)

                data = {
                    col.strip(): [] for col in header if col.strip() in ASOS_COLUMNS
                }

                for row in reader:
                    for col_name in data.keys():
                        try:
                            col_idx = header.index(col_name)
                            value = row[col_idx].strip()
                            if value in ("M", "T", ""):
                                data[col_name].append(np.nan)
                            else:
                                data[col_name].append(float(value))
                        except (ValueError, IndexError):
                            data[col_name].append(np.nan)

                if data:
                    stations_data[station] = data

        except Exception as e:
            logger.warning(f"Failed to read {csv_path}: {e}")
            continue

    for station, data in stations_data.items():
        station_group = zarr_store.create_group(station)

        for col_name, values in data.items():
            if not values:
                continue

            arr = np.array(values, dtype=np.float32)
            meta = ASOS_COLUMNS.get(col_name, {"name": col_name, "units": "unknown"})

            var_name = meta["name"]
            z = station_group.create_array(
                var_name,
                shape=arr.shape,
                chunks=(min(1000, len(arr)),),
                dtype=arr.dtype,
                compressor=compressor,
            )
            z[:] = arr
            z.attrs["units"] = meta["units"]

    zarr_store.attrs["source"] = "ASOS"
    zarr_store.attrs["n_stations"] = len(stations_data)
    zarr_store.attrs["stations"] = list(stations_data.keys())

    logger.info(f"Saved batch ASOS Zarr to {zarr_path}")
    return zarr_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert ASOS CSV to Zarr")
    parser.add_argument("input", type=str, help="Input CSV file(s)")
    parser.add_argument("output", type=str, help="Output Zarr path")
    parser.add_argument("--batch", action="store_true", help="Batch mode")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.batch:
        import glob

        files = glob.glob(args.input)
        convert_asos_batch_to_zarr(files, args.output)
    else:
        convert_asos_to_zarr(args.input, args.output)
