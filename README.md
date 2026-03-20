# AI Weather Analytics Platform

A scientifically accurate weather visualization system that ingests real-time weather data from multiple sources (NWP models, satellite, radar, ground observations) and provides interactive 3D visualizations for both public users and meteorologists.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![Node](https://img.shields.io/badge/node-18+-green.svg)
![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen.svg)

## Features

- 🌍 **Multi-Source Data Ingestion** - GFS, HRRR, GOES, NEXRAD, ASOS
- 🚀 **GPU-Accelerated Processing** - RAPIDS for fast GRIB → Zarr conversion
- 📊 **Interactive Dashboards** - Real-time metrics with Prometheus & Grafana
- 🚨 **Smart Alerting** - 28 pre-configured alert rules
- 📝 **Centralized Logging** - Loki for searchable logs
- ✅ **Quality Control** - Automated data validation
- 🔄 **Automated Pipeline** - Celery-based task scheduling
- ☁️ **Cloud-Ready** - Docker Compose or Google Cloud Run

## Quick Start

### Local Development (Docker Compose)

```bash
# Clone repository
git clone https://github.com/khiwniti/weather-analytics.git
cd weather-analytics

# Start all services
docker-compose up -d

# Access services
open http://localhost:80          # Frontend
open http://localhost:3002        # Grafana (admin/admin)
open http://localhost:9090        # Prometheus
```

### Cloud Run Deployment

```bash
# Set your GCP project
export GCP_PROJECT_ID="your-project-id"

# Run automated deployment
./.gcp/deploy.sh
```

See [Cloud Run Quick Start](./.gcp/QUICKSTART.md) for details.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│                    http://localhost:80                       │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────┐
│                  Backend API (Express)                       │
│                   http://localhost:3001                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ Celery Tasks
┌──────────────────────────▼──────────────────────────────────┐
│             Celery Workers (Python + RAPIDS)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Download   │→ │  Process    │→ │   Upload    │        │
│  │   (NOAA)    │  │ (GRIB→Zarr) │  │    (S3)     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└──────────────────────────┬──────────────────────────────────┘
                           │ Redis (Broker)
┌──────────────────────────▼──────────────────────────────────┐
│                     Redis Queue                              │
└─────────────────────────────────────────────────────────────┘

Monitoring Stack:
┌─────────────────────────────────────────────────────────────┐
│  Grafana → Prometheus → Exporters                           │
│  Grafana → Loki → Promtail → Docker Logs                    │
└─────────────────────────────────────────────────────────────┘
```

## Data Sources

| Source | Type | Update Frequency | Coverage |
|--------|------|------------------|----------|
| **GFS** | NWP Model | Every 6 hours | Global |
| **HRRR** | NWP Model | Hourly | CONUS |
| **GOES-16/17** | Satellite | 5-15 minutes | Americas |
| **NEXRAD** | Radar | 4-6 minutes | US |
| **ASOS** | Ground Obs | 1 minute | Airports |

## Tech Stack

### Backend
- **Python 3.11** - Data processing
- **Celery** - Distributed task queue
- **RAPIDS** - GPU-accelerated data processing
- **Redis** - Message broker
- **Node.js 18** - REST API

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Material-UI** - Component library

### Data Formats
- **GRIB2** - Input format (weather data)
- **Zarr** - Storage format (cloud-optimized)
- **NetCDF4** - Alternative format

### Monitoring
- **Prometheus** - Metrics collection
- **Grafana** - Visualization
- **Loki** - Log aggregation
- **Promtail** - Log collection

## Development

### Prerequisites

- **Docker** & **Docker Compose**
- **Python 3.11+**
- **Node.js 18+**
- **pnpm** (for monorepo)

### Local Setup

```bash
# Install dependencies
pip install -r requirements.txt
pnpm install

# Run tests
pytest --cov=src
cd src/frontend && npm test

# Start development servers
pnpm dev  # Starts frontend + backend
```

### Environment Variables

```bash
# Copy example
cp .env.example .env

# Configure
REDIS_URL=redis://localhost:6379
S3_WEATHER_BUCKET=your-bucket-name
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Frontend tests
cd src/frontend && npm test
```

**Coverage**: 61 tests, >85% coverage

See [TESTING.md](./TESTING.md) for details.

## Deployment

### Docker Compose (Development)

```bash
docker-compose up -d
```

12 services: frontend, backend, celery-worker, celery-beat, flower, redis, prometheus, grafana, loki, promtail, redis-exporter, node-exporter

### Google Cloud Run (Production)

```bash
./.gcp/deploy.sh
```

See [Cloud Run Deployment Guide](./.gcp/DEPLOYMENT.md).

### Manual Deployment

1. Set up Redis (Cloud Memorystore or Upstash)
2. Create storage bucket (S3 or GCS)
3. Deploy services
4. Configure Cloud Scheduler

## Monitoring

Access monitoring tools:

- **Grafana**: http://localhost:3002 (admin/admin)
  - Weather Pipeline Overview
  - Data Ingestion Details
  - System Performance
  - Service Logs

- **Prometheus**: http://localhost:9090
  - Metrics & alerts

- **Flower**: http://localhost:5555
  - Celery task monitoring

See [MONITORING.md](./MONITORING.md) and [OBSERVABILITY.md](./OBSERVABILITY.md).

## Documentation

- [**CLAUDE.md**](./CLAUDE.md) - Developer setup guide
- [**MONITORING.md**](./MONITORING.md) - Metrics & Grafana
- [**ALERTING.md**](./ALERTING.md) - Alert rules (28 rules)
- [**LOGGING.md**](./LOGGING.md) - Loki & LogQL
- [**OBSERVABILITY.md**](./OBSERVABILITY.md) - Complete observability guide
- [**TESTING.md**](./TESTING.md) - Test suite documentation
- [**.gcp/DEPLOYMENT.md**](./.gcp/DEPLOYMENT.md) - Cloud Run deployment
- [**.gcp/QUICKSTART.md**](./.gcp/QUICKSTART.md) - Quick start guide

## Project Structure

```
ai-weather-analytics/
├── src/
│   ├── frontend/          # React SPA
│   ├── backend/           # Express API
│   ├── ingestion/         # Data downloaders
│   │   ├── nwp/          # GFS, HRRR
│   │   ├── satellite/    # GOES
│   │   ├── radar/        # NEXRAD
│   │   ├── ground/       # ASOS
│   │   └── scheduler/    # Celery tasks
│   ├── processing/        # Data processing
│   │   ├── rapids/       # GPU acceleration
│   │   └── qc/           # Quality control
│   └── monitoring/        # Prometheus metrics
├── configs/               # Configuration files
│   ├── data/             # Source configs
│   ├── qc/               # QC thresholds
│   ├── prometheus/       # Alert rules
│   ├── grafana/          # Dashboards
│   └── loki/             # Log configs
├── .gcp/                  # Cloud Run deployment
│   ├── DEPLOYMENT.md
│   ├── QUICKSTART.md
│   ├── cloudbuild.yaml
│   └── deploy.sh
└── docker-compose.yml     # Local development
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **NOAA** - Weather data sources
- **RAPIDS** - GPU-accelerated processing
- **Grafana Labs** - Monitoring stack
- **Google Cloud** - Cloud infrastructure

## Support

- **Issues**: [GitHub Issues](https://github.com/khiwniti/weather-analytics/issues)
- **Discussions**: [GitHub Discussions](https://github.com/khiwniti/weather-analytics/discussions)
- **Documentation**: See docs/ directory

---

**Status**: ✅ Production-ready
**Version**: 1.0.0
**Last Updated**: 2026-03-20
