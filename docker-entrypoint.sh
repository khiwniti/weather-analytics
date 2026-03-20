#!/bin/bash
# Entrypoint script for Celery worker with Prometheus metrics

set -e

echo "Starting Prometheus metrics server on port 9091..."
python -c "
from src.monitoring.server import start_metrics_server
import threading
import time

def metrics_server():
    start_metrics_server(port=9091)

# Start metrics server in background thread
thread = threading.Thread(target=metrics_server, daemon=True)
thread.start()
time.sleep(2)  # Give it time to start
print('Metrics server started')
" &

echo "Starting Celery worker..."
exec celery -A src.ingestion.scheduler.tasks worker --loglevel=info
