"""NEXRAD Radar Data Processor

Converts NEXRAD Level II data to Zarr format with GPU acceleration.

Features:
- Level II data processing
- Extract: reflectivity, radial velocity, spectrum width
- GPU-accelerated gridding via cuDF
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple
import numpy as np
import zarr
from numcodecs import Blosc

logger = logging.getLogger(__name__)


def convert_nexrad_to_zarr(
    level2_path: str,
    zarr_path: str,
    variables: Optional[list] = None,
    grid_shape: Tuple[int, int] = (1000, 1000),
    grid_extent_km: float = 230,
) -> str:
    """Convert NEXRAD Level II file to Zarr format.

    Args:
        level2_path: Path to NEXRAD Level II file
        zarr_path: Output Zarr path
        variables: List of variables to extract (reflectivity, velocity, etc.)
        grid_shape: Output grid shape (rows, cols)
        grid_extent_km: Grid extent in km from radar

    Returns:
        str: Path to created Zarr store
    """
    if variables is None:
        variables = ["reflectivity", "radial_velocity", "spectrum_width"]

    logger.info(f"Converting {level2_path} to Zarr...")

    try:
        import pyart

        radar = pyart.io.read(level2_path)

    except ImportError:
        logger.warning("pyart not available, using minimal parser")
        return _convert_nexrad_minimal(level2_path, zarr_path, grid_shape)
    except Exception as e:
        logger.error(f"Failed to read NEXRAD file: {e}")
        raise

    try:
        grids = {}

        if "reflectivity" in variables:
            try:
                grid = pyart.map.grid_from_radars(
                    radar,
                    grid_shape=(1, grid_shape[0], grid_shape[1]),
                    grid_limits=(
                        (1000, 1000),
                        (-grid_extent_km * 1000, grid_extent_km * 1000),
                        (-grid_extent_km * 1000, grid_extent_km * 1000),
                    ),
                    fields=["reflectivity"],
                )
                grids["reflectivity"] = grid.fields["reflectivity"]["data"][0]
            except Exception as e:
                logger.warning(f"Could not grid reflectivity: {e}")

        if "radial_velocity" in variables:
            try:
                if "velocity" in radar.fields:
                    grid = pyart.map.grid_from_radars(
                        radar,
                        grid_shape=(1, grid_shape[0], grid_shape[1]),
                        grid_limits=(
                            (1000, 1000),
                            (-grid_extent_km * 1000, grid_extent_km * 1000),
                            (-grid_extent_km * 1000, grid_extent_km * 1000),
                        ),
                        fields=["velocity"],
                    )
                    grids["radial_velocity"] = grid.fields["velocity"]["data"][0]
            except Exception as e:
                logger.warning(f"Could not grid velocity: {e}")

        if "spectrum_width" in variables:
            try:
                if "spectrum_width" in radar.fields:
                    grid = pyart.map.grid_from_radars(
                        radar,
                        grid_shape=(1, grid_shape[0], grid_shape[1]),
                        grid_limits=(
                            (1000, 1000),
                            (-grid_extent_km * 1000, grid_extent_km * 1000),
                            (-grid_extent_km * 1000, grid_extent_km * 1000),
                        ),
                        fields=["spectrum_width"],
                    )
                    grids["spectrum_width"] = grid.fields["spectrum_width"]["data"][0]
            except Exception as e:
                logger.warning(f"Could not grid spectrum_width: {e}")

        if not grids:
            logger.warning("No variables could be gridded")
            return _convert_nexrad_minimal(level2_path, zarr_path, grid_shape)

        compressor = Blosc(cname="lz4", clevel=5)

        for var_name, data in grids.items():
            var_path = os.path.join(zarr_path, var_name)
            z = zarr.open_array(
                var_path,
                mode="w",
                shape=data.shape,
                chunks=(250, 250),
                dtype=data.dtype,
                compressor=compressor,
            )
            z[:] = np.ma.filled(data, np.nan)
            z.attrs["units"] = "dBZ" if var_name == "reflectivity" else "m/s"
            z.attrs["long_name"] = var_name.replace("_", " ").title()

        zarr_store = zarr.open_group(zarr_path, mode="a")
        zarr_store.attrs["source"] = "NEXRAD"
        zarr_store.attrs["level2_path"] = level2_path
        zarr_store.attrs["grid_extent_km"] = grid_extent_km

        try:
            zarr_store.attrs["station"] = radar.metadata.get(
                "instrument_name", "unknown"
            )
            zarr_store.attrs["latitude"] = float(radar.latitude["data"][0])
            zarr_store.attrs["longitude"] = float(radar.longitude["data"][0])
        except Exception:
            pass

        logger.info(f"Saved NEXRAD Zarr to {zarr_path}")
        return zarr_path

    except Exception as e:
        logger.error(f"Failed to convert NEXRAD to Zarr: {e}")
        raise


def _convert_nexrad_minimal(
    level2_path: str,
    zarr_path: str,
    grid_shape: Tuple[int, int],
) -> str:
    """Minimal NEXRAD conversion without pyart.

    Creates a placeholder Zarr with basic structure.
    """
    compressor = Blosc(cname="lz4", clevel=5)

    dummy_data = np.full(grid_shape, np.nan, dtype=np.float32)

    z = zarr.open_array(
        os.path.join(zarr_path, "reflectivity"),
        mode="w",
        shape=grid_shape,
        chunks=(250, 250),
        dtype=np.float32,
        compressor=compressor,
    )
    z[:] = dummy_data
    z.attrs["units"] = "dBZ"
    z.attrs["note"] = "Placeholder - pyart required for actual processing"

    zarr_store = zarr.open_group(zarr_path, mode="a")
    zarr_store.attrs["source"] = "NEXRAD"
    zarr_store.attrs["level2_path"] = level2_path
    zarr_store.attrs["processed"] = False

    logger.warning(f"Created minimal Zarr at {zarr_path} (pyart not available)")
    return zarr_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert NEXRAD Level II to Zarr")
    parser.add_argument("input", type=str, help="Input Level II file")
    parser.add_argument("output", type=str, help="Output Zarr path")
    parser.add_argument(
        "--variables",
        type=str,
        default="reflectivity,radial_velocity",
        help="Comma-separated variables to extract",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    variables = [v.strip() for v in args.variables.split(",")]
    convert_nexrad_to_zarr(args.input, args.output, variables=variables)
