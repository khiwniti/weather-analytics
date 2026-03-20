"""Data Ingestion Pipeline Orchestrator

Unified interface for all data source ingestion.

Features:
- Single entry point for all data sources
- Automatic Zarr path generation
- S3 storage structure management
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_ROOT = "s3://weather-data"


@dataclass
class IngestionResult:
    """Result of a data ingestion operation."""

    source: str
    timestamp: datetime
    zarr_path: str
    success: bool
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class IngestionOrchestrator:
    """Orchestrates data ingestion from multiple sources."""

    def __init__(self, storage_root: str = DEFAULT_STORAGE_ROOT):
        """Initialize the orchestrator.

        Args:
            storage_root: Root path for data storage (local or S3)
        """
        self.storage_root = storage_root
        self.downloaders = {}
        self.processors = {}
        self._register_handlers()

    def _register_handlers(self):
        """Register all data source handlers."""
        from src.ingestion.nwp import gfs_downloader, hrrr_downloader
        from src.ingestion.satellite import goes_downloader, goes_processor
        from src.ingestion.radar import nexrad_downloader, nexrad_processor
        from src.ingestion.ground import asos_downloader, asos_processor

        self.downloaders = {
            "gfs": gfs_downloader.download_gfs,
            "hrrr": hrrr_downloader.download_hrrr,
            "goes": goes_downloader.download_goes,
            "nexrad": nexrad_downloader.download_nexrad,
            "asos": asos_downloader.download_asos,
        }

        self.processors = {
            "gfs": self._process_gfs,
            "hrrr": self._process_hrrr,
            "goes": goes_processor.convert_goes_to_zarr,
            "nexrad": nexrad_processor.convert_nexrad_to_zarr,
            "asos": asos_processor.convert_asos_to_zarr,
        }

    def get_zarr_path(
        self,
        source: str,
        datetime_obj: datetime,
        extra: Optional[str] = None,
    ) -> str:
        """Generate Zarr path for a data source.

        Args:
            source: Data source name (gfs, hrrr, goes, nexrad, asos)
            datetime_obj: Data timestamp
            extra: Extra path component (e.g., station ID)

        Returns:
            str: Zarr path
        """
        year = datetime_obj.year
        month = f"{datetime_obj.month:02d}"
        day = f"{datetime_obj.day:02d}"

        if source == "gfs":
            cycle = f"{datetime_obj.hour:02d}z"
            return f"{self.storage_root}/gfs/{year}/{month}/{day}/{cycle}.zarr"

        elif source == "hrrr":
            cycle = f"{datetime_obj.hour:02d}z"
            return f"{self.storage_root}/hrrr/{year}/{month}/{day}/{cycle}.zarr"

        elif source == "goes":
            satellite = extra or "16"
            domain = "CONUS"
            return (
                f"{self.storage_root}/goes/{satellite}/{year}/{month}/{day}/{domain}/"
            )

        elif source == "nexrad":
            station = extra or "KTLX"
            return f"{self.storage_root}/nexrad/{year}/{month}/{day}/{station}/"

        elif source == "asos":
            return f"{self.storage_root}/asos/{year}/{month}/{day}/hourly.zarr"

        else:
            return f"{self.storage_root}/{source}/{year}/{month}/{day}/"

    def run_ingestion_pipeline(
        self,
        source: str,
        datetime_obj: Optional[datetime] = None,
        **kwargs,
    ) -> IngestionResult:
        """Run the ingestion pipeline for a single data source.

        Args:
            source: Data source name (gfs, hrrr, goes, nexrad, asos)
            datetime_obj: Data timestamp (defaults to current time)
            **kwargs: Additional arguments for downloader/processor

        Returns:
            IngestionResult: Result of the ingestion
        """
        if datetime_obj is None:
            datetime_obj = datetime.utcnow()

        if source not in self.downloaders:
            return IngestionResult(
                source=source,
                timestamp=datetime_obj,
                zarr_path="",
                success=False,
                error=f"Unknown source: {source}",
            )

        zarr_path = self.get_zarr_path(
            source,
            datetime_obj,
            extra=kwargs.get("station") or kwargs.get("satellite"),
        )

        try:
            logger.info(f"Starting ingestion for {source} at {datetime_obj}")

            downloader = self.downloaders[source]
            downloaded_files = downloader(
                **{k: v for k, v in kwargs.items() if k != "processor_args"}
            )

            if not downloaded_files:
                return IngestionResult(
                    source=source,
                    timestamp=datetime_obj,
                    zarr_path=zarr_path,
                    success=False,
                    error="No files downloaded",
                )

            # Run QC before processing
            qc_config_path = "configs/qc/temporal_limits.yaml"
            if os.path.exists(qc_config_path):
                try:
                    import yaml

                    with open(qc_config_path, "r") as f:
                        qc_cfg = yaml.safe_load(f)
                    # Placeholder: In real pipeline, load data into cudf DataFrame and run QC
                    logger.info(
                        f"QC would be executed for {source} using {qc_config_path}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to load QC config: {e}")
            else:
                logger.warning("QC config not found, skipping QC")

            processor = self.processors.get(source)
            if processor:
                if isinstance(downloaded_files, list):
                    if len(downloaded_files) == 1:
                        processor(downloaded_files[0], zarr_path)
                    else:
                        for f in downloaded_files:
                            fname = Path(f).stem
                            processor(f, os.path.join(zarr_path, fname))
                else:
                    processor(downloaded_files, zarr_path)

            logger.info(f"Successfully ingested {source} to {zarr_path}")

            return IngestionResult(
                source=source,
                timestamp=datetime_obj,
                zarr_path=zarr_path,
                success=True,
                metadata={"files": downloaded_files},
            )

        except Exception as e:
            logger.error(f"Failed to ingest {source}: {e}")
            return IngestionResult(
                source=source,
                timestamp=datetime_obj,
                zarr_path=zarr_path,
                success=False,
                error=str(e),
            )

    def ingest_all_sources(
        self,
        datetime_obj: Optional[datetime] = None,
        sources: Optional[List[str]] = None,
    ) -> List[IngestionResult]:
        """Run ingestion for multiple data sources.

        Args:
            datetime_obj: Data timestamp
            sources: List of sources to ingest (default: all)

        Returns:
            List[IngestionResult]: Results for each source
        """
        if sources is None:
            sources = list(self.downloaders.keys())

        results = []
        for source in sources:
            result = self.run_ingestion_pipeline(source, datetime_obj)
            results.append(result)

        return results

    def _process_gfs(self, grib_path: str, zarr_path: str) -> str:
        """Process GFS GRIB2 file to Zarr."""
        try:
            from src.processing.rapids import grib_to_zarr

            return grib_to_zarr.convert_grib_to_zarr(grib_path, zarr_path)
        except ImportError:
            logger.warning("RAPIDS processor not available, using minimal conversion")
            return self._minimal_grib_to_zarr(grib_path, zarr_path)

    def _process_hrrr(self, grib_path: str, zarr_path: str) -> str:
        """Process HRRR GRIB2 file to Zarr."""
        return self._process_gfs(grib_path, zarr_path)

    def _minimal_grib_to_zarr(self, grib_path: str, zarr_path: str) -> str:
        """Minimal GRIB2 to Zarr conversion."""
        import zarr
        from numcodecs import Blosc

        compressor = Blosc(cname="lz4", clevel=5)
        z = zarr.open_group(zarr_path, mode="w")
        z.attrs["source_file"] = grib_path
        z.attrs["processed"] = False
        z.attrs["note"] = "Minimal conversion - RAPIDS required for full processing"

        return zarr_path


def run_ingestion_pipeline(
    source: str,
    datetime_obj: Optional[datetime] = None,
    storage_root: str = DEFAULT_STORAGE_ROOT,
    **kwargs,
) -> IngestionResult:
    """Convenience function to run a single ingestion.

    Args:
        source: Data source name
        datetime_obj: Data timestamp
        storage_root: Storage root path
        **kwargs: Additional arguments

    Returns:
        IngestionResult: Result of the ingestion
    """
    orchestrator = IngestionOrchestrator(storage_root=storage_root)
    return orchestrator.run_ingestion_pipeline(source, datetime_obj, **kwargs)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run data ingestion pipeline")
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        choices=["gfs", "hrrr", "goes", "nexrad", "asos"],
        help="Data source to ingest",
    )
    parser.add_argument(
        "--storage",
        type=str,
        default="/tmp/weather-data",
        help="Storage root path",
    )
    parser.add_argument(
        "--station",
        type=str,
        help="Station ID (for NEXRAD/ASOS)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    orchestrator = IngestionOrchestrator(storage_root=args.storage)
    result = orchestrator.run_ingestion_pipeline(
        source=args.source,
        station=args.station,
    )

    if result.success:
        print(f"Success: {result.zarr_path}")
    else:
        print(f"Failed: {result.error}")
