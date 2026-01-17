#!/bin/bash

# ====================================================================
# Lumi Educational Analytics API Deployment Script
# ====================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Lumi Educational Analytics API Deployment${NC}"
echo -e "${BLUE}===============================================${NC}\n"

# ====================================================================
# 1. Configuration
# ====================================================================

# Set your GCP Project ID
export GCP_PROJECT_ID="swye360-prod-01"
# Set the region (Northern Virginia)
export GCP_REGION="us-east4"
# Set the service name (used for Artifact Registry and Cloud Run)
export SERVICE_NAME="lumi-educational-api"
# Image name (append a tag like v3.1.0 for versioning, or use 'latest' for simple updates)
export IMAGE_TAG="latest"
export IMAGE_NAME="${SERVICE_NAME}-image"

# Full path to your container image
export IMAGE_URL="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${SERVICE_NAME}/${IMAGE_NAME}:${IMAGE_TAG}"

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "  Project ID:   $GCP_PROJECT_ID"
echo "  Region:       $GCP_REGION"
echo "  Service:      $SERVICE_NAME"
echo "  Image:        $IMAGE_URL"
echo "  Tag:          $IMAGE_TAG"
echo ""

# ====================================================================
# 2. Check Prerequisites
# ====================================================================

echo -e "${YELLOW}🔍 Checking prerequisites...${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if user is logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "."; then
    echo -e "${YELLOW}⚠️  Not logged in to gcloud. Please authenticate...${NC}"
    gcloud auth login
fi

# Check if project exists
if ! gcloud projects describe $GCP_PROJECT_ID &> /dev/null; then
    echo -e "${RED}❌ Project '$GCP_PROJECT_ID' not found or access denied${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}\n"

# ====================================================================
# 3. Set GCP Project
# ====================================================================

echo -e "${YELLOW}⚙️  Setting GCP project...${NC}"
gcloud config set project $GCP_PROJECT_ID
echo -e "${GREEN}✅ Project set to $GCP_PROJECT_ID${NC}\n"

# ====================================================================
# 4. Build and Push Docker Image
# ====================================================================

echo -e "${YELLOW}📦 Building Docker image...${NC}"
echo "Image: $IMAGE_URL"
echo ""

# Authenticate Docker to Artifact Registry
echo "Authenticating Docker to Artifact Registry..."
gcloud auth configure-docker ${GCP_REGION}-docker.pkg.dev

# Build and push using Cloud Build
echo -e "${BLUE}Starting Cloud Build...${NC}"
gcloud builds submit \
    --tag ${IMAGE_URL} \
    --project ${GCP_PROJECT_ID} \
    --timeout 30m

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Image built and pushed successfully${NC}"
else
    echo -e "${RED}❌ Build failed${NC}"
    exit 1
fi

echo ""

# ====================================================================
# 5. Deploy to Cloud Run
# ====================================================================

echo -e "${YELLOW}☁️  Deploying to Cloud Run...${NC}"

# Read environment variables from .env file if exists
ENV_VARS=""
if [ -f .env.production ]; then
    echo "Loading environment variables from .env.production..."
    while IFS= read -r line; do
        # Skip comments and empty lines
        [[ $line =~ ^#.* ]] && continue
        [[ -z $line ]] && continue

        key=$(echo $line | cut -d '=' -f 1)
        value=$(echo $line | cut -d '=' -f 2-)

        # Add to environment variables string
        if [ -z "$ENV_VARS" ]; then
            ENV_VARS="${key}=${value}"
        else
            ENV_VARS="${ENV_VARS},${key}=${value}"
        fi
    done < .env.production
fi

# Add mandatory environment variables from deployment guide
MANDATORY_ENV="POSTGRES_HOST=aws-0-us-east-1.pooler.supabase.com,POSTGRES_PORT=5432,POSTGRES_DB=postgres,POSTGRES_USER=swye360_agent.ytpwaryvxdrwtevltgwp,POSTGRES_PASSWORD=aiengineerswye360agent,POSTGRES_SCHEMA=public,API_HOST=0.0.0.0,API_PORT=8080,DEBUG=False,OPENAI_API_KEY="

# Merge environment variables
if [ -n "$ENV_VARS" ]; then
    ALL_ENV_VARS="${MANDATORY_ENV},${ENV_VARS}"
else
    ALL_ENV_VARS="${MANDATORY_ENV}"
fi

echo -e "${BLUE}Deploying service '$SERVICE_NAME'...${NC}"
echo "Region: $GCP_REGION"
echo "Image: $IMAGE_URL"
echo ""

# Deploy to Cloud Run
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_URL} \
    --region ${GCP_REGION} \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --set-env-vars ${ALL_ENV_VARS} \
    --cpu 2 \
    --memory 2Gi \
    --min-instances 1 \
    --max-instances 10 \
    --concurrency 80 \
    --timeout 300s \
    --project ${GCP_PROJECT_ID} \
    --quiet

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Deployment successful${NC}"
else
    echo -e "${RED}❌ Deployment failed${NC}"
    exit 1
fi

echo ""

# ====================================================================
# 6. Get Service Information
# ====================================================================

echo -e "${YELLOW}📊 Service Information:${NC}"

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region ${GCP_REGION} \
    --format="value(status.url)" \
    --project ${GCP_PROJECT_ID})

echo -e "${GREEN}Service URL:${NC} $SERVICE_URL"
echo -e "${GREEN}Custom Domain:${NC} https://lumi.classsight.ai"
echo ""

# ====================================================================
# 7. Test Deployment
# ====================================================================

echo -e "${YELLOW}🧪 Testing deployment...${NC}"

# Wait a moment for the service to be ready
echo "Waiting for service to be ready..."
sleep 10

# Test health endpoint
HEALTH_URL="${SERVICE_URL}/health"
echo -e "Testing health endpoint: $HEALTH_URL"

if curl -s --max-time 10 $HEALTH_URL | grep -q "healthy"; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${YELLOW}⚠️  Health check may be delayed. Service is deploying...${NC}"
fi

echo ""

# ====================================================================
# 8. Cleanup (Optional)
# ====================================================================

# Uncomment to clean old images (keeps last 5)
# echo -e "${YELLOW}🧹 Cleaning old images...${NC}"
# gcloud artifacts docker images list ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${SERVICE_NAME} \
#     --format='value(digest)' \
#     --sort-by=~UPDATE_TIME \
#     | tail -n +6 \
#     | xargs -I {} gcloud artifacts docker images delete ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${SERVICE_NAME}@{} \
#     --quiet

echo -e "${BLUE}===============================================${NC}"
echo -e "${GREEN}🚀 Deployment Complete!${NC}"
echo -e "${BLUE}===============================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Test the API: curl $SERVICE_URL/health"
echo "2. Visit: https://lumi.classsight.ai"
echo "3. Monitor logs: gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}' --limit=10"
echo ""
