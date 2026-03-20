# Centralized Logging Guide

This document describes the centralized logging setup using Loki for the AI Weather Analytics Platform.

## Overview

The logging stack consists of:

1. **Loki** - Log aggregation and storage backend
2. **Promtail** - Log collection agent (scrapes Docker containers)
3. **Grafana** - Log visualization and exploration
4. **Service Logs Dashboard** - Pre-configured log views

All Docker container logs are automatically collected, indexed, and made searchable.

## Architecture

```
Docker Containers (stdout/stderr)
  ↓ (via Docker API)
Promtail (log shipper)
  ↓ (HTTP push)
Loki (storage & indexing)
  ↓ (LogQL queries)
Grafana (visualization)
```

## Components

### Loki (Port 3100)

Log aggregation backend that stores and indexes logs.

**Access**: http://localhost:3100

**Configuration**: `configs/loki/loki-config.yml`

**Features**:
- Efficient log storage (only indexes labels, not content)
- 24-hour retention chunks
- BoltDB for indexing
- Filesystem storage backend

**Storage**:
- Chunks: `/loki/chunks`
- Rules: `/loki/rules`
- Volume: `loki_data`

### Promtail (Port 9080)

Log collection agent that scrapes Docker container logs.

**Configuration**: `configs/loki/promtail-config.yml`

**What it collects**:
- All Docker containers in the `ai-weather-analytics` project
- System logs from `/var/log` (optional)

**Labels extracted**:
- `container` - Container name
- `service` - Docker Compose service name
- `project` - Docker Compose project name
- `container_id` - Container ID
- `image` - Docker image name
- `level` - Log level (ERROR, WARNING, INFO, DEBUG)

**Log processing pipeline**:
1. Scrape Docker container stdout/stderr
2. Parse JSON logs (if applicable)
3. Extract log level
4. Add labels
5. Push to Loki

### Grafana Integration

Loki is pre-configured as a datasource in Grafana.

**Access**: http://localhost:3002 → Explore → Select "Loki"

**Pre-configured Dashboard**: "Service Logs"
- Log volume by service (time-series)
- Log volume by level (time-series)
- All service logs (scrollable)
- Celery worker logs
- Error logs (filtered)
- Backend API logs
- Redis logs

## Usage

### Starting the Logging Stack

```bash
# Start all services including logging
docker-compose up -d

# Verify Loki is running
curl http://localhost:3100/ready

# Verify Promtail is running
curl http://localhost:9080/ready

# Check Promtail targets
curl http://localhost:9080/targets
```

### Viewing Logs in Grafana

**Method 1: Pre-configured Dashboard**

1. Navigate to http://localhost:3002
2. Login (admin/admin)
3. Click "Dashboards" → Browse
4. Select "Service Logs"
5. Use service dropdown to filter by service
6. Adjust time range as needed

**Method 2: Explore Mode**

1. Click "Explore" icon (compass)
2. Select "Loki" datasource
3. Use Log Browser or write LogQL query
4. Click "Run Query"

### LogQL Query Examples

LogQL is similar to PromQL but for logs.

**All logs from Celery worker**:
```logql
{service="celery-worker"}
```

**Error logs from all services**:
```logql
{project="ai-weather-analytics"} |~ "(?i)(error|exception|fail)"
```

**Logs containing "download"**:
```logql
{project="ai-weather-analytics"} |= "download"
```

**Case-insensitive search for "GFS"**:
```logql
{service="celery-worker"} |~ "(?i)gfs"
```

**Logs from last hour with level ERROR**:
```logql
{project="ai-weather-analytics", level="ERROR"}
```

**Count of error logs per minute**:
```logql
sum(count_over_time({project="ai-weather-analytics"} |~ "(?i)error" [1m]))
```

**Logs excluding DEBUG level**:
```logql
{project="ai-weather-analytics"} != "DEBUG"
```

**Multiple conditions (AND)**:
```logql
{service="celery-worker"} |= "GFS" |~ "(?i)error"
```

**Multiple conditions (OR)**:
```logql
{service="celery-worker"} |~ "(?i)(gfs|hrrr)"
```

**Extract fields (JSON parsing)**:
```logql
{service="celery-worker"} | json | level="ERROR"
```

**Rate of logs**:
```logql
rate({project="ai-weather-analytics"}[5m])
```

**Logs by service (top 10)**:
```logql
topk(10, sum by (service) (count_over_time({project="ai-weather-analytics"}[1h])))
```

## LogQL Operators

### Filter Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `\|=` | Contains (case-sensitive) | `\|= "error"` |
| `!=` | Does not contain | `!= "debug"` |
| `\|~` | Regex match | `\|~ "(?i)error"` |
| `!~` | Regex not match | `!~` `"DEBUG\|INFO"` |

### Parser Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `\| json` | Parse JSON | `\| json \| level="ERROR"` |
| `\| logfmt` | Parse logfmt | `\| logfmt \| status="500"` |
| `\| regexp` | Parse with regex | `\| regexp "(?P<status>\\d{3})"` |

### Aggregation Functions

| Function | Description | Example |
|----------|-------------|---------|
| `rate()` | Rate per second | `rate({service="backend"}[5m])` |
| `count_over_time()` | Count logs | `count_over_time({service="redis"}[1h])` |
| `sum()` | Sum values | `sum(count_over_time({...}[1m]))` |
| `avg()` | Average | `avg(rate({...}[5m]))` |
| `topk()` | Top K results | `topk(5, sum by (service)(...))` |

## Common Use Cases

### 1. Debugging Task Failures

```logql
# Find all error logs from Celery
{service="celery-worker"} |~ "(?i)(error|exception|traceback)"

# Filter by specific task
{service="celery-worker"} |= "ingest_gfs_cycle" |~ "(?i)error"
```

### 2. Monitoring Download Issues

```logql
# All download-related errors
{project="ai-weather-analytics"} |= "download" |~ "(?i)(fail|error|timeout)"

# Download logs from specific source
{service="celery-worker"} |= "GFS" |= "download"
```

### 3. API Request Tracking

```logql
# All backend API requests
{service="backend"}

# Failed API requests (HTTP 4xx/5xx)
{service="backend"} |~ "(?i)(400|401|403|404|500|502|503)"
```

### 4. Performance Analysis

```logql
# Slow processing warnings
{service="celery-worker"} |= "slow" | json | level="WARNING"

# Task duration logs
{service="celery-worker"} |= "duration" | json
```

### 5. Security Monitoring

```logql
# Authentication failures
{project="ai-weather-analytics"} |~ "(?i)(unauthorized|forbidden|denied)"

# Unusual activity patterns
{service="backend"} |~ "(?i)(suspicious|attack|injection)"
```

## Log Levels

Logs are automatically labeled with level when detected:

- **ERROR** - Errors and exceptions
- **WARNING** - Warnings and deprecations
- **INFO** - Informational messages
- **DEBUG** - Debug-level details

Filter by level:
```logql
{project="ai-weather-analytics", level="ERROR"}
```

## Log Retention

**Default retention**: Unlimited (constrained by disk space)

To configure retention, update `configs/loki/loki-config.yml`:

```yaml
limits_config:
  retention_period: 168h  # 7 days
```

Then configure compaction:

```yaml
compactor:
  working_directory: /loki/compactor
  shared_store: filesystem
  retention_enabled: true
  retention_delete_delay: 2h
```

## Performance Tuning

### Reducing Query Time

1. **Use specific labels** - Narrow down by service/container
   ```logql
   # Fast
   {service="celery-worker"} |= "error"

   # Slow
   {project="ai-weather-analytics"} |= "error"
   ```

2. **Limit time range** - Don't query days of logs
   - Use "Last 1 hour" instead of "Last 7 days"

3. **Use filters early** - Filter before parsing
   ```logql
   # Better
   {service="backend"} |= "error" | json

   # Slower
   {service="backend"} | json | level="ERROR"
   ```

### Reducing Storage

1. **Drop unnecessary logs**:
   Edit `configs/loki/promtail-config.yml`:
   ```yaml
   pipeline_stages:
     - drop:
         source: message
         expression: ".*health check.*"
   ```

2. **Sample logs**:
   ```yaml
   pipeline_stages:
     - match:
         selector: '{service="noisy-service"}'
         stages:
           - sampling:
               rate: 0.1  # Keep 10% of logs
   ```

## Alerting on Logs

Create Loki recording rules in `configs/loki/loki-rules.yml`:

```yaml
groups:
  - name: log_alerts
    interval: 1m
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate({project="ai-weather-analytics"} |~ "(?i)error" [5m])) > 10
        for: 5m
        annotations:
          summary: "High error rate in logs"
```

## Troubleshooting

### No Logs Appearing

1. **Check Promtail targets**:
   ```bash
   curl http://localhost:9080/targets
   ```
   Should show discovered Docker containers.

2. **Check Promtail logs**:
   ```bash
   docker-compose logs promtail
   ```

3. **Verify Loki is reachable**:
   ```bash
   curl http://localhost:3100/ready
   ```

4. **Test query directly**:
   ```bash
   curl -G -s "http://localhost:3100/loki/api/v1/query" \
     --data-urlencode 'query={project="ai-weather-analytics"}' \
     | jq
   ```

### Logs Not Parsing

If JSON logs aren't parsing:

1. Check log format in container:
   ```bash
   docker logs celery-worker --tail 10
   ```

2. Update pipeline in `promtail-config.yml`:
   ```yaml
   pipeline_stages:
     - json:
         expressions:
           level: levelname  # Adjust key name
           message: msg      # Adjust key name
   ```

### High Memory Usage

Loki uses memory for caching. To reduce:

1. Decrease cache size in `loki-config.yml`:
   ```yaml
   query_range:
     results_cache:
       cache:
         embedded_cache:
           max_size_mb: 50  # Default 100
   ```

2. Reduce query parallelism:
   ```yaml
   limits_config:
     max_query_parallelism: 16  # Default 32
   ```

## Integration with Other Tools

### Export Logs to File

```bash
# Export last hour of error logs
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={project="ai-weather-analytics"} |~ "(?i)error"' \
  --data-urlencode "start=$(date -u -d '1 hour ago' +%s)000000000" \
  --data-urlencode "end=$(date -u +%s)000000000" \
  | jq -r '.data.result[].values[][1]' > errors.log
```

### Stream Logs in Terminal

```bash
# Use logcli (Loki CLI tool)
docker run -it --rm --network ai-weather-network \
  grafana/logcli:latest \
  --addr=http://loki:3100 \
  query '{service="celery-worker"}' --tail
```

### Forward to External System

Configure Promtail to send logs to multiple destinations:

```yaml
clients:
  - url: http://loki:3100/loki/api/v1/push
  - url: http://external-loki:3100/loki/api/v1/push
    basic_auth:
      username: user
      password: pass
```

## Best Practices

### 1. Structured Logging

Use JSON logging in your applications:

**Python**:
```python
import logging
import json_log_formatter

formatter = json_log_formatter.JSONFormatter()
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

logger.info("Task completed", extra={
    "task_name": "ingest_gfs",
    "duration": 120.5,
    "files_processed": 42
})
```

**Node.js**:
```javascript
const winston = require('winston');

const logger = winston.createLogger({
  format: winston.format.json(),
  transports: [
    new winston.transports.Console()
  ]
});

logger.info('Request processed', {
  method: 'GET',
  path: '/api/weather',
  duration: 45
});
```

### 2. Consistent Labels

Use consistent service names in Docker Compose to enable filtering.

### 3. Avoid High-Cardinality Labels

Don't use labels with many unique values:
- ❌ User IDs
- ❌ Request IDs
- ❌ Timestamps
- ✅ Service names
- ✅ Log levels
- ✅ Environment

### 4. Query Optimization

- Use specific labels
- Limit time ranges
- Filter before parsing
- Use `count_over_time()` instead of raw logs for metrics

## Configuration Files

- **Loki Config**: `configs/loki/loki-config.yml`
- **Promtail Config**: `configs/loki/promtail-config.yml`
- **Grafana Datasource**: `configs/grafana/provisioning/datasources/prometheus.yml`
- **Logs Dashboard**: `configs/grafana/provisioning/dashboards/service-logs.json`

## Ports Reference

| Service | Port | Purpose |
|---------|------|---------|
| Loki | 3100 | Log storage API |
| Promtail | 9080 | Metrics & targets |
| Grafana | 3002 | Log visualization |

---

**Status**: ✅ Centralized logging operational
**Log Sources**: All Docker containers
**Storage**: Filesystem with BoltDB indexing
**Retention**: Unlimited (disk-constrained)
**Dashboards**: 1 pre-configured (Service Logs)
