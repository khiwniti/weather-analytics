"""
Scheduler Configuration

Redis broker settings and task retry configuration.
"""

# Redis broker URL
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"

# Task settings
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True

# Retry settings
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_DEFAULT_RETRY_DELAY = 300  # 5 minutes
CELERY_TASK_MAX_RETRIES = 3

# Worker settings
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100

# Beat schedule (for periodic tasks)
CELERY_BEAT_SCHEDULE = {
    # GFS cycles at expected availability times
    "gfs-00z": {
        "task": "src.ingestion.scheduler.tasks.ingest_gfs_cycle",
        "schedule": 21600.0,  # every 6 hours
        "args": ("00",),
    },
    "gfs-06z": {
        "task": "src.ingestion.scheduler.tasks.ingest_gfs_cycle",
        "schedule": 21600.0,
        "args": ("06",),
    },
    "gfs-12z": {
        "task": "src.ingestion.scheduler.tasks.ingest_gfs_cycle",
        "schedule": 21600.0,
        "args": ("12",),
    },
    "gfs-18z": {
        "task": "src.ingestion.scheduler.tasks.ingest_gfs_cycle",
        "schedule": 21600.0,
        "args": ("18",),
    },
    # HRRR hourly
    "hrrr-hourly": {
        "task": "src.ingestion.scheduler.tasks.ingest_hrrr_cycle",
        "schedule": 3600.0,  # every hour
        "args": None,  # uses current hour
    },
}
