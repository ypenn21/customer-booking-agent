#!/bin/bash

# Shared configuration for shell scripts

# Required:
export PROJECT_ID="$(gcloud config get-value project)"
export PROJECT_NUMBER="$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")"
export ORG_ID="$(gcloud projects describe ${PROJECT_ID} --format="value(parent.id)")"
export LOCATION="us-central1"

# IAM Settings
FRONTEND_UI_SA="frontend-ui-sa"
FRONTEND_UI_SA_EMAIL="${FRONTEND_UI_SA}@${PROJECT_ID}.iam.gserviceaccount.com"
CLOUD_BUILD_RUNNER_SA="cloud-build-runner"
CLOUD_BUILD_RUNNER_SA_EMAIL="${CLOUD_BUILD_RUNNER_SA}@${PROJECT_ID}.iam.gserviceaccount.com"
CLOUD_RUN_FUNCTIONS_SA="before-sign-in-sa"
CLOUD_RUN_FUNCTIONS_SA_EMAIL="${CLOUD_RUN_FUNCTIONS_SA}@${PROJECT_ID}.iam.gserviceaccount.com"

# Docker Image Settings
REPO_NAME="agent-repo"
FRONTEND_IMAGE_NAME="frontend-ui"

# IAP JWT expected Aud Claim
export IAP_EXPECTED_AUDIENCE=""

# Optional Overrides:
# STAGING_BUCKET=""

export CUSTOMERS_ENGINE_ID=""
export BOOKINGS_ENGINE_ID=""

CUSTOMERS_PRINCIPAL=""
BOOKINGS_PRINCIPAL=""

