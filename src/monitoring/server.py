"""
Prometheus metrics HTTP server.

Exposes metrics endpoint for Prometheus scraping.
"""

from prometheus_client import start_http_server, REGISTRY
import logging

logger = logging.getLogger(__name__)

DEFAULT_PORT = 9090


def start_metrics_server(port=DEFAULT_PORT):
    """
    Start Prometheus metrics HTTP server.

    Args:
        port: Port to listen on (default: 9090)
    """
    try:
        start_http_server(port, registry=REGISTRY)
        logger.info(f"Prometheus metrics server started on port {port}")
        logger.info(f"Metrics available at http://localhost:{port}/metrics")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
        raise


if __name__ == '__main__':
    import time
    logging.basicConfig(level=logging.INFO)

    start_metrics_server()
    print("Metrics server running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
