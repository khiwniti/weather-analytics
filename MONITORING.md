# Monitoring Infrastructure

This document describes the monitoring and observability setup for the AI Weather Analytics Platform.

## Architecture

The monitoring stack consists of:

1. **Prometheus** - Time-series metrics collection and alerting
2. **Grafana** - Visual dashboards and data exploration
3. **Redis Exporter** - Exposes Redis/Celery broker metrics
4. **Node Exporter** - System-level metrics (CPU, memory, disk, network)
5. **Custom Python Metrics** - Application-level metrics from the data pipeline

## Components

### 1. Prometheus (Port 9090)

Main metrics collection engine that scrapes metrics from all exporters.

**Access**: http://localhost:9090

**Configuration**: `configs/prometheus.yml`

**Key Features**:
- 15-second scrape interval
- 30-day data retention
- Multiple scrape targets configured

### 2. Grafana (Port 3002)

Visual dashboard platform for exploring and visualizing Prometheus metrics.

**Access**: http://localhost:3002

**Default Login**:
- Username: `admin`
- Password: `admin` (change on first login)

**Pre-configured Dashboards**:

1. **Weather Pipeline Overview** - High-level system health
   - Tasks per minute (success rate)
   - Task success rate gauge
   - Current queue depth
   - Active workers count
   - Task duration trends
   - Quality control pass rates
   - Error rates by component

2. **Data Ingestion Details** - Download and processing metrics
   - Average download duration by source
   - Average file sizes downloaded
   - Download success/failure rates
   - Processing duration by operation
   - Files processed rate
   - Summary table by data source

3. **System Performance** - Infrastructure monitoring
   - CPU usage percentage
   - Memory usage (used vs available)
   - Disk usage (used vs available)
   - Network I/O (RX/TX)
   - Redis memory usage
   - Redis connection count

**Configuration**:
- Datasource: `configs/grafana/provisioning/datasources/prometheus.yml`
- Dashboards: `configs/grafana/provisioning/dashboards/*.json`

### 3. Application Metrics (Port 9091)

Custom Prometheus metrics exposed by the Celery worker via `src/monitoring/server.py`.

**Metrics Collected**:

- **Task Execution**:
  - `weather_task_duration_seconds` - Histogram of task durations
  - `weather_task_total` - Counter of tasks by status (success/failure)

- **Downloads**:
  - `weather_download_size_bytes` - Histogram of download sizes
  - `weather_download_duration_seconds` - Time spent downloading
  - `weather_download_total` - Counter of download attempts

- **Processing**:
  - `weather_files_processed_total` - Counter of processed files
  - `weather_processing_duration_seconds` - Processing time by operation

- **Errors**:
  - `weather_errors_total` - Counter of errors by component and type

- **Quality Control**:
  - `weather_qc_flagged_points_total` - Counter of flagged data points
  - `weather_qc_pass_rate` - Gauge of QC pass percentage

- **Queue Metrics**:
  - `weather_queue_depth` - Number of pending tasks
  - `weather_active_workers` - Number of active Celery workers

- **Storage**:
  - `weather_storage_used_bytes` - Disk space usage

### 4. Redis Exporter (Port 9121)

Monitors the Redis instance used as Celery's broker.

**Key Metrics**:
- `redis_connected_clients` - Number of client connections
- `redis_used_memory_bytes` - Memory usage
- `redis_commands_total` - Total commands executed
- `redis_keyspace_*` - Database size and keys

### 5. Node Exporter (Port 9100)

System-level metrics from the host machine.

**Key Metrics**:
- `node_cpu_seconds_total` - CPU usage by mode
- `node_memory_*` - Memory usage statistics
- `node_disk_*` - Disk I/O and space
- `node_network_*` - Network traffic and errors

## Usage

### Starting the Monitoring Stack

```bash
# Start all services including monitoring
docker-compose up -d

# View logs
docker-compose logs -f prometheus
docker-compose logs -f grafana
docker-compose logs -f celery-worker
```

### Accessing Grafana

Navigate to **http://localhost:3002** and log in:

**First-time setup**:
1. Username: `admin`
2. Password: `admin`
3. You'll be prompted to change the password (recommended but optional)

**Using the Dashboards**:

1. **Main Dashboard** - Click the "Dashboards" icon (4 squares) in the left sidebar
2. **Browse Dashboards** - You'll see 3 pre-configured dashboards:
   - **Weather Pipeline Overview** - Start here for system health
   - **Data Ingestion Details** - Deep dive into download/processing
   - **System Performance** - Infrastructure metrics

3. **Time Range** - Use the time picker (top right) to adjust the view:
   - Last 6 hours (default)
   - Last 24 hours
   - Last 7 days
   - Custom range

4. **Refresh** - Auto-refresh every 30s (configurable in top right)

5. **Panel Actions**:
   - Hover over any panel → Click title → View
   - Click "Edit" to customize queries
   - Click "Share" to get snapshot or embed links

6. **Explore Mode** - Click "Explore" (compass icon) to run ad-hoc queries

**Creating Custom Dashboards**:
1. Click "+" icon → Dashboard
2. Add Panel → Choose visualization type
3. Select "Prometheus" datasource
4. Write PromQL query
5. Configure display options
6. Save dashboard

### Accessing Prometheus

Navigate to http://localhost:9090 and explore:

1. **Graph Tab** - Query and visualize metrics
2. **Alerts Tab** - View active alerts (when configured)
3. **Status → Targets** - Check scrape target health

### Example Prometheus Queries

**Task Success Rate**:
```promql
rate(weather_task_total{status="success"}[5m])
/
rate(weather_task_total[5m])
```

**Average Download Duration**:
```promql
rate(weather_download_duration_seconds_sum[5m])
/
rate(weather_download_duration_seconds_count[5m])
```

**Files Processed Per Minute**:
```promql
rate(weather_files_processed_total[1m]) * 60
```

**Error Rate by Component**:
```promql
rate(weather_errors_total[5m])
```

**Queue Depth**:
```promql
weather_queue_depth
```

**Storage Usage**:
```promql
weather_storage_used_bytes / 1024 / 1024 / 1024  # Convert to GB
```

### Adding Custom Metrics

1. **Define the metric** in `src/monitoring/metrics.py`:

```python
from prometheus_client import Counter

my_metric = Counter(
    'weather_my_metric_total',
    'Description of my metric',
    ['label1', 'label2']
)
```

2. **Instrument your code**:

```python
from ...monitoring.metrics import my_metric

def my_function():
    my_metric.labels(label1='value1', label2='value2').inc()
    # Your code here
```

3. **Metrics are automatically exposed** at http://localhost:9091/metrics

## Scrape Targets

| Target | Port | Job Name | Interval | Purpose |
|--------|------|----------|----------|---------|
| Prometheus | 9090 | prometheus | 15s | Self-monitoring |
| Celery Worker | 9091 | weather-pipeline | 10s | Application metrics |
| Redis Exporter | 9121 | redis | 10s | Broker metrics |
| Node Exporter | 9100 | node | 15s | System metrics |
| Backend API | 3001 | backend-api | 10s | API metrics (future) |

## Monitoring Best Practices

### 1. Metric Naming

Follow Prometheus naming conventions:
- Use `_total` suffix for counters
- Use `_seconds` for durations
- Use `_bytes` for sizes
- Use descriptive base names (e.g., `weather_download_duration_seconds`)

### 2. Labels

Use labels for dimensions:
```python
# Good
download_counter.labels(source='gfs', status='success').inc()

# Avoid high cardinality
# Bad: using timestamp or user ID as label
```

### 3. Metric Types

- **Counter**: Monotonically increasing values (total requests, errors)
- **Gauge**: Values that go up and down (queue depth, temperature)
- **Histogram**: Distribution of values (request duration, file sizes)
- **Summary**: Similar to histogram, but with quantiles

### 4. Decorators and Context Managers

Use the provided helpers for automatic instrumentation:

```python
from ...monitoring.metrics import track_task_metrics, track_download, track_processing

@app.task
@track_task_metrics('my_task_name')
def my_task():
    with track_download('gfs'):
        files = download_gfs()

    for file in files:
        with track_processing('gfs', 'conversion'):
            convert_file(file)
```

## Troubleshooting

### Metrics Not Appearing

1. **Check if metrics server is running**:
   ```bash
   curl http://localhost:9091/metrics
   ```

2. **Check Prometheus targets**:
   - Navigate to http://localhost:9090/targets
   - Ensure all targets are "UP"

3. **Check Docker logs**:
   ```bash
   docker-compose logs celery-worker
   docker-compose logs prometheus
   ```

### High Memory Usage

Prometheus stores metrics in memory. If memory usage is high:

1. **Reduce retention period** in `configs/prometheus.yml`:
   ```yaml
   command:
     - '--storage.tsdb.retention.time=7d'  # Default is 30d
   ```

2. **Reduce scrape frequency**:
   ```yaml
   global:
     scrape_interval: 30s  # Default is 15s
   ```

### Missing Historical Data

Prometheus data is stored in Docker volumes. If containers are removed:

```bash
# Data persists in named volume
docker volume ls | grep prometheus

# To completely reset (WARNING: destroys all metrics history)
docker-compose down -v
```

## Next Steps

1. ✅ **Grafana Integration** - Visual dashboards for metrics (COMPLETE)
2. **Alerting Rules** - Define alert conditions in Prometheus
3. **Alertmanager** - Route alerts to Slack, email, PagerDuty
4. **Centralized Logging** - Add Loki for log aggregation
5. **Distributed Tracing** - Add Jaeger for request tracing

## Ports Reference

| Service | Port | Purpose |
|---------|------|---------|
| Frontend | 80 | Web UI |
| Backend API | 3001 | REST API |
| Grafana | 3002 | Visual dashboards |
| Flower | 5555 | Celery monitoring |
| Redis | 6379 | Celery broker |
| Prometheus | 9090 | Metrics collection UI |
| Celery Metrics | 9091 | Application metrics endpoint |
| Node Exporter | 9100 | System metrics |
| Redis Exporter | 9121 | Redis metrics |
| Redis Exporter | 9121 | Redis metrics |

---

**Status**: ✅ Monitoring infrastructure operational
**Last Updated**: 2026-03-20
