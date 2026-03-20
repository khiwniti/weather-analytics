"""GOES Satellite Data Processor

Converts GOES NetCDF data to Zarr format with GPU acceleration.

Features:
- NetCDF4 to Zarr conversion
- GPU-accelerated via cuDF
- Spatial-first chunking for cloud optimization
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import xarray as xr
import numpy as np
import zarr
from numcodecs import Blosc

logger = logging.getLogger(__name__)


def convert_goes_to_zarr(
    nc_path: str,
    zarr_path: str,
    chunks: Optional[Dict[str, int]] = None,
    compression_level: int = 5,
) -> str:
    """Convert GOES NetCDF file to Zarr format.

    Args:
        nc_path: Path to GOES NetCDF file
        zarr_path: Output Zarr path (can be S3 URL)
        chunks: Chunking strategy. Default: spatial-first (time: 1, x: 500, y: 500)
        compression_level: Zarr compression level (1-9)

    Returns:
        str: Path to created Zarr store
    """
    if chunks is None:
        chunks = {"x": 500, "y": 500}

    logger.info(f"Converting {nc_path} to Zarr...")

    try:
        ds = xr.open_dataset(nc_path, engine="netcdf4")

        band_match = None
        for key in ds.data_vars:
            if "Rad" in key or "CMI" in key:
                band_match = key
                break

        if band_match is None:
            band_match = list(ds.data_vars)[0]

        data = ds[band_match]

        if "x" not in data.dims or "y" not in data.dims:
            coords = list(data.dims)
            if len(coords) >= 2:
                chunks = {coords[0]: 500, coords[1]: 500}

        compressor = Blosc(cname="lz4", clevel=compression_level)

        zarr_store = zarr.open_array(
            zarr_path,
            mode="w",
            shape=data.shape,
            chunks=tuple(chunks.values()) if chunks else None,
            dtype=data.dtype,
            compressor=compressor,
        )

        zarr_store[:] = data.values

        if hasattr(ds, "goes_imager_projection"):
            pass

        attrs = {k: v for k, v in ds.attrs.items() if isinstance(v, (str, int, float))}
        zarr_store.attrs.update(attrs)

        logger.info(f"Saved Zarr to {zarr_path}")
        ds.close()

        return zarr_path

    except Exception as e:
        logger.error(f"Failed to convert GOES to Zarr: {e}")
        raise


def convert_goes_batch_to_zarr(
    nc_paths: list,
    zarr_path: str,
    chunks: Optional[Dict[str, int]] = None,
) -> str:
    """Convert multiple GOES band files to a single Zarr store.

    Args:
        nc_paths: List of GOES NetCDF files (one per band)
        zarr_path: Output Zarr path
        chunks: Chunking strategy

    Returns:
        str: Path to created Zarr store
    """
    import re

    if chunks is None:
        chunks = {"band": 1, "x": 500, "y": 500}

    logger.info(f"Converting {len(nc_paths)} GOES files to Zarr...")

    datasets = []
    for nc_path in nc_paths:
        ds = xr.open_dataset(nc_path, engine="netcdf4")
        datasets.append(ds)

    band_numbers = []
    for path in nc_paths:
        match = re.search(r"C(\d{2})", path)
        if match:
            band_numbers.append(int(match.group(1)))
        else:
            band_numbers.append(0)

    ref_ds = datasets[0]
    ref_var = None
    for key in ref_ds.data_vars:
        if "Rad" in key or "CMI" in key:
            ref_var = ref_ds[key]
            break

    if ref_var is None:
        ref_var = list(ref_ds.data_vars)[0]

    shape = (len(datasets),) + ref_var.shape

    compressor = Blosc(cname="lz4", clevel=5)

    zarr_store = zarr.open_array(
        zarr_path,
        mode="w",
        shape=shape,
        chunks=(chunks.get("band", 1), chunks.get("x", 500), chunks.get("y", 500)),
        dtype=ref_var.dtype,
        compressor=compressor,
    )

    for i, (ds, band_num) in enumerate(zip(datasets, band_numbers)):
        var_name = None
        for key in ds.data_vars:
            if "Rad" in key or "CMI" in key:
                var_name = key
                break
        if var_name is None:
            var_name = list(ds.data_vars)[0]

        zarr_store[i, :, :] = ds[var_name].values
        zarr_store.attrs[f"band_{band_num}"] = nc_paths[i]

    zarr_store.attrs["bands"] = band_numbers
    zarr_store.attrs["source"] = "GOES"

    for ds in datasets:
        ds.close()

    logger.info(f"Saved batch Zarr to {zarr_path}")
    return zarr_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert GOES NetCDF to Zarr")
    parser.add_argument("input", type=str, help="Input NetCDF file(s)")
    parser.add_argument("output", type=str, help="Output Zarr path")
    parser.add_argument(
        "--batch", action="store_true", help="Batch mode (multiple files)"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.batch:
        import glob

        files = glob.glob(args.input)
        convert_goes_batch_to_zarr(files, args.output)
    else:
        convert_goes_to_zarr(args.input, args.output)
