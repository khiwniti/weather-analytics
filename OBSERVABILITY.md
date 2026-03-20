# Observability Stack - Complete Guide

This is the master guide for the AI Weather Analytics Platform observability infrastructure.

## Quick Links

- 📊 **[MONITORING.md](./MONITORING.md)** - Metrics with Prometheus & Grafana
- 🚨 **[ALERTING.md](./ALERTING.md)** - Alert rules and thresholds
- 📝 **[LOGGING.md](./LOGGING.md)** - Centralized logging with Loki
- ✅ **[TESTING.md](./TESTING.md)** - Test suite documentation

## Overview

The platform uses a modern observability stack with:

### **The Three Pillars**

1. **Metrics** (Prometheus + Grafana)
   - Time-series data
   - Performance trends
   - Resource usage
   - Business metrics

2. **Logs** (Loki + Promtail + Grafana)
   - Centralized log aggregation
   - Searchable with LogQL
   - Automatic Docker log collection
   - Structured logging support

3. **Alerts** (Prometheus Alerting)
   - 28 alert rules
   - Warning & Critical levels
   - Automated threshold monitoring
   - Future: Route to Slack/Email/PagerDuty

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Grafana (Port 3002)                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │   Dashboards   │  │     Explore    │  │     Alerts     │ │
│  └────────────────┘  └────────────────┘  └────────────────┘ │
└──────────────┬──────────────────┬────────────────┬──────────┘
               │                  │                 │
       ┌───────▼───────┐  ┌──────▼──────┐  ┌──────▼──────┐
       │  Prometheus   │  │     Loki     │  │ Alertmanager│
       │  (Port 9090)  │  │ (Port 3100)  │  │  (Future)   │
       └───────┬───────┘  └──────┬───────┘  └─────────────┘
               │                  │
       ┌───────▼──────────────────▼─────────────────┐
       │           Data Sources & Collectors         │
       ├──────────────────────┬──────────────────────┤
       │  Prometheus Targets  │  Promtail Scraping   │
       ├──────────────────────┼──────────────────────┤
       │ - Celery Worker      │ - Docker Logs        │
       │ - Redis Exporter     │ - System Logs        │
       │ - Node Exporter      │ - JSON Parsing       │
       │ - Backend API        │ - Auto-labeling      │
       └──────────────────────┴──────────────────────┘
                               │
               ┌───────────────▼───────────────┐
               │    Weather Analytics Services │
               ├───────────────────────────────┤
               │ - Celery Workers              │
               │ - Backend API                 │
               │ - Redis                       │
               │ - Frontend                    │
               └───────────────────────────────┘
```

## Getting Started

### 1. Start the Full Stack

```bash
# Clone and navigate to project
cd ai-weather-analytics

# Start all services (including monitoring)
docker-compose up -d

# Verify all services are healthy
docker-compose ps
```

### 2. Access Monitoring UIs

**Grafana** (Primary Interface)
- URL: http://localhost:3002
- Login: `admin` / `admin`
- Change password on first login

**Prometheus** (Metrics Backend)
- URL: http://localhost:9090
- Check targets: http://localhost:9090/targets
- Check alerts: http://localhost:9090/alerts

**Loki** (Logs Backend)
- URL: http://localhost:3100
- Readiness: http://localhost:3100/ready

### 3. Explore Pre-configured Dashboards

Navigate to **Dashboards → Browse** in Grafana:

1. **Weather Pipeline Overview**
   - System health at a glance
   - Task success rates
   - Queue depth
   - Error trends

2. **Data Ingestion Details**
   - Download performance
   - Processing metrics
   - File throughput
   - Source-by-source breakdown

3. **System Performance**
   - CPU, memory, disk
   - Network I/O
   - Redis metrics
   - Container resources

4. **Service Logs**
   - Live log tailing
   - Error filtering
   - Service-specific views
   - Log volume trends

### 4. Set Up Alerts (Already Configured!)

Alerts are automatically active. Check them at:
- Prometheus: http://localhost:9090/alerts
- See [ALERTING.md](./ALERTING.md) for all 28 rules

## Key Metrics to Monitor

### Application Metrics

| Metric | Dashboard | Description |
|--------|-----------|-------------|
| `weather_task_total` | Pipeline Overview | Task execution count by status |
| `weather_task_duration_seconds` | Pipeline Overview | Task execution time |
| `weather_queue_depth` | Pipeline Overview | Pending tasks in queue |
| `weather_active_workers` | Pipeline Overview | Number of active Celery workers |
| `weather_download_duration_seconds` | Ingestion Details | Download time by source |
| `weather_download_size_bytes` | Ingestion Details | Downloaded file sizes |
| `weather_files_processed_total` | Ingestion Details | Files converted to Zarr |
| `weather_qc_pass_rate` | Pipeline Overview | Data quality percentage |
| `weather_errors_total` | Pipeline Overview | Error count by component |

### Infrastructure Metrics

| Metric | Dashboard | Description |
|--------|-----------|-------------|
| `node_cpu_seconds_total` | System Performance | CPU usage by mode |
| `node_memory_*` | System Performance | Memory usage stats |
| `node_filesystem_*` | System Performance | Disk usage and I/O |
| `node_network_*` | System Performance | Network traffic |
| `redis_memory_used_bytes` | System Performance | Redis memory consumption |
| `redis_connected_clients` | System Performance | Redis connection count |

## Common Workflows

### Workflow 1: Investigate Task Failures

1. **Check high-level metrics** (Grafana → Pipeline Overview)
   - Task success rate gauge
   - Error rate graph

2. **Identify failing task** (Prometheus)
   ```promql
   rate(weather_task_total{status="failure"}[5m])
   ```

3. **View task logs** (Grafana → Explore → Loki)
   ```logql
   {service="celery-worker", level="ERROR"} |= "ingest_gfs_cycle"
   ```

4. **Check related alerts** (Prometheus → Alerts)
   - `HighTaskFailureRate`
   - `HighErrorRate`

5. **Correlate with metrics** (Grafana dashboards)
   - Was CPU high?
   - Was disk full?
   - Network issues?

### Workflow 2: Performance Optimization

1. **Baseline current performance** (Grafana)
   - Average task duration
   - Download speeds
   - Processing times

2. **Make code changes**

3. **Compare before/after** (Grafana time range)
   - Use time picker to compare periods
   - Check if metrics improved

4. **Monitor for regressions** (Alerts)
   - `SlowDownloads`
   - `SlowProcessing`
   - `SlowTaskExecution`

### Workflow 3: Capacity Planning

1. **Review resource trends** (System Performance dashboard)
   - CPU usage over last 7 days
   - Memory growth rate
   - Disk usage trends

2. **Check queue depth** (Pipeline Overview)
   - Are tasks backing up?
   - Need more workers?

3. **Analyze peak times** (All dashboards)
   - When is load highest?
   - Scale accordingly

4. **Plan ahead** (Prometheus alerts)
   - `DiskWillFillIn24Hours`
   - `HighStorageUsage`

### Workflow 4: Incident Response

**When alert fires:**

1. **Acknowledge in Prometheus** (Silence if needed)
   - http://localhost:9090/alerts → Silence

2. **Check dashboard** (Grafana)
   - Which service is affected?
   - How severe?

3. **Review logs** (Loki)
   ```logql
   {service="<affected-service>"} |~ "(?i)error"
   ```

4. **Investigate metrics** (Prometheus)
   - What changed before incident?
   - Correlate with logs

5. **Fix and verify** (All tools)
   - Apply fix
   - Watch metrics return to normal
   - Verify alert resolves

## Integration Points

### With Existing Tools

**CI/CD Pipeline** (GitHub Actions)
- Test reports → Codecov
- Metrics → Prometheus (on deploy)
- Logs → Loki (after deployment)

**Flower** (Celery Monitoring)
- URL: http://localhost:5555
- Task details
- Worker management
- Complements Grafana dashboards

**Direct API Access**
- Backend health: http://localhost:3001/api/health
- Metrics endpoint: http://localhost:9091/metrics
- Loki API: http://localhost:3100/loki/api/v1/query

### External Integrations (Future)

**Alertmanager** (Route alerts)
```yaml
# Add to docker-compose.yml
alertmanager:
  image: prom/alertmanager
  ports:
    - "9093:9093"
  volumes:
    - ./configs/alertmanager.yml:/etc/alertmanager/config.yml
```

**Slack Notifications**
```yaml
# In alertmanager.yml
receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'YOUR_WEBHOOK_URL'
        channel: '#alerts'
```

**PagerDuty** (Critical alerts)
```yaml
receivers:
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_SERVICE_KEY'
```

## Troubleshooting

### No Metrics Appearing

1. Check scrape targets healthy:
   ```bash
   curl http://localhost:9090/targets
   ```

2. Verify metrics endpoint:
   ```bash
   curl http://localhost:9091/metrics | grep weather_
   ```

3. Check Prometheus logs:
   ```bash
   docker-compose logs prometheus
   ```

### No Logs Appearing

1. Check Promtail targets:
   ```bash
   curl http://localhost:9080/targets
   ```

2. Verify Loki is running:
   ```bash
   curl http://localhost:3100/ready
   ```

3. Check Promtail logs:
   ```bash
   docker-compose logs promtail
   ```

### Dashboard Not Loading

1. Verify Grafana is running:
   ```bash
   curl http://localhost:3002/api/health
   ```

2. Check datasources configured:
   ```bash
   curl http://localhost:3002/api/datasources
   ```

3. Restart Grafana:
   ```bash
   docker-compose restart grafana
   ```

### Alerts Not Firing

1. Test alert expression in Prometheus:
   - Navigate to http://localhost:9090/graph
   - Paste alert expression
   - Verify it returns data

2. Check alert rules loaded:
   ```bash
   curl http://localhost:9090/api/v1/rules | jq
   ```

3. Verify alert duration hasn't elapsed yet
   - Check `for:` field in alert rule

## Best Practices

### 1. Dashboard Organization

- **Overview first** - Start with Pipeline Overview
- **Drill down** - Use other dashboards for details
- **Customize** - Add panels for your specific needs
- **Share** - Export and version control dashboards

### 2. Alert Tuning

- **Start conservative** - Use default thresholds
- **Tune based on baseline** - Adjust after observing normal behavior
- **Avoid alert fatigue** - Only alert on actionable issues
- **Document runbooks** - Add resolution steps to alerts

### 3. Log Management

- **Use structured logging** - JSON format for easy parsing
- **Consistent labels** - Use same service names everywhere
- **Filter early** - Use specific queries to reduce load
- **Retention policy** - Set appropriate retention for disk space

### 4. Performance

- **Limit dashboard panels** - Don't query everything at once
- **Use appropriate intervals** - Don't query 30 days of raw metrics
- **Cache expensive queries** - Use recording rules
- **Sample high-volume logs** - Reduce log ingestion if needed

## Configuration Files Reference

### Prometheus

| File | Purpose |
|------|---------|
| `configs/prometheus.yml` | Main config, scrape targets |
| `configs/prometheus/alerts/pipeline.yml` | Pipeline alert rules |
| `configs/prometheus/alerts/infrastructure.yml` | Infrastructure alert rules |

### Loki

| File | Purpose |
|------|---------|
| `configs/loki/loki-config.yml` | Storage and indexing config |
| `configs/loki/promtail-config.yml` | Log collection and parsing |

### Grafana

| File | Purpose |
|------|---------|
| `configs/grafana/provisioning/datasources/` | Auto-configured datasources |
| `configs/grafana/provisioning/dashboards/` | Auto-loaded dashboards |

## Ports Reference

| Service | Port | Purpose | Access |
|---------|------|---------|--------|
| Frontend | 80 | Web UI | http://localhost:80 |
| Backend API | 3001 | REST API | http://localhost:3001 |
| Grafana | 3002 | Dashboards | http://localhost:3002 |
| Loki | 3100 | Logs API | http://localhost:3100 |
| Flower | 5555 | Celery UI | http://localhost:5555 |
| Redis | 6379 | Broker | redis://localhost:6379 |
| Promtail | 9080 | Log metrics | http://localhost:9080 |
| Prometheus | 9090 | Metrics | http://localhost:9090 |
| Celery Metrics | 9091 | App metrics | http://localhost:9091/metrics |
| Node Exporter | 9100 | System metrics | http://localhost:9100/metrics |
| Redis Exporter | 9121 | Redis metrics | http://localhost:9121/metrics |

## Resources & Documentation

### Internal Documentation

- [MONITORING.md](./MONITORING.md) - Metrics and Grafana setup
- [ALERTING.md](./ALERTING.md) - All 28 alert rules
- [LOGGING.md](./LOGGING.md) - Loki and LogQL guide
- [TESTING.md](./TESTING.md) - Test suite (61 tests, >85% coverage)
- [CLAUDE.md](./CLAUDE.md) - Developer setup guide

### External Resources

**Prometheus**
- [Query Documentation](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Alerting Rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)

**Grafana**
- [Dashboard Guide](https://grafana.com/docs/grafana/latest/dashboards/)
- [Panel Documentation](https://grafana.com/docs/grafana/latest/panels/)

**Loki**
- [LogQL Documentation](https://grafana.com/docs/loki/latest/logql/)
- [Best Practices](https://grafana.com/docs/loki/latest/best-practices/)

## Summary

### What You Get

✅ **4 Grafana Dashboards** - Pre-configured and ready
✅ **28 Alert Rules** - Covering all critical scenarios
✅ **Automatic Log Collection** - No code changes needed
✅ **12 Metrics** - Application and infrastructure
✅ **4 Log Sources** - All Docker containers
✅ **600+ Lines of Documentation** - Guides for everything

### Monitoring Stack Statistics

- **Services**: 12 total (including 4 monitoring services)
- **Dashboards**: 4 pre-configured
- **Alert Rules**: 28 (15 pipeline + 13 infrastructure)
- **Metrics Collected**: 100+ (Prometheus + exporters)
- **Log Sources**: All Docker containers
- **Storage Retention**: 30 days (metrics), unlimited (logs)

---

**Status**: ✅ Production-ready observability stack
**Last Updated**: 2026-03-20
**Version**: 1.0.0
