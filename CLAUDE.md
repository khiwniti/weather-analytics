# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI Weather Analytics Platform** - A scientifically accurate weather visualization system that ingests real-time weather data (NWP models, satellite, radar, ground observations) and provides interactive 3D visualizations for both public users and meteorologists.

**Architecture**: Microservices + Monorepo hybrid
- Frontend: React 18 + TypeScript + Vite
- Backend: Express API (Node.js)
- Data Pipeline: Python + Celery + RAPIDS (GPU-accelerated)
- Infrastructure: Docker Compose with Redis, Nginx

## Development Commands

### Monorepo Management (TurboPack)

```bash
# Install all dependencies
pnpm install

# Run all services in parallel (frontend + backend)
pnpm dev

# Build all services
pnpm build

# Start production builds
pnpm start
```

### Frontend (React + Vite)

```bash
cd src/frontend

# Development server (port 3000)
pnpm dev

# Production build
pnpm build

# Preview production build
pnpm preview

# Run tests
pnpm test
# or
npm test
```

### Backend (Express API)

```bash
cd src/backend

# Development server (port 3001)
pnpm dev
# or
npm run dev

# Production start
pnpm start
```

### Python Data Pipeline

```bash
# Install Python dependencies
pip install -r requirements.txt

# Note: RAPIDS (GPU acceleration) requires conda
# conda install -c rapidsai -c nvidia -c conda-forge cudf cuspatial cupy

# Run Celery worker
celery -A src.ingestion.scheduler.tasks worker --loglevel=info

# Run Celery Beat scheduler
celery -A src.ingestion.scheduler.tasks beat --loglevel=info

# Manual task execution
python src/ingestion/scheduler/tasks.py [gfs|hrrr|all]

# Test single downloader
python src/ingestion/nwp/gfs_downloader.py --cycle 12 --test
```

### Docker Compose (Full System)

```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f [service-name]

# Stop all services
docker-compose down

# Rebuild images
docker-compose build

# Services: redis, backend, frontend, celery-worker, celery-beat, flower, prometheus, grafana, redis-exporter, node-exporter
```

### Monitoring

- **Grafana (Visual Dashboards)**: http://localhost:3002 (login: admin/admin)
- **Prometheus (Metrics)**: http://localhost:9090
- **Flower (Celery monitoring)**: http://localhost:5555
- **Frontend**: http://localhost:80 (Docker) or http://localhost:3000 (dev)
- **Backend API**: http://localhost:3001
- **Health Check**: http://localhost:3001/api/health

## Architecture & Code Structure

### Data Flow

```
Weather Data Sources (NOAA)
  ↓ (download via Celery tasks)
Local /tmp Storage (GRIB2 files)
  ↓ (RAPIDS GPU conversion)
Zarr Format (cloud-native)
  ↓ (optional S3 upload - currently disabled)
Backend API (future)
  ↓ (HTTP/REST)
Frontend Visualization
```

### Key Directories

- **`src/frontend/`** - React TypeScript SPA
  - `pages/` - Route components (PublicView, ScientistView)
  - `components/` - Reusable React components
  - `App.tsx` - Root component with routing

- **`src/backend/`** - Express API server
  - `server.js` - API entry point (minimal implementation)

- **`src/ingestion/`** - Python data ingestion
  - `nwp/` - NWP models (GFS, HRRR downloaders)
  - `satellite/` - GOES satellite data
  - `radar/` - NEXRAD radar data
  - `ground/` - ASOS ground observations
  - `scheduler/` - Celery tasks and configuration
  - `pipeline/` - Orchestration and monitoring
  - `retention/` - Data cleanup policies

- **`src/processing/`** - Python data processing
  - `rapids/` - GPU-accelerated GRIB→Zarr conversion
  - `qc/` - Quality control modules

- **`configs/`** - YAML configuration files
  - `data/` - Data source configs (gfs.yaml, hrrr.yaml, etc.)
  - `qc/` - Quality control thresholds
  - `storage/` - Retention policies

### Critical File Locations

- **Celery Tasks**: `src/ingestion/scheduler/tasks.py`
  - Task definitions: `ingest_gfs_cycle()`, `ingest_hrrr_cycle()`
  - Retry logic: 3 attempts, 5-minute delay

- **Frontend Entry**: `src/frontend/main.tsx` → `src/frontend/App.tsx`
  - Routes: `/` (PublicView), `/scientist` (ScientistView)

- **Backend Entry**: `src/backend/server.js`
  - Currently only health check endpoint

- **Docker Orchestration**: `docker-compose.yml`
  - 6 services: redis, backend, frontend, celery-worker, celery-beat, flower

## Code Patterns

### Python Downloader Pattern

Each weather data source follows this structure:

```python
# src/ingestion/{source}/{source}_downloader.py

def download_{source}(
    cycle: str,
    forecast_hours: List[int],
    output_dir: str = "/tmp/{source}",
    **kwargs
) -> List[str]:
    """Download data from source.

    Returns:
        List[str]: Paths to downloaded files
    """
    # Download logic
    return downloaded_files
```

### Python Processor Pattern

```python
# src/ingestion/{source}/{source}_processor.py

def process_{source}(input_files: List[str]) -> ProcessingResult:
    """Transform raw data to standard format."""
    # Processing logic
    return result
```

### Celery Task Pattern

```python
@app.task(bind=True, max_retries=3)
def task_name(self, param: str = None):
    """Task description."""
    try:
        # Task logic
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise self.retry(exc=e)
```

### React Component Pattern

```typescript
// src/frontend/pages/ComponentName.tsx
import React from 'react';

const ComponentName = () => {
  return (
    <div>
      {/* Component JSX */}
    </div>
  );
};

export default ComponentName;
```

## Important Implementation Notes

### ⚠️ Current Limitations (See .planning/codebase/CONCERNS.md)

1. **Ephemeral Storage (without S3)**: Data in `/tmp` (lost on restart)
   - Pattern: `/tmp/{source}/{YYYYMMDD}/{cycle}/`
   - Configure persistent volumes or S3 for production

3. **Minimal Testing**: Python has 0% test coverage

### GPU Acceleration (RAPIDS)

RAPIDS requires:
- NVIDIA GPU with CUDA 12.x
- Conda installation (not pip): `conda install -c rapidsai cudf cuspatial cupy`
- Fallback: QC modules work on CPU, but GRIB conversion may require GPU

### Configuration

- **S3 Storage** (optional):
  - Set `S3_WEATHER_BUCKET` environment variable to enable cloud uploads
  - Configure AWS credentials: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
  - See `.env.example` for configuration template
  - If not configured, data remains in `/tmp` (ephemeral)

- **Redis URLs**:
  - Development: `redis://localhost:6379/0`
  - Docker: `redis://redis:6379/0`

- **Celery Config**: `src/ingestion/scheduler/config.py`
  - Timezone: UTC
  - Retry delay: 5 minutes
  - Max retries: 3

- **Weather Sources**: Configure in `configs/data/{source}.yaml`

### Time Handling

- All times in UTC (Celery configured with `timezone="UTC"`)
- Datetime formatting: `strftime("%Y%m%d")` for dates
- GFS cycles: 00Z, 06Z, 12Z, 18Z (4 times daily)
- HRRR cycles: Hourly (00-23Z)

## Testing

### Python Tests (pytest)

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest src/ingestion/nwp/test_gfs_downloader.py

# Run specific test
pytest src/processing/qc/test_temporal_qc.py::TestCheckTemporalConsistency::test_passes_with_valid_data

# Run with markers
pytest -m "not slow"  # Skip slow tests
pytest -m integration  # Only integration tests
pytest -m "not gpu"   # Skip GPU tests

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Frontend Tests

```bash
cd src/frontend
npm test

# Run specific test file
npm test -- src/utils/__tests__/dataTransform.test.js
```

### Test Coverage

Current coverage:
- **Python Unit Tests**: 45 tests covering downloaders, Celery tasks, QC modules
- **Frontend Tests**: Minimal (utils only)
- **Integration Tests**: Coming soon

Target: **>80% code coverage**

### CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/test.yml`):
- Runs on push to master/main/develop
- Tests Python 3.9, 3.10, 3.11
- Runs pytest with coverage reporting
- Lints code (ruff, black, isort)
- Tests Docker builds
- Uploads coverage to Codecov

## Testing

### Frontend Tests

```bash
cd src/frontend
npm test

# Run specific test file
npm test -- src/utils/__tests__/dataTransform.test.js
```

### Python Tests (Not Implemented)

Expected pattern when added:
```bash
# Run all tests
pytest

# Run specific module
pytest src/ingestion/nwp/test_gfs_downloader.py

# With coverage
pytest --cov=src --cov-report=html

# Verbose
pytest -v
```

## Common Tasks

### Add a New Weather Data Source

1. Create downloader: `src/ingestion/{source}/{source}_downloader.py`
2. Create processor: `src/ingestion/{source}/{source}_processor.py`
3. Add config: `configs/data/{source}.yaml`
4. Add Celery task: Update `src/ingestion/scheduler/tasks.py`
5. Add schedule: Update `src/ingestion/scheduler/beat.py`

### Debug Celery Tasks

```bash
# View Flower monitoring UI
open http://localhost:5555

# View worker logs
docker-compose logs -f celery-worker

# View beat logs
docker-compose logs -f celery-beat

# Check Redis
docker-compose exec redis redis-cli
> KEYS *
> GET celery-task-meta-{task-id}
```

### Debug Frontend Issues

```bash
# Check dev server logs
cd src/frontend && pnpm dev

# Check Vite build
pnpm build

# Check browser console
# Open http://localhost:3000
# F12 → Console tab
```

### Debug Backend Issues

```bash
# Check backend logs
cd src/backend && pnpm dev

# Test health endpoint
curl http://localhost:3001/api/health

# View Docker logs
docker-compose logs -f backend
```

## Project Context

This codebase is **Phase 1-complete** (data ingestion foundation) with **minimal UI implementation**. Key areas needing work:

1. **Data API** - Backend endpoints for querying processed weather data
2. **Visualization** - Interactive 3D weather visualizations using deck.gl
3. **Data Pipeline** - Remove demo limits, enable S3 storage, implement retention
4. **Testing** - Add comprehensive test coverage
5. **Authentication** - User accounts and role-based access

See `.planning/` directory for:
- `ROADMAP.md` - Phase breakdown and milestones
- `REQUIREMENTS.md` - User requirements and acceptance criteria
- `STATE.md` - Current project status
- `codebase/CONCERNS.md` - 28 identified technical concerns

## Additional Resources

- **Planning Documents**: `.planning/` directory
- **Phase Documentation**: `.planning/phases/{NN}-{phase-name}/`
- **Codebase Analysis**: `.planning/codebase/` (STACK, ARCHITECTURE, CONVENTIONS, etc.)
- **Test Report**: `TEST_REPORT.md` (if exists)
