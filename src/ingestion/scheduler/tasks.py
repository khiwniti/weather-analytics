"""
Celery Tasks for Weather Data Ingestion

Scheduled tasks for automated downloads of GFS, HRRR, and other data sources.
"""

import logging
from datetime import datetime

from celery import Celery

logger = logging.getLogger(__name__)

# Create Celery app
app = Celery("weather_ingest")

# Configure Celery
app.conf.update(
    broker_url="redis://localhost:6379/0",
    result_backend="redis://localhost:6379/0",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=300,  # 5 minutes
    task_max_retries=3,
)


@app.task(bind=True, max_retries=3)
def ingest_gfs_cycle(self, cycle: str = None):
    """
    Download and process a GFS forecast cycle.

    Triggers download of all forecast hours for a GFS cycle,
    converts to Zarr, and uploads to S3.

    Args:
        cycle: Cycle hour (00, 06, 12, 18). Defaults to current cycle.
    """
    from ..nwp.gfs_downloader import download_gfs
    from ...processing.rapids.grib_to_zarr import convert_grib_to_zarr, upload_to_s3
    import os

    if cycle is None:
        # Get current cycle
        hour = datetime.utcnow().hour
        if hour < 5:
            cycle = "00"
        elif hour < 11:
            cycle = "06"
        elif hour < 17:
            cycle = "12"
        else:
            cycle = "18"

    logger.info(f"Starting GFS {cycle}Z cycle ingestion")

    try:
        # Download GFS data
        output_dir = f"/tmp/gfs/{datetime.utcnow().strftime('%Y%m%d')}/{cycle}"
        files = download_gfs(
            cycle, forecast_hours=list(range(385)), output_dir=output_dir
        )

        logger.info(f"Downloaded {len(files)} GFS files")

        # Convert each file to Zarr
        for grib_file in files:
            zarr_path = grib_file.replace(".grib2", ".zarr")
            convert_grib_to_zarr(grib_file, zarr_path)

            # Upload to S3 if configured
            s3_bucket = os.getenv("S3_WEATHER_BUCKET")
            if s3_bucket:
                s3_prefix = f"gfs/{datetime.utcnow().strftime('%Y/%m/%d')}/{cycle}"
                upload_to_s3(zarr_path, s3_bucket, s3_prefix)
                logger.info(f"Uploaded {zarr_path} to s3://{s3_bucket}/{s3_prefix}")

        logger.info(f"GFS {cycle}Z cycle complete")
        return {"cycle": cycle, "files_processed": len(files)}

    except Exception as e:
        logger.error(f"GFS ingestion failed: {e}")
        raise self.retry(exc=e)


@app.task(bind=True, max_retries=3)
def ingest_hrrr_cycle(self, cycle: str = None):
    """
    Download and process an HRRR forecast cycle.

    Triggers download of all forecast hours for an HRRR cycle,
    converts to Zarr, and uploads to S3.

    Args:
        cycle: Cycle hour (00-23). Defaults to current hour.
    """
    from ..nwp.hrrr_downloader import download_hrrr
    from ...processing.rapids.grib_to_zarr import convert_grib_to_zarr
    import os

    if cycle is None:
        cycle = f"{datetime.utcnow().hour:02d}"

    logger.info(f"Starting HRRR {cycle}Z cycle ingestion")

    try:
        # Download HRRR data
        output_dir = f"/tmp/hrrr/{datetime.utcnow().strftime('%Y%m%d')}/{cycle}"
        files = download_hrrr(
            cycle, forecast_hours=list(range(19)), output_dir=output_dir
        )

        logger.info(f"Downloaded {len(files)} HRRR files")

        # Convert to Zarr
        for grib_file in files:
            zarr_path = grib_file.replace(".grib2", ".zarr")
            convert_grib_to_zarr(grib_file, zarr_path)

        logger.info(f"HRRR {cycle}Z cycle complete")
        return {"cycle": cycle, "files_processed": len(files)}

    except Exception as e:
        logger.error(f"HRRR ingestion failed: {e}")
        raise self.retry(exc=e)


@app.task
def ingest_all_sources():
    """
    Trigger ingestion of all active data sources.

    Chains GFS and HRRR ingestion tasks.
    """
    from celery import chain

    # Chain tasks
    workflow = chain(
        ingest_gfs_cycle.s(),
        ingest_hrrr_cycle.s(),
    )

    return workflow.apply_async()


if __name__ == "__main__":
    # Run tasks manually for testing
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        task_name = sys.argv[1]
        if task_name == "gfs":
            ingest_gfs_cycle()
        elif task_name == "hrrr":
            ingest_hrrr_cycle()
        elif task_name == "all":
            ingest_all_sources()
    else:
        print("Usage: python tasks.py [gfs|hrrr|all]")
