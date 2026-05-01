#!/bin/bash

# Source the shared configuration file
source ../config.sh

# Construct the full image URL
IMAGE="${LOCATION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/fast-api-fe:latest"

gcloud run deploy $FRONTEND_IMAGE_NAME \
  --image=$IMAGE \
  --region=$LOCATION \
  --port=8080 \
  --ingress=internal-and-cloud-load-balancing \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},LOCATION=${LOCATION},CUSTOMERS_ENGINE_ID=${CUSTOMERS_ENGINE_ID},IAP_EXPECTED_AUDIENCE=${IAP_EXPECTED_AUDIENCE}" \
  --memory=512Mi \
  --cpu=2 \
  --service-account="${FRONTEND_UI_SA_EMAIL}"

# Grant invoker access to allUsers. 
# This is required when 'constraints/run.managed.requireInvokerIam' is enforced.
# Public access is still restricted by the Load Balancer ingress setting.
gcloud run services add-iam-policy-binding $FRONTEND_IMAGE_NAME \
  --region=$LOCATION \
  --member="allUsers" \
  --role="roles/run.invoker"

