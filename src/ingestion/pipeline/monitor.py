"""Ingestion Pipeline Monitor

Tracks ingestion status, latency, and alerts.

Features:
- Success/failure tracking
- Latency metrics
- Alert on missing data
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)


@dataclass
class IngestionMetric:
    """Single ingestion metric."""

    source: str
    timestamp: datetime
    success: bool
    latency_seconds: float
    zarr_path: str
    error: Optional[str] = None


@dataclass
class SourceStatus:
    """Status tracking for a single data source."""

    source: str
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    total_ingestions: int = 0
    total_successes: int = 0
    total_failures: int = 0
    avg_latency_seconds: float = 0.0
    recent_errors: List[str] = field(default_factory=list)


class IngestionMonitor:
    """Monitors data ingestion pipeline health."""

    def __init__(self, alert_threshold_failures: int = 3):
        """Initialize the monitor.

        Args:
            alert_threshold_failures: Number of consecutive failures to trigger alert
        """
        self.alert_threshold = alert_threshold_failures
        self.sources: Dict[str, SourceStatus] = {}
        self.metrics: List[IngestionMetric] = []
        self.max_metrics_history = 1000

    def record_ingestion(
        self,
        source: str,
        success: bool,
        latency_seconds: float,
        zarr_path: str,
        error: Optional[str] = None,
    ) -> Optional[str]:
        """Record an ingestion event.

        Args:
            source: Data source name
            success: Whether ingestion succeeded
            latency_seconds: Time taken for ingestion
            zarr_path: Path where data was stored
            error: Error message if failed

        Returns:
            Optional[str]: Alert message if threshold exceeded
        """
        now = datetime.utcnow()

        metric = IngestionMetric(
            source=source,
            timestamp=now,
            success=success,
            latency_seconds=latency_seconds,
            zarr_path=zarr_path,
            error=error,
        )
        self.metrics.append(metric)

        if len(self.metrics) > self.max_metrics_history:
            self.metrics = self.metrics[-self.max_metrics_history :]

        if source not in self.sources:
            self.sources[source] = SourceStatus(source=source)

        status = self.sources[source]
        status.total_ingestions += 1

        if success:
            status.last_success = now
            status.consecutive_failures = 0
            status.total_successes += 1
            status.avg_latency_seconds = (
                status.avg_latency_seconds * (status.total_successes - 1)
                + latency_seconds
            ) / status.total_successes
            logger.info(
                f"[{source}] Ingestion succeeded - latency: {latency_seconds:.1f}s"
            )
        else:
            status.last_failure = now
            status.consecutive_failures += 1
            status.total_failures += 1
            if error:
                status.recent_errors.append(error)
                if len(status.recent_errors) > 10:
                    status.recent_errors = status.recent_errors[-10:]

            logger.error(f"[{source}] Ingestion failed: {error}")

        if status.consecutive_failures >= self.alert_threshold:
            return self._generate_alert(source, status)

        return None

    def _generate_alert(self, source: str, status: SourceStatus) -> str:
        """Generate an alert message for a failing source.

        Args:
            source: Data source name
            status: Source status

        Returns:
            str: Alert message
        """
        alert = (
            f"ALERT: {source} has failed {status.consecutive_failures} consecutive times. "
            f"Last error: {status.recent_errors[-1] if status.recent_errors else 'Unknown'}. "
            f"Last success: {status.last_success or 'Never'}."
        )
        logger.warning(alert)
        return alert

    def get_status(self, source: str) -> Optional[SourceStatus]:
        """Get status for a specific source.

        Args:
            source: Data source name

        Returns:
            Optional[SourceStatus]: Source status or None if not found
        """
        return self.sources.get(source)

    def get_all_status(self) -> Dict[str, SourceStatus]:
        """Get status for all sources.

        Returns:
            Dict[str, SourceStatus]: All source statuses
        """
        return self.sources.copy()

    def check_missing_data(
        self,
        source: str,
        expected_interval_minutes: int,
    ) -> Optional[str]:
        """Check if data is missing for a source.

        Args:
            source: Data source name
            expected_interval_minutes: Expected data interval in minutes

        Returns:
            Optional[str]: Alert message if data is missing
        """
        if source not in self.sources:
            return f"WARNING: No data received for {source}"

        status = self.sources[source]
        if status.last_success is None:
            return f"WARNING: No successful ingestion for {source}"

        time_since_success = datetime.utcnow() - status.last_success
        threshold = timedelta(minutes=expected_interval_minutes * 2)

        if time_since_success > threshold:
            return (
                f"WARNING: {source} data is missing. "
                f"Last successful ingestion: {status.last_success} "
                f"({time_since_success.total_seconds() / 60:.1f} minutes ago)"
            )

        return None

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all ingestion activity.

        Returns:
            Dict[str, Any]: Summary statistics
        """
        total_ingestions = sum(s.total_ingestions for s in self.sources.values())
        total_successes = sum(s.total_successes for s in self.sources.values())
        total_failures = sum(s.total_failures for s in self.sources.values())

        success_rate = total_successes / total_ingestions if total_ingestions > 0 else 0

        return {
            "total_ingestions": total_ingestions,
            "total_successes": total_successes,
            "total_failures": total_failures,
            "success_rate": success_rate,
            "sources": {
                source: {
                    "last_success": status.last_success.isoformat()
                    if status.last_success
                    else None,
                    "last_failure": status.last_failure.isoformat()
                    if status.last_failure
                    else None,
                    "consecutive_failures": status.consecutive_failures,
                    "success_rate": (
                        status.total_successes / status.total_ingestions
                        if status.total_ingestions > 0
                        else 0
                    ),
                    "avg_latency_seconds": status.avg_latency_seconds,
                }
                for source, status in self.sources.items()
            },
        }

    def save_state(self, filepath: str):
        """Save monitor state to a file.

        Args:
            filepath: Path to save state
        """
        state = {
            "sources": {
                source: {
                    "last_success": status.last_success.isoformat()
                    if status.last_success
                    else None,
                    "last_failure": status.last_failure.isoformat()
                    if status.last_failure
                    else None,
                    "consecutive_failures": status.consecutive_failures,
                    "total_ingestions": status.total_ingestions,
                    "total_successes": status.total_successes,
                    "total_failures": status.total_failures,
                    "avg_latency_seconds": status.avg_latency_seconds,
                    "recent_errors": status.recent_errors,
                }
                for source, status in self.sources.items()
            },
            "saved_at": datetime.utcnow().isoformat(),
        }

        with open(filepath, "w") as f:
            json.dump(state, f, indent=2)

        logger.info(f"Saved monitor state to {filepath}")

    def load_state(self, filepath: str):
        """Load monitor state from a file.

        Args:
            filepath: Path to load state from
        """
        if not os.path.exists(filepath):
            logger.warning(f"State file not found: {filepath}")
            return

        with open(filepath, "r") as f:
            state = json.load(f)

        for source, data in state.get("sources", {}).items():
            self.sources[source] = SourceStatus(
                source=source,
                last_success=datetime.fromisoformat(data["last_success"])
                if data.get("last_success")
                else None,
                last_failure=datetime.fromisoformat(data["last_failure"])
                if data.get("last_failure")
                else None,
                consecutive_failures=data.get("consecutive_failures", 0),
                total_ingestions=data.get("total_ingestions", 0),
                total_successes=data.get("total_successes", 0),
                total_failures=data.get("total_failures", 0),
                avg_latency_seconds=data.get("avg_latency_seconds", 0.0),
                recent_errors=data.get("recent_errors", []),
            )

        logger.info(f"Loaded monitor state from {filepath}")


if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser(description="Test ingestion monitor")
    parser.add_argument("--state-file", type=str, default="/tmp/ingestion_monitor.json")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    monitor = IngestionMonitor()

    monitor.record_ingestion("gfs", True, 45.2, "/data/gfs/2024/03/19/00z.zarr")
    monitor.record_ingestion("hrrr", True, 12.3, "/data/hrrr/2024/03/19/00z.zarr")
    monitor.record_ingestion(
        "goes", False, 5.0, "/data/goes/16/", error="S3 connection timeout"
    )
    monitor.record_ingestion(
        "goes", False, 3.0, "/data/goes/16/", error="S3 connection timeout"
    )
    monitor.record_ingestion(
        "goes", False, 2.0, "/data/goes/16/", error="S3 connection timeout"
    )

    print("\nStatus Summary:")
    print(json.dumps(monitor.get_summary(), indent=2, default=str))

    monitor.save_state(args.state_file)
