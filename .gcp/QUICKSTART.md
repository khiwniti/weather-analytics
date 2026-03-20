# Cloud Run Quick Start Guide

## Prerequisites

1. **GCP Account** - With billing enabled
2. **gcloud CLI** - Installed and authenticated
3. **GitHub Repository** - Connected to Cloud Run

## 1-Minute Setup

```bash
# Clone your repo
git clone https://github.com/khiwniti/weather-analytics.git
cd weather-analytics

# Set your GCP project
export GCP_PROJECT_ID="your-project-id"

# Run deployment script
./.gcp/deploy.sh
```

That's it! The script will:
- ✅ Enable required GCP APIs
- ✅ Create Cloud Memorystore (Redis)
- ✅ Create Cloud Storage bucket
- ✅ Configure Secret Manager
- ✅ Build and deploy all services
- ✅ Set up Cloud Scheduler jobs

## What Gets Deployed

### Services

1. **weather-frontend** (Port 80)
   - React SPA
   - Auto-scales 0-5 instances
   - 256MB RAM, 1 CPU

2. **weather-backend** (Port 3001)
   - Express.js API
   - Auto-scales 0-10 instances
   - 512MB RAM, 1 CPU

3. **weather-worker** (Port 9091)
   - Celery worker
   - Min 1 instance (always on)
   - 2GB RAM, 2 CPU

### Infrastructure

- **Cloud Memorystore**: Redis for Celery (~$50/month)
- **Cloud Storage**: Weather data bucket (auto-delete after 30 days)
- **Cloud Scheduler**: 2 jobs (GFS every 6h, HRRR hourly)
- **VPC Connector**: For Redis access
- **Secret Manager**: Secure credential storage

## Manual Deployment (Step-by-Step)

If you prefer manual control:

### Step 1: Set Project

```bash
gcloud config set project YOUR_PROJECT_ID
```

### Step 2: Enable APIs

```bash
gcloud services enable run.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  redis.googleapis.com \
  storage-api.googleapis.com
```

### Step 3: Create Redis

```bash
gcloud redis instances create weather-redis \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_7_0 \
  --tier=BASIC
```

### Step 4: Create Storage

```bash
gsutil mb -l us-central1 gs://YOUR_PROJECT_ID-weather-data
```

### Step 5: Create VPC Connector

```bash
gcloud compute networks vpc-access connectors create weather-connector \
  --region=us-central1 \
  --range=10.8.0.0/28
```

### Step 6: Deploy Services

```bash
# Deploy backend
gcloud run deploy weather-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --dockerfile Dockerfile.backend

# Deploy frontend
gcloud run deploy weather-frontend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --dockerfile Dockerfile.frontend

# Deploy worker
gcloud run deploy weather-worker \
  --source . \
  --region us-central1 \
  --no-allow-unauthenticated \
  --dockerfile Dockerfile
```

## Accessing Your Application

After deployment:

```bash
# Get service URLs
FRONTEND_URL=$(gcloud run services describe weather-frontend --region us-central1 --format="value(status.url)")
BACKEND_URL=$(gcloud run services describe weather-backend --region us-central1 --format="value(status.url)")

echo "Frontend: $FRONTEND_URL"
echo "Backend: $BACKEND_URL"

# Test
curl $BACKEND_URL/api/health
```

## Monitoring

### View Logs

```bash
# Real-time logs
gcloud run logs tail weather-worker --region us-central1

# Last 50 lines
gcloud run logs read weather-backend --region us-central1 --limit 50
```

### Cloud Console

- **Logs**: https://console.cloud.google.com/logs
- **Monitoring**: https://console.cloud.google.com/monitoring
- **Cloud Run**: https://console.cloud.google.com/run

## Cost Optimization

### Free Tier

Cloud Run free tier:
- 2 million requests/month
- 360,000 GB-seconds
- 180,000 vCPU-seconds

### Reduce Costs

```bash
# Scale down worker
gcloud run services update weather-worker \
  --min-instances=0 \
  --region us-central1

# Use smaller Redis (Upstash free tier)
# Sign up at https://upstash.com
# Update REDIS_URL in Secret Manager
```

## Troubleshooting

### Service Not Responding

```bash
# Check service status
gcloud run services describe weather-backend --region us-central1

# Check recent deployments
gcloud run revisions list --service weather-backend --region us-central1

# View error logs
gcloud run logs read weather-backend --region us-central1 --limit 100 | grep ERROR
```

### Redis Connection Issues

```bash
# Verify VPC connector
gcloud compute networks vpc-access connectors describe weather-connector --region us-central1

# Get Redis IP
gcloud redis instances describe weather-redis --region us-central1 --format="value(host)"

# Update REDIS_URL secret
echo -n "redis://NEW_IP:6379" | gcloud secrets versions add REDIS_URL --data-file=-
```

### High Costs

```bash
# Check billing
gcloud billing projects describe YOUR_PROJECT_ID

# View Cloud Run metrics
gcloud run services list --region us-central1

# Set budget alerts
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="Weather Analytics Budget" \
  --budget-amount=100USD
```

## CI/CD Setup

### Connect to GitHub

```bash
# Create build trigger
gcloud builds triggers create github \
  --repo-name=weather-analytics \
  --repo-owner=khiwniti \
  --branch-pattern="^main$" \
  --build-config=.gcp/cloudbuild.yaml
```

Now every push to `main` branch automatically deploys!

## Rollback

```bash
# List revisions
gcloud run revisions list --service weather-backend --region us-central1

# Rollback to previous revision
gcloud run services update-traffic weather-backend \
  --to-revisions=weather-backend-00002-xyz=100 \
  --region us-central1
```

## Clean Up

To delete everything:

```bash
# Delete Cloud Run services
gcloud run services delete weather-backend --region us-central1 --quiet
gcloud run services delete weather-frontend --region us-central1 --quiet
gcloud run services delete weather-worker --region us-central1 --quiet

# Delete Redis
gcloud redis instances delete weather-redis --region us-central1 --quiet

# Delete VPC connector
gcloud compute networks vpc-access connectors delete weather-connector --region us-central1 --quiet

# Delete scheduler jobs
gcloud scheduler jobs delete gfs-ingestion --location us-central1 --quiet
gcloud scheduler jobs delete hrrr-ingestion --location us-central1 --quiet

# Delete storage bucket
gsutil -m rm -r gs://YOUR_PROJECT_ID-weather-data
```

## Next Steps

1. ✅ Set up custom domain
2. ✅ Configure Cloud CDN for frontend
3. ✅ Add Cloud SQL for metadata
4. ✅ Set up monitoring alerts
5. ✅ Configure backup strategy

## Support

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [GitHub Repository](https://github.com/khiwniti/weather-analytics)
- [Full Deployment Guide](./.gcp/DEPLOYMENT.md)
