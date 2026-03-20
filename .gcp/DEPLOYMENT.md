# Google Cloud Run Deployment Guide

This guide covers deploying the AI Weather Analytics Platform to Google Cloud Run.

## Architecture Overview

### Cloud Run Services

The application is split into multiple Cloud Run services:

1. **Frontend** - React SPA served via Nginx
2. **Backend API** - Express.js REST API
3. **Celery Worker** - Background task processing
4. **Prometheus Metrics** - Metrics collection (optional)

### External Services (Required)

1. **Cloud Memorystore (Redis)** - Celery broker
2. **Cloud Storage** - Weather data storage
3. **Cloud Scheduler** - Replaces Celery Beat
4. **Secret Manager** - API keys and credentials
5. **Cloud SQL (Optional)** - For metadata storage

### Monitoring Stack

1. **Cloud Monitoring** - Replaces Prometheus (native GCP)
2. **Cloud Logging** - Replaces Loki (native GCP)
3. **Cloud Trace** - Distributed tracing
4. **Error Reporting** - Automatic error tracking

## Prerequisites

```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Login and set project
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  redis.googleapis.com \
  storage-api.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com
```

## Step 1: Set Up External Services

### 1.1 Create Cloud Memorystore (Redis)

```bash
# Create Redis instance (Basic tier)
gcloud redis instances create weather-redis \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_7_0 \
  --tier=BASIC

# Get connection info
gcloud redis instances describe weather-redis \
  --region=us-central1 \
  --format="value(host,port)"
```

**Cost**: ~$50/month for 1GB Basic tier

**Alternative (Serverless)**: Use Upstash Redis for pay-per-request pricing
- Sign up at https://upstash.com
- Create Redis database
- Copy connection URL

### 1.2 Create Cloud Storage Bucket

```bash
# Create bucket for weather data
gsutil mb -l us-central1 gs://YOUR_PROJECT_ID-weather-data

# Set lifecycle policy (auto-delete after 30 days)
cat > lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 30}
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://YOUR_PROJECT_ID-weather-data
```

### 1.3 Set Up Secret Manager

```bash
# Create secrets
echo -n "YOUR_REDIS_URL" | gcloud secrets create REDIS_URL --data-file=-
echo -n "YOUR_S3_BUCKET_NAME" | gcloud secrets create S3_WEATHER_BUCKET --data-file=-
echo -n "YOUR_AWS_KEY" | gcloud secrets create AWS_ACCESS_KEY_ID --data-file=-
echo -n "YOUR_AWS_SECRET" | gcloud secrets create AWS_SECRET_ACCESS_KEY --data-file=-

# Grant access to Cloud Run
gcloud secrets add-iam-policy-binding REDIS_URL \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Step 2: Build and Deploy Services

### 2.1 Deploy Backend API

```bash
# Build and deploy
gcloud run deploy weather-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 3001 \
  --min-instances 0 \
  --max-instances 10 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --set-env-vars NODE_ENV=production \
  --set-secrets=REDIS_URL=REDIS_URL:latest \
  --dockerfile Dockerfile.backend
```

### 2.2 Deploy Frontend

```bash
# Build and deploy
gcloud run deploy weather-frontend \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 80 \
  --min-instances 0 \
  --max-instances 5 \
  --memory 256Mi \
  --cpu 1 \
  --dockerfile Dockerfile.frontend
```

### 2.3 Deploy Celery Worker

```bash
# Build and deploy
gcloud run deploy weather-worker \
  --source . \
  --platform managed \
  --region us-central1 \
  --no-allow-unauthenticated \
  --port 9091 \
  --min-instances 1 \
  --max-instances 5 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --set-env-vars CELERY_BROKER_URL=REDIS_URL \
  --set-secrets=REDIS_URL=REDIS_URL:latest,S3_WEATHER_BUCKET=S3_WEATHER_BUCKET:latest \
  --dockerfile Dockerfile
```

## Step 3: Set Up Cloud Scheduler (Replaces Celery Beat)

```bash
# Create scheduler for GFS ingestion (every 6 hours)
gcloud scheduler jobs create http gfs-ingestion \
  --location us-central1 \
  --schedule="0 */6 * * *" \
  --uri="https://weather-worker-XXXXXX-uc.a.run.app/tasks/ingest-gfs" \
  --http-method POST \
  --oidc-service-account-email=YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com \
  --oidc-token-audience="https://weather-worker-XXXXXX-uc.a.run.app"

# Create scheduler for HRRR ingestion (hourly)
gcloud scheduler jobs create http hrrr-ingestion \
  --location us-central1 \
  --schedule="0 * * * *" \
  --uri="https://weather-worker-XXXXXX-uc.a.run.app/tasks/ingest-hrrr" \
  --http-method POST \
  --oidc-service-account-email=YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com \
  --oidc-token-audience="https://weather-worker-XXXXXX-uc.a.run.app"
```

## Step 4: Configure Monitoring

### 4.1 Cloud Monitoring (Replaces Prometheus)

Cloud Monitoring is automatically enabled. Custom metrics:

```python
# In your Python code
from google.cloud import monitoring_v3

client = monitoring_v3.MetricServiceClient()
project_name = f"projects/{project_id}"

series = monitoring_v3.TimeSeries()
series.metric.type = "custom.googleapis.com/weather/task_duration"
series.resource.type = "cloud_run_revision"
series.resource.labels["service_name"] = "weather-worker"

point = monitoring_v3.Point()
point.value.double_value = duration
point.interval.end_time.seconds = int(time.time())
series.points = [point]

client.create_time_series(name=project_name, time_series=[series])
```

### 4.2 Cloud Logging (Replaces Loki)

Automatic log collection. View logs:

```bash
# View worker logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=weather-worker" \
  --limit 50 \
  --format json

# Create log-based metric
gcloud logging metrics create task_errors \
  --description="Count of task errors" \
  --log-filter='resource.type="cloud_run_revision"
    severity="ERROR"
    jsonPayload.task_name=~"ingest_.*"'
```

### 4.3 Set Up Alerting

```bash
# Create alert policy for high error rate
gcloud alpha monitoring policies create \
  --notification-channels=YOUR_CHANNEL_ID \
  --display-name="High Task Error Rate" \
  --condition-display-name="Error rate > 10%" \
  --condition-threshold-value=0.1 \
  --condition-threshold-duration=300s \
  --condition-filter='resource.type="cloud_run_revision"
    metric.type="logging.googleapis.com/user/task_errors"'
```

## Step 5: Configure Networking

### 5.1 Custom Domain (Optional)

```bash
# Map custom domain to frontend
gcloud run domain-mappings create \
  --service weather-frontend \
  --domain weather.yourdomain.com \
  --region us-central1

# Map custom domain to backend
gcloud run domain-mappings create \
  --service weather-backend \
  --domain api.weather.yourdomain.com \
  --region us-central1
```

### 5.2 VPC Connector (For Cloud Memorystore)

```bash
# Create VPC connector
gcloud compute networks vpc-access connectors create weather-connector \
  --region us-central1 \
  --range 10.8.0.0/28

# Update services to use VPC connector
gcloud run services update weather-backend \
  --vpc-connector weather-connector \
  --region us-central1

gcloud run services update weather-worker \
  --vpc-connector weather-connector \
  --region us-central1
```

## Step 6: CI/CD with Cloud Build

Create `.gcp/cloudbuild.yaml`:

```yaml
steps:
  # Build backend
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/weather-backend', '-f', 'Dockerfile.backend', '.']

  # Build frontend
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/weather-frontend', '-f', 'Dockerfile.frontend', '.']

  # Build worker
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/weather-worker', '-f', 'Dockerfile', '.']

  # Push images
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/weather-backend']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/weather-frontend']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/weather-worker']

  # Deploy backend
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'weather-backend'
      - '--image=gcr.io/$PROJECT_ID/weather-backend'
      - '--region=us-central1'
      - '--platform=managed'

  # Deploy frontend
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'weather-frontend'
      - '--image=gcr.io/$PROJECT_ID/weather-frontend'
      - '--region=us-central1'
      - '--platform=managed'

  # Deploy worker
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'weather-worker'
      - '--image=gcr.io/$PROJECT_ID/weather-worker'
      - '--region=us-central1'
      - '--platform=managed'

images:
  - 'gcr.io/$PROJECT_ID/weather-backend'
  - 'gcr.io/$PROJECT_ID/weather-frontend'
  - 'gcr.io/$PROJECT_ID/weather-worker'

timeout: 1800s
```

Connect to GitHub:

```bash
# Connect repository
gcloud builds triggers create github \
  --repo-name=weather-analytics \
  --repo-owner=khiwniti \
  --branch-pattern="^main$" \
  --build-config=.gcp/cloudbuild.yaml
```

## Architecture Differences

### Local (docker-compose) vs Cloud Run

| Component | Local | Cloud Run |
|-----------|-------|-----------|
| **Redis** | Container | Cloud Memorystore or Upstash |
| **Storage** | /tmp | Cloud Storage |
| **Scheduling** | Celery Beat | Cloud Scheduler |
| **Monitoring** | Prometheus/Grafana | Cloud Monitoring |
| **Logging** | Loki/Promtail | Cloud Logging |
| **Secrets** | .env file | Secret Manager |
| **Networking** | Docker network | VPC Connector |
| **Scaling** | Manual | Automatic (0-N) |

## Cost Estimation

### Monthly Costs (Light Usage)

| Service | Cost | Notes |
|---------|------|-------|
| Cloud Run (Frontend) | ~$5 | 100K requests/month |
| Cloud Run (Backend) | ~$10 | 500K requests/month |
| Cloud Run (Worker) | ~$30 | 1 instance always on |
| Cloud Memorystore | ~$50 | 1GB Basic tier |
| Cloud Storage | ~$5 | 100GB storage |
| Cloud Scheduler | ~$1 | 10 jobs |
| **Total** | **~$100/month** | |

### Cost Optimization

1. **Use Upstash Redis** - Pay per request (~$10-20/month)
2. **Min instances = 0** - Scale to zero when idle
3. **Cloud Storage lifecycle** - Auto-delete old files
4. **Shared VPC connector** - $0.10/hour per connector

## Environment Variables

### Backend (.env.production)

```bash
NODE_ENV=production
PORT=3001
REDIS_URL=redis://MEMORYSTORE_IP:6379
CELERY_BROKER_URL=redis://MEMORYSTORE_IP:6379
CELERY_RESULT_BACKEND=redis://MEMORYSTORE_IP:6379
```

### Worker (.env.production)

```bash
CELERY_BROKER_URL=redis://MEMORYSTORE_IP:6379
CELERY_RESULT_BACKEND=redis://MEMORYSTORE_IP:6379
S3_WEATHER_BUCKET=gs://YOUR_PROJECT_ID-weather-data
GCP_PROJECT_ID=YOUR_PROJECT_ID
GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-key.json
```

## Testing Deployment

```bash
# Get service URLs
BACKEND_URL=$(gcloud run services describe weather-backend --region us-central1 --format="value(status.url)")
FRONTEND_URL=$(gcloud run services describe weather-frontend --region us-central1 --format="value(status.url)")

# Test backend health
curl $BACKEND_URL/api/health

# Test frontend
curl $FRONTEND_URL

# Trigger manual task
curl -X POST $BACKEND_URL/api/tasks/trigger-gfs \
  -H "Content-Type: application/json"
```

## Troubleshooting

### Check Logs

```bash
# Backend logs
gcloud run logs read weather-backend --region us-central1 --limit 100

# Worker logs
gcloud run logs read weather-worker --region us-central1 --limit 100

# Scheduler logs
gcloud scheduler jobs describe gfs-ingestion --location us-central1
```

### Common Issues

**1. Redis connection timeout**
- Ensure VPC connector is configured
- Verify Cloud Memorystore IP address
- Check firewall rules

**2. Task not executing**
- Check Cloud Scheduler is enabled
- Verify OIDC token audience
- Check worker service is running

**3. High costs**
- Set min-instances=0 for non-critical services
- Configure request timeout
- Use Cloud Storage lifecycle policies

## Migration Checklist

- [ ] Create Cloud Memorystore (Redis)
- [ ] Create Cloud Storage bucket
- [ ] Set up Secret Manager secrets
- [ ] Deploy backend service
- [ ] Deploy frontend service
- [ ] Deploy worker service
- [ ] Configure Cloud Scheduler jobs
- [ ] Set up VPC connector
- [ ] Configure custom domains
- [ ] Set up Cloud Build triggers
- [ ] Configure monitoring alerts
- [ ] Test end-to-end workflow
- [ ] Update DNS records
- [ ] Monitor costs

## Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Memorystore](https://cloud.google.com/memorystore)
- [Cloud Scheduler](https://cloud.google.com/scheduler)
- [Secret Manager](https://cloud.google.com/secret-manager)
- [Cloud Monitoring](https://cloud.google.com/monitoring)

---

**Status**: Ready for Cloud Run deployment
**Next Steps**: Follow Step 1 to set up external services
