"""
Scheduled Data Ingestion System

Celery-based task scheduling for automated weather data downloads.
"""

from .tasks import ingest_gfs_cycle, ingest_hrrr_cycle

__all__ = [
    "ingest_gfs_cycle",
    "ingest_hrrr_cycle",
]
