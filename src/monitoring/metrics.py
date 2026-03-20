"""
Prometheus metrics for weather data ingestion pipeline.

Tracks:
- Task execution times
- Download success/failure rates
- Data processing throughput
- Queue depths
- Error rates
"""

from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps

# Task execution metrics
task_duration = Histogram(
    'weather_task_duration_seconds',
    'Time spent processing task',
    ['task_name', 'status'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800]
)

task_counter = Counter(
    'weather_task_total',
    'Total number of tasks executed',
    ['task_name', 'status']
)

# Download metrics
download_size_bytes = Histogram(
    'weather_download_size_bytes',
    'Size of downloaded files in bytes',
    ['source'],
    buckets=[1e6, 10e6, 100e6, 500e6, 1e9, 5e9, 10e9]
)

download_duration = Histogram(
    'weather_download_duration_seconds',
    'Time spent downloading files',
    ['source'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)

download_counter = Counter(
    'weather_download_total',
    'Total number of download attempts',
    ['source', 'status']
)

# Processing metrics
files_processed = Counter(
    'weather_files_processed_total',
    'Total number of files processed',
    ['source', 'format']
)

processing_duration = Histogram(
    'weather_processing_duration_seconds',
    'Time spent processing files',
    ['source', 'operation'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)

# Queue metrics
queue_depth = Gauge(
    'weather_queue_depth',
    'Number of tasks waiting in queue',
    ['queue_name']
)

active_workers = Gauge(
    'weather_active_workers',
    'Number of active Celery workers',
)

# Error metrics
error_counter = Counter(
    'weather_errors_total',
    'Total number of errors',
    ['component', 'error_type']
)

# Data quality metrics
qc_flagged_points = Counter(
    'weather_qc_flagged_points_total',
    'Number of data points flagged by QC',
    ['source', 'check_type']
)

qc_pass_rate = Gauge(
    'weather_qc_pass_rate',
    'Percentage of data points passing QC',
    ['source']
)

# Storage metrics
storage_used_bytes = Gauge(
    'weather_storage_used_bytes',
    'Disk space used by weather data',
    ['storage_type']
)

# System info
system_info = Info(
    'weather_system',
    'System information'
)


def track_task_metrics(task_name):
    """
    Decorator to track Celery task metrics.

    Usage:
        @app.task
        @track_task_metrics('ingest_gfs')
        def ingest_gfs_cycle():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 'success'

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'failure'
                error_counter.labels(
                    component=task_name,
                    error_type=type(e).__name__
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                task_duration.labels(
                    task_name=task_name,
                    status=status
                ).observe(duration)
                task_counter.labels(
                    task_name=task_name,
                    status=status
                ).inc()

        return wrapper
    return decorator


def track_download(source):
    """
    Context manager to track download metrics.

    Usage:
        with track_download('gfs'):
            files = download_gfs(...)
    """
    class DownloadTracker:
        def __init__(self, source):
            self.source = source
            self.start_time = None

        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = time.time() - self.start_time
            status = 'failure' if exc_type else 'success'

            download_duration.labels(source=self.source).observe(duration)
            download_counter.labels(
                source=self.source,
                status=status
            ).inc()

            if exc_type:
                error_counter.labels(
                    component=f'download_{self.source}',
                    error_type=exc_type.__name__
                ).inc()

            return False  # Don't suppress exceptions

    return DownloadTracker(source)


def track_processing(source, operation):
    """
    Context manager to track processing metrics.

    Usage:
        with track_processing('gfs', 'grib_to_zarr'):
            convert_grib_to_zarr(...)
    """
    class ProcessingTracker:
        def __init__(self, source, operation):
            self.source = source
            self.operation = operation
            self.start_time = None

        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = time.time() - self.start_time
            processing_duration.labels(
                source=self.source,
                operation=self.operation
            ).observe(duration)

            if not exc_type:
                files_processed.labels(
                    source=self.source,
                    format='zarr'
                ).inc()

            return False

    return ProcessingTracker(source, operation)


def update_queue_metrics(celery_app):
    """
    Update queue depth metrics from Celery inspect.

    Should be called periodically (e.g., every 30 seconds).
    """
    try:
        inspect = celery_app.control.inspect()

        # Get active tasks
        active = inspect.active()
        if active:
            active_count = sum(len(tasks) for tasks in active.values())
            active_workers.set(len(active))

        # Get queue lengths
        reserved = inspect.reserved()
        if reserved:
            for worker, tasks in reserved.items():
                queue_depth.labels(queue_name='celery').set(len(tasks))

    except Exception as e:
        error_counter.labels(
            component='metrics_collector',
            error_type=type(e).__name__
        ).inc()


def record_qc_metrics(source, total_points, flagged_points, check_type):
    """
    Record quality control metrics.

    Args:
        source: Data source (e.g., 'gfs', 'hrrr')
        total_points: Total number of data points checked
        flagged_points: Number of points flagged as bad
        check_type: Type of QC check (e.g., 'temporal', 'spatial')
    """
    qc_flagged_points.labels(
        source=source,
        check_type=check_type
    ).inc(flagged_points)

    if total_points > 0:
        pass_rate = ((total_points - flagged_points) / total_points) * 100
        qc_pass_rate.labels(source=source).set(pass_rate)


def update_storage_metrics(tmp_path='/tmp', s3_enabled=False):
    """
    Update storage usage metrics.

    Args:
        tmp_path: Path to temporary storage
        s3_enabled: Whether S3 storage is enabled
    """
    import shutil

    try:
        # Local /tmp storage
        stat = shutil.disk_usage(tmp_path)
        storage_used_bytes.labels(storage_type='local_tmp').set(stat.used)

        # S3 storage (if enabled)
        if s3_enabled:
            # TODO: Implement S3 usage tracking
            pass

    except Exception as e:
        error_counter.labels(
            component='storage_metrics',
            error_type=type(e).__name__
        ).inc()
