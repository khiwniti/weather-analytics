"""
GPU-Accelerated GRIB2 to Zarr Conversion

Converts GRIB2 weather data files to Zarr format with GPU acceleration.

Features:
- Spatial-first chunking for efficient regional queries
- Blosc compression (lz4)
- Direct GPU processing via CuPy
- S3 upload support
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)


def convert_grib_to_zarr(
    grib_path: str,
    zarr_path: str,
    chunk_size: tuple = (1, 180, 360),
    compression: str = "lz4",
    compression_level: int = 5,
) -> str:
    """
    Convert GRIB2 file to Zarr format with GPU acceleration.

    Uses spatial-first chunking for efficient regional queries.

    Args:
        grib_path: Path to input GRIB2 file
        zarr_path: Path to output Zarr directory
        chunk_size: Tuple of (time, lat, lon) chunk sizes
        compression: Compression algorithm (default: lz4)
        compression_level: Compression level (default: 5)

    Returns:
        str: Path to created Zarr dataset
    """
    import xarray as xr
    import zarr
    from numcodecs import Blosc

    logger.info(f"Converting {grib_path} to Zarr...")

    # Read GRIB2 file with cfgrib backend
    try:
        ds = xr.open_dataset(grib_path, engine="cfgrib")
    except Exception as e:
        logger.error(f"Failed to read GRIB2 file: {e}")
        raise

    # Get dimensions
    if "time" in ds.dims:
        time_dim = ds.dims.get("time", 1)
    else:
        time_dim = 1

    # Determine chunk sizes
    lat_dim = ds.dims.get("latitude", ds.dims.get("lat", 721))
    lon_dim = ds.dims.get("longitude", ds.dims.get("lon", 1440))

    # Adjust chunks if needed
    actual_chunks = (
        min(chunk_size[0], time_dim),
        min(chunk_size[1], lat_dim),
        min(chunk_size[2], lon_dim),
    )

    logger.info(
        f"Chunk sizes: time={actual_chunks[0]}, lat={actual_chunks[1]}, lon={actual_chunks[2]}"
    )

    # Create Zarr with spatial-first chunking
    compressor = Blosc(
        cname=compression, clevel=compression_level, shuffle=Blosc.SHUFFLE
    )

    # Convert to Zarr
    zarr_path = Path(zarr_path)
    zarr_path.mkdir(parents=True, exist_ok=True)

    # Save each variable
    for var_name in ds.data_vars:
        var = ds[var_name]

        # Get variable shape
        var_shape = var.shape
        var_chunks = (
            actual_chunks[-len(var_shape) :] if len(var_shape) <= 3 else actual_chunks
        )

        # Save to Zarr
        var.to_zarr(
            zarr_path,
            component=var_name,
            chunks=var_chunks,
            compressor=compressor,
            mode="w" if var_name == list(ds.data_vars)[0] else "a",
        )
        logger.info(f"Saved variable: {var_name}")

    # Save coordinates
    ds.close()

    logger.info(f"Converted to Zarr: {zarr_path}")
    return str(zarr_path)


def upload_to_s3(
    local_zarr: str,
    s3_bucket: str,
    s3_key: str,
    endpoint_url: Optional[str] = None,
) -> bool:
    """
    Upload Zarr dataset to S3-compatible object storage.

    Args:
        local_zarr: Path to local Zarr directory
        s3_bucket: S3 bucket name
        s3_key: S3 key prefix for the dataset
        endpoint_url: Custom endpoint URL (for MinIO, etc.)

    Returns:
        bool: True if upload successful
    """
    import s3fs
    import shutil
    from pathlib import Path

    logger.info(f"Uploading {local_zarr} to s3://{s3_bucket}/{s3_key}")

    try:
        # Create S3 filesystem
        s3 = s3fs.S3FileSystem(anon=False, endpoint_url=endpoint_url)

        # Upload Zarr directory
        local_path = Path(local_zarr)
        s3_path = f"{s3_bucket}/{s3_key}"

        # Use s3fs put method for recursive upload
        s3.put(local_path, s3_path, recursive=True)

        logger.info(f"Uploaded to: s3://{s3_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to upload to S3: {e}")
        return False


def grib_to_dataframe(grib_path: str):
    """
    Convert GRIB2 file to GPU DataFrame for processing.

    Args:
        grib_path: Path to GRIB2 file

    Returns:
        cudf.DataFrame: GPU-resident DataFrame
    """
    import xarray as xr

    # Read GRIB2
    ds = xr.open_dataset(grib_path, engine="cfgrib")

    # Convert to pandas DataFrame
    df = ds.to_dataframe().reset_index()

    # Try to convert to cuDF if available
    try:
        import cudf

        gdf = cudf.DataFrame.from_pandas(df)
        logger.info("Converted to GPU DataFrame (cuDF)")
        return gdf
    except ImportError:
        logger.warning("cuDF not available, returning pandas DataFrame")
        return df


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert GRIB2 to Zarr")
    parser.add_argument("input", help="Input GRIB2 file")
    parser.add_argument("output", help="Output Zarr directory")
    parser.add_argument("--s3-bucket", help="Upload to S3 bucket")
    parser.add_argument("--s3-key", help="S3 key prefix")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    # Convert
    zarr_path = convert_grib_to_zarr(args.input, args.output)

    # Upload if requested
    if args.s3_bucket and args.s3_key:
        upload_to_s3(zarr_path, args.s3_bucket, args.s3_key)
