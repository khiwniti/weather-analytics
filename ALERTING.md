# Alerting Rules Guide

This document describes the Prometheus alerting rules configured for the AI Weather Analytics Platform.

## Overview

The platform has **28 alerting rules** across 2 categories:
- **Pipeline Alerts** (15 rules) - Data ingestion and processing
- **Infrastructure Alerts** (13 rules) - System resources and services

Alerts are evaluated every 30 seconds and trigger based on configurable thresholds.

## Alert Severity Levels

- **Warning** ⚠️ - Requires attention but not urgent (10-15 min before action)
- **Critical** 🚨 - Immediate action required (system degraded or failing)

## Pipeline Alerts

### Task Alerts

| Alert | Severity | Threshold | Duration | Description |
|-------|----------|-----------|----------|-------------|
| `HighTaskFailureRate` | Warning | >10% | 5m | Tasks failing at elevated rate |
| `CriticalTaskFailureRate` | Critical | >50% | 2m | Majority of tasks failing |
| `NoTasksExecuting` | Warning | 0 tasks | 15m | No tasks executed recently |
| `SlowTaskExecution` | Warning | >30 min avg | 15m | Tasks taking longer than normal |

**Example**: If GFS ingestion tasks fail 15% of the time for 5 minutes, you'll get a warning alert.

### Worker Alerts

| Alert | Severity | Threshold | Duration | Description |
|-------|----------|-----------|----------|-------------|
| `NoActiveWorkers` | Critical | 0 workers | 5m | No Celery workers running |
| `LowWorkerCount` | Warning | <2 workers | 10m | Insufficient worker capacity |

**Action**: Scale up workers or restart Celery service.

### Queue Alerts

| Alert | Severity | Threshold | Duration | Description |
|-------|----------|-----------|----------|-------------|
| `HighQueueDepth` | Warning | >100 tasks | 10m | Tasks backing up in queue |
| `CriticalQueueDepth` | Critical | >500 tasks | 5m | Severe task backlog |

**Action**: Add more workers or investigate stuck tasks.

### Download Alerts

| Alert | Severity | Threshold | Duration | Description |
|-------|----------|-----------|----------|-------------|
| `HighDownloadFailureRate` | Warning | >20% | 5m | Many downloads failing |
| `SlowDownloads` | Warning | >300s avg | 10m | Downloads taking too long |

**Action**: Check network connectivity, verify NOAA service status, check disk space.

### Processing Alerts

| Alert | Severity | Threshold | Duration | Description |
|-------|----------|-----------|----------|-------------|
| `SlowProcessing` | Warning | >600s avg | 10m | GRIB→Zarr conversion slow |

**Action**: Check CPU/GPU utilization, verify RAPIDS is working, check disk I/O.

### Quality Control Alerts

| Alert | Severity | Threshold | Duration | Description |
|-------|----------|-----------|----------|-------------|
| `LowQCPassRate` | Warning | <80% | 15m | Data quality degrading |
| `CriticalQCPassRate` | Critical | <50% | 5m | Severe data quality issues |

**Action**: Investigate data source, check for corrupted files, review QC thresholds.

### Error Alerts

| Alert | Severity | Threshold | Duration | Description |
|-------|----------|-----------|----------|-------------|
| `HighErrorRate` | Warning | >1 error/s | 5m | Elevated error rate |
| `CriticalErrorRate` | Critical | >5 errors/s | 2m | Very high error rate |

**Action**: Check logs for error details, investigate failing component.

## Infrastructure Alerts

### CPU Alerts

| Alert | Severity | Threshold | Duration | Description |
|-------|----------|-----------|----------|-------------|
| `HighCPUUsage` | Warning | >80% | 10m | CPU usage high |
| `CriticalCPUUsage` | Critical | >95% | 5m | CPU nearly maxed out |

**Action**: Scale horizontally, optimize code, identify resource-intensive processes.

### Memory Alerts

| Alert | Severity | Threshold | Duration | Description |
|-------|----------|-----------|----------|-------------|
| `HighMemoryUsage` | Warning | >80% | 10m | Memory usage high |
| `CriticalMemoryUsage` | Critical | >95% | 5m | Memory nearly exhausted |

**Action**: Increase memory allocation, fix memory leaks, restart services.

### Disk Alerts

| Alert | Severity | Threshold | Duration | Description |
|-------|----------|-----------|----------|-------------|
| `HighDiskUsage` | Warning | >80% | 10m | Disk filling up |
| `CriticalDiskUsage` | Critical | >95% | 5m | Disk nearly full |
| `DiskWillFillIn24Hours` | Warning | Linear projection | 5m | Disk will fill soon |
| `HighStorageUsage` | Warning | >100GB | 10m | Weather data storage high |

**Action**: Run retention cleanup, delete old files, expand disk, enable S3 archival.

### Network Alerts

| Alert | Severity | Threshold | Duration | Description |
|-------|----------|-----------|----------|-------------|
| `HighNetworkErrors` | Warning | >10 errors/s | 5m | Network errors detected |

**Action**: Check network hardware, investigate connectivity issues.

### Redis Alerts

| Alert | Severity | Threshold | Duration | Description |
|-------|----------|-----------|----------|-------------|
| `RedisHighMemory` | Warning | >80% | 10m | Redis memory high |
| `RedisHighConnections` | Warning | >100 | 10m | Too many connections |
| `RedisDown` | Critical | Service down | 1m | Redis unavailable |

**Action**: Increase Redis memory limit, fix connection leaks, restart Redis.

### Service Health Alerts

| Alert | Severity | Threshold | Duration | Description |
|-------|----------|-----------|----------|-------------|
| `PrometheusDown` | Critical | Service down | 5m | Prometheus unavailable |
| `ExporterDown` | Warning | Service down | 5m | Exporter unavailable |

**Action**: Restart failed service, check Docker container logs.

## Viewing Alerts

### In Prometheus

Navigate to **http://localhost:9090/alerts** to see:
- **Inactive** - Alert rule exists but not triggered
- **Pending** - Condition met but duration not reached
- **Firing** - Alert is active

### In Grafana

Alerts appear in dashboards as:
- Red/orange panel backgrounds when thresholds exceeded
- Annotation markers on time-series graphs

## Alert Routing (Future)

To route alerts to external systems, configure **Alertmanager** in `configs/prometheus.yml`:

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

Then configure Alertmanager routes to:
- **Slack** - #alerts channel
- **Email** - ops@example.com
- **PagerDuty** - For critical alerts
- **Webhook** - Custom integrations

## Silencing Alerts

To temporarily silence an alert in Prometheus:

1. Go to **http://localhost:9090/alerts**
2. Click "Silence" next to the firing alert
3. Set duration and reason
4. Alert will be muted but still evaluated

## Customizing Alerts

### Adjusting Thresholds

Edit alert files in `configs/prometheus/alerts/`:

```yaml
- alert: HighCPUUsage
  expr: |
    100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
                                                                                       # ↑ Change threshold
  for: 10m  # ← Change duration
```

### Adding New Alerts

Add new rules to appropriate file:

```yaml
- alert: MyCustomAlert
  expr: my_metric > 100
  for: 5m
  labels:
    severity: warning
    component: my-component
  annotations:
    summary: "Short description"
    description: "Detailed description with {{ $value }} and {{ $labels.label_name }}"
```

### Reload Configuration

After editing alert rules:

```bash
# Restart Prometheus to load new rules
docker-compose restart prometheus

# Or send reload signal (if reload enabled)
curl -X POST http://localhost:9090/-/reload
```

## Testing Alerts

### 1. Simulate High Task Failure

```python
# Artificially fail some tasks
from src.ingestion.scheduler.tasks import ingest_gfs_cycle

# Run with invalid parameters to trigger failures
for i in range(20):
    try:
        ingest_gfs_cycle.apply_async(kwargs={'cycle': 'invalid'})
    except:
        pass
```

### 2. Simulate High Queue Depth

```python
# Queue many tasks
from celery import group
from src.ingestion.scheduler.tasks import ingest_gfs_cycle

job = group([ingest_gfs_cycle.s() for _ in range(200)])
result = job.apply_async()
```

### 3. Simulate Resource Pressure

```bash
# Create CPU load
stress-ng --cpu 4 --timeout 300s

# Fill disk
dd if=/dev/zero of=/tmp/bigfile bs=1M count=50000
```

## Alert Query Examples

### PromQL for Common Scenarios

**Tasks failing in last 5 minutes**:
```promql
sum(rate(weather_task_total{status="failure"}[5m])) by (task_name)
```

**Queue depth trend**:
```promql
weather_queue_depth
```

**Error breakdown by component**:
```promql
sum(rate(weather_errors_total[5m])) by (component, error_type)
```

**CPU usage per core**:
```promql
100 - (avg by (cpu) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

## Best Practices

### 1. Alert Fatigue Prevention

- Don't alert on everything - only actionable conditions
- Use appropriate durations (don't alert on transient spikes)
- Tune thresholds based on actual baseline

### 2. Alert Descriptions

- Include **what** happened
- Include **why** it matters
- Include **how** to investigate
- Include relevant metric values

### 3. Severity Guidelines

**Warning**: Use when:
- Issue may self-resolve
- Can wait 10-15 minutes for human intervention
- Degraded but not failed

**Critical**: Use when:
- Service is down or severely degraded
- Data loss imminent
- Immediate action required

### 4. Alert Grouping

Group related alerts:
- Use consistent label naming
- Group by component/service
- Avoid duplicate alerts for same root cause

## Troubleshooting Alerts

### Alert Not Firing

1. **Check expression**: Test in Prometheus graph
   ```promql
   # Example: Test if expression returns data
   rate(weather_task_total{status="failure"}[5m])
   ```

2. **Check duration**: Has threshold been exceeded for `for` duration?

3. **Check labels**: Ensure labels in expression match your metrics

### False Positives

1. **Increase duration**: Change `for: 5m` to `for: 10m`
2. **Adjust threshold**: Increase numeric threshold
3. **Add filters**: Narrow down using label filters

### Missing Metrics

If alerts reference metrics that don't exist:

```bash
# Check if metric is being scraped
curl http://localhost:9091/metrics | grep weather_task_total

# Check Prometheus targets
# http://localhost:9090/targets
```

## Configuration Files

- **Pipeline Alerts**: `configs/prometheus/alerts/pipeline.yml`
- **Infrastructure Alerts**: `configs/prometheus/alerts/infrastructure.yml`
- **Prometheus Config**: `configs/prometheus.yml`

---

**Total Alert Rules**: 28
**Alert Evaluation Interval**: 30s
**Prometheus Version**: Latest
**Documentation**: See MONITORING.md for full observability guide
