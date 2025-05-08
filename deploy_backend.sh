#!/bin/bash

# Ensure the script fails on error
set -e

# Load environment variables from the .env file
if [ -f .env ]; then
  export $(cat .env | xargs)
fi

# Validate environment variables
if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ] || [ -z "$IMAGE_NAME" ]; then
  echo "ERROR: Missing required environment variables."
  exit 1
fi

# Set your Google Cloud project variables
DOCKER_IMAGE="gcr.io/${PROJECT_ID}/${IMAGE_NAME}"

# Step 1: Authenticate with Google Cloud
echo "Authenticating with Google Cloud..."
gcloud auth login
gcloud config set project ${PROJECT_ID}

# Step 2: Build the Docker image
echo "Building Docker image..."
docker build -t ${DOCKER_IMAGE} .

# Step 3: Push the Docker image to Google Container Registry
echo "Pushing Docker image to Google Container Registry..."
docker push ${DOCKER_IMAGE}

# Step 4: Deploy the image to Google Cloud Run
echo "Deploying the backend to Google Cloud Run..."
gcloud run deploy ${IMAGE_NAME} \
  --image ${DOCKER_IMAGE} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated

# Step 5: Output the URL of the deployed service
echo "Deployment successful!"
echo "You can access your backend at:"
gcloud run services describe ${IMAGE_NAME} --platform managed --region ${REGION} --format "value(status.url)"
