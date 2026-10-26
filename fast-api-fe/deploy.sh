#!/bin/bash

# Source the shared configuration file
source ../config.sh

echo $PROJECT_ID
# Construct the full image URL
IMAGE="${LOCATION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/fast-api-fe:latest"
ORCHESTRATOR_DISPLAY_NAME="${ORCHESTRATOR_AGENT_DISPLAY_NAME:-Orchestrator Agent}"

gcloud run deploy $FRONTEND_IMAGE_NAME \
  --image=$IMAGE \
  --region=$LOCATION \
  --port=8080 \
  --ingress=internal-and-cloud-load-balancing \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},LOCATION=${LOCATION},AGENT_REGISTRY_LOCATION=${LOCATION},ORCHESTRATOR_AGENT_DISPLAY_NAME=${ORCHESTRATOR_DISPLAY_NAME},IAP_EXPECTED_AUDIENCE=${IAP_EXPECTED_AUDIENCE}" \
  --memory=512Mi \
  --cpu=2 \
  --no-default-url \
  --service-account="${FRONTEND_UI_SA_EMAIL}"

