# 🚀 Lumi Educational Analytics API Deployment Guide

This document outlines the standard procedure for building and deploying new code updates to the `lumi-educational-api` service running on **Google Cloud Run** in the **`us-east4` (Northern Virginia)** region.

## 📝 Prerequisites

1.  **GCP Project ID:** `swye360-prod-01`
2.  **Cloud Run Service:** `lumi-educational-api`
3.  **Artifact Registry:** `lumi-educational-api` (in `us-east4`)
4.  **Custom Domain:** `https://lumi.classsight.ai`
5.  **Tools:** `gcloud` CLI and Docker are installed and configured.

## 1\. ⚙️ Set Deployment Variables

Before starting any deployment, always set the required environment variables in your terminal. This ensures all commands target the correct service and region.

```bash
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
```

-----

## 2\. 📦 Build and Push New Container Image

This step uses **Cloud Build** to build a new Docker image containing your updated code and pushes it to **Artifact Registry**.

1.  **Review Dependencies:** Ensure your `requirements.txt` file and your `Dockerfile` are up-to-date with any new dependencies.
2.  **Run Build Command:** Submit the build context (your project directory) to Google Cloud.

<!-- end list -->

```bash
# Authenticate Docker (usually only needed once per setup)
gcloud auth configure-docker ${GCP_REGION}-docker.pkg.dev

# Build and Push the new image using the defined variables
echo "Building and pushing new image: ${IMAGE_URL}"
gcloud builds submit \
  --tag ${IMAGE_URL} \
  --project ${GCP_PROJECT_ID}
```

> **Wait for `SUCCESS`:** The build logs will confirm success with a `STATUS: SUCCESS` message.

-----

## 3\. ☁️ Deploy New Revision to Cloud Run

After the image is pushed, deploy a new revision of the **`lumi-educational-api`** service. Cloud Run will automatically handle traffic migration from the old revision to the new one.

1.  **Run Deploy Command:** Use the image URL from the previous step. You must re-specify all environment variables (`--set-env-vars`), including the PostgreSQL credentials and the `OPENAI_API_KEY`, to ensure they are carried over to the new revision.

<!-- end list -->

```bash
echo "Deploying new revision using image: ${IMAGE_URL}"
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_URL} \
  --region ${GCP_REGION} \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars POSTGRES_HOST=aws-0-us-east-1.pooler.supabase.com,POSTGRES_PORT=5432,POSTGRES_DB=postgres,POSTGRES_USER=swye360_agent.ytpwaryvxdrwtevltgwp,POSTGRES_PASSWORD=aiengineerswye360agent,POSTGRES_SCHEMA=public,API_HOST=0.0.0.0,API_PORT=8000,DEBUG=False,OPENAI_API_KEY=... \
  --project ${GCP_PROJECT_ID}
```

> **⚠️ Security Note:** It is highly recommended to migrate sensitive secrets like `POSTGRES_PASSWORD` and `OPENAI_API_KEY` to **Google Cloud Secret Manager** and reference them in the deployment command using the `--update-secrets` flag.

-----

## 4\. 🔗 Verification

1.  **Check Service Status:** Verify the deployment succeeded and the new revision is serving traffic.
2.  **Test Endpoint:** Access the API via the custom domain to ensure all updates are live and functional.

**Custom Domain URL:**
`https://lumi.classsight.ai`

**Internal Cloud Run URL:**
`https://lumi-educational-api-359545177183.us-east4.run.app` (The `359...` number is your project number)

-----

## 5\. 🔑 Recommended Improvement: Secret Manager

For better security, remove plain text secrets from your deployment script and use **Secret Manager**.

**Replace this:**

```bash
... POSTGRES_PASSWORD=aiengineerswye360agent, ... OPENAI_API_KEY="sk-proj--..."
```

**With this structure (assuming secrets are stored in Secret Manager):**

```bash
# This is a conceptual example for the deployment command
gcloud run deploy ...
  --set-env-vars POSTGRES_HOST=...,POSTGRES_DB=...,POSTGRES_SCHEMA=... \
  --update-secrets=POSTGRES_PASSWORD=postgres-secret:latest,OPENAI_API_KEY=openai-key-secret:latest \
  --project ${GCP_PROJECT_ID}
```
