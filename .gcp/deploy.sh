#!/bin/bash
# Cloud Run Deployment Script for AI Weather Analytics Platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-""}
REGION=${GCP_REGION:-"us-central1"}
REDIS_INSTANCE=${REDIS_INSTANCE:-"weather-redis"}

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Weather Analytics - Cloud Run Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if project ID is set
if [ -z "$PROJECT_ID" ]; then
    echo -e "${YELLOW}Enter your GCP Project ID:${NC}"
    read PROJECT_ID
    if [ -z "$PROJECT_ID" ]; then
        echo -e "${RED}Error: Project ID is required${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}Using Project: $PROJECT_ID${NC}"
echo -e "${GREEN}Using Region: $REGION${NC}"
echo ""

# Set project
gcloud config set project $PROJECT_ID

# Function to enable APIs
enable_apis() {
    echo -e "${YELLOW}Enabling required GCP APIs...${NC}"

    apis=(
        "run.googleapis.com"
        "cloudbuild.googleapis.com"
        "cloudscheduler.googleapis.com"
        "secretmanager.googleapis.com"
        "redis.googleapis.com"
        "storage-api.googleapis.com"
        "monitoring.googleapis.com"
        "logging.googleapis.com"
        "vpcaccess.googleapis.com"
    )

    for api in "${apis[@]}"; do
        echo "Enabling $api..."
        gcloud services enable $api --quiet
    done

    echo -e "${GREEN}✓ APIs enabled${NC}"
    echo ""
}

# Function to create Cloud Memorystore (Redis)
create_redis() {
    echo -e "${YELLOW}Checking Cloud Memorystore (Redis)...${NC}"

    if gcloud redis instances describe $REDIS_INSTANCE --region=$REGION &> /dev/null; then
        echo -e "${GREEN}✓ Redis instance already exists${NC}"
        REDIS_HOST=$(gcloud redis instances describe $REDIS_INSTANCE --region=$REGION --format="value(host)")
        REDIS_PORT=$(gcloud redis instances describe $REDIS_INSTANCE --region=$REGION --format="value(port)")
        echo "  Host: $REDIS_HOST"
        echo "  Port: $REDIS_PORT"
    else
        echo "Creating Redis instance... (this takes ~5 minutes)"
        gcloud redis instances create $REDIS_INSTANCE \
            --size=1 \
            --region=$REGION \
            --redis-version=redis_7_0 \
            --tier=BASIC \
            --quiet

        REDIS_HOST=$(gcloud redis instances describe $REDIS_INSTANCE --region=$REGION --format="value(host)")
        REDIS_PORT=$(gcloud redis instances describe $REDIS_INSTANCE --region=$REGION --format="value(port)")
        echo -e "${GREEN}✓ Redis instance created${NC}"
    fi

    REDIS_URL="redis://$REDIS_HOST:$REDIS_PORT"
    echo ""
}

# Function to create Cloud Storage bucket
create_storage() {
    echo -e "${YELLOW}Checking Cloud Storage bucket...${NC}"

    BUCKET_NAME="$PROJECT_ID-weather-data"

    if gsutil ls -b gs://$BUCKET_NAME &> /dev/null; then
        echo -e "${GREEN}✓ Bucket already exists: gs://$BUCKET_NAME${NC}"
    else
        echo "Creating bucket..."
        gsutil mb -l $REGION gs://$BUCKET_NAME

        # Set lifecycle policy
        cat > /tmp/lifecycle.json <<EOF
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
        gsutil lifecycle set /tmp/lifecycle.json gs://$BUCKET_NAME
        echo -e "${GREEN}✓ Bucket created with 30-day retention${NC}"
    fi
    echo ""
}

# Function to create secrets
create_secrets() {
    echo -e "${YELLOW}Setting up Secret Manager...${NC}"

    # Create REDIS_URL secret
    if gcloud secrets describe REDIS_URL &> /dev/null; then
        echo "Updating REDIS_URL secret..."
        echo -n "$REDIS_URL" | gcloud secrets versions add REDIS_URL --data-file=-
    else
        echo "Creating REDIS_URL secret..."
        echo -n "$REDIS_URL" | gcloud secrets create REDIS_URL --data-file=-
    fi

    # Create S3_WEATHER_BUCKET secret
    if gcloud secrets describe S3_WEATHER_BUCKET &> /dev/null; then
        echo "S3_WEATHER_BUCKET secret already exists"
    else
        echo "Creating S3_WEATHER_BUCKET secret..."
        echo -n "gs://$PROJECT_ID-weather-data" | gcloud secrets create S3_WEATHER_BUCKET --data-file=-
    fi

    # Grant access to compute service account
    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
    SERVICE_ACCOUNT="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

    for secret in REDIS_URL S3_WEATHER_BUCKET; do
        gcloud secrets add-iam-policy-binding $secret \
            --member="serviceAccount:$SERVICE_ACCOUNT" \
            --role="roles/secretmanager.secretAccessor" \
            --quiet &> /dev/null
    done

    echo -e "${GREEN}✓ Secrets configured${NC}"
    echo ""
}

# Function to create VPC connector
create_vpc_connector() {
    echo -e "${YELLOW}Checking VPC connector...${NC}"

    if gcloud compute networks vpc-access connectors describe weather-connector --region=$REGION &> /dev/null; then
        echo -e "${GREEN}✓ VPC connector already exists${NC}"
    else
        echo "Creating VPC connector... (this takes ~3 minutes)"
        gcloud compute networks vpc-access connectors create weather-connector \
            --region=$REGION \
            --range=10.8.0.0/28 \
            --quiet
        echo -e "${GREEN}✓ VPC connector created${NC}"
    fi
    echo ""
}

# Function to build and deploy services
deploy_services() {
    echo -e "${YELLOW}Building and deploying services...${NC}"

    # Submit build to Cloud Build
    echo "Submitting build to Cloud Build..."
    gcloud builds submit \
        --config=.gcp/cloudbuild.yaml \
        --substitutions=_REDIS_IP=$REDIS_HOST \
        --quiet

    echo -e "${GREEN}✓ Services deployed${NC}"
    echo ""
}

# Function to set up Cloud Scheduler
setup_scheduler() {
    echo -e "${YELLOW}Setting up Cloud Scheduler...${NC}"

    # Get worker URL
    WORKER_URL=$(gcloud run services describe weather-worker --region=$REGION --format="value(status.url)")
    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
    SERVICE_ACCOUNT="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

    # Create GFS ingestion job (every 6 hours)
    if gcloud scheduler jobs describe gfs-ingestion --location=$REGION &> /dev/null; then
        echo "Updating gfs-ingestion job..."
        gcloud scheduler jobs update http gfs-ingestion \
            --location=$REGION \
            --schedule="0 */6 * * *" \
            --uri="$WORKER_URL/tasks/ingest-gfs" \
            --http-method=POST \
            --oidc-service-account-email=$SERVICE_ACCOUNT \
            --oidc-token-audience="$WORKER_URL" \
            --quiet
    else
        echo "Creating gfs-ingestion job..."
        gcloud scheduler jobs create http gfs-ingestion \
            --location=$REGION \
            --schedule="0 */6 * * *" \
            --uri="$WORKER_URL/tasks/ingest-gfs" \
            --http-method=POST \
            --oidc-service-account-email=$SERVICE_ACCOUNT \
            --oidc-token-audience="$WORKER_URL" \
            --quiet
    fi

    # Create HRRR ingestion job (hourly)
    if gcloud scheduler jobs describe hrrr-ingestion --location=$REGION &> /dev/null; then
        echo "Updating hrrr-ingestion job..."
        gcloud scheduler jobs update http hrrr-ingestion \
            --location=$REGION \
            --schedule="0 * * * *" \
            --uri="$WORKER_URL/tasks/ingest-hrrr" \
            --http-method=POST \
            --oidc-service-account-email=$SERVICE_ACCOUNT \
            --oidc-token-audience="$WORKER_URL" \
            --quiet
    else
        echo "Creating hrrr-ingestion job..."
        gcloud scheduler jobs create http hrrr-ingestion \
            --location=$REGION \
            --schedule="0 * * * *" \
            --uri="$WORKER_URL/tasks/ingest-hrrr" \
            --http-method=POST \
            --oidc-service-account-email=$SERVICE_ACCOUNT \
            --oidc-token-audience="$WORKER_URL" \
            --quiet
    fi

    echo -e "${GREEN}✓ Cloud Scheduler jobs configured${NC}"
    echo ""
}

# Function to display service URLs
show_urls() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Deployment Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    BACKEND_URL=$(gcloud run services describe weather-backend --region=$REGION --format="value(status.url)")
    FRONTEND_URL=$(gcloud run services describe weather-frontend --region=$REGION --format="value(status.url)")
    WORKER_URL=$(gcloud run services describe weather-worker --region=$REGION --format="value(status.url)")

    echo -e "${YELLOW}Service URLs:${NC}"
    echo "  Frontend:  $FRONTEND_URL"
    echo "  Backend:   $BACKEND_URL"
    echo "  Worker:    $WORKER_URL (internal)"
    echo ""

    echo -e "${YELLOW}Test commands:${NC}"
    echo "  curl $BACKEND_URL/api/health"
    echo "  curl $FRONTEND_URL"
    echo ""

    echo -e "${YELLOW}View logs:${NC}"
    echo "  gcloud run logs read weather-backend --region=$REGION --limit=50"
    echo "  gcloud run logs read weather-worker --region=$REGION --limit=50"
    echo ""

    echo -e "${YELLOW}Monitor costs:${NC}"
    echo "  https://console.cloud.google.com/billing/projects/$PROJECT_ID"
    echo ""
}

# Main deployment flow
main() {
    echo -e "${YELLOW}Starting deployment process...${NC}"
    echo ""

    enable_apis
    create_redis
    create_storage
    create_secrets
    create_vpc_connector
    deploy_services
    setup_scheduler
    show_urls

    echo -e "${GREEN}Deployment completed successfully!${NC}"
}

# Run main function
main
