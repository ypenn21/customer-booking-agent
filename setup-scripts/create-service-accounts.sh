#!/bin/bash
set -eux

source ../config.sh

gcloud iam service-accounts create $CLOUD_BUILD_RUNNER_SA \
    --display-name="Cloud Build Runner Service Account"

gcloud iam service-accounts create $FRONTEND_UI_SA \
    --display-name="SA for Agent Engine Execution"

gcloud iam service-accounts create $CLOUD_RUN_FUNCTIONS_SA \
    --display-name="Cloud Run Functions before-signin handler for IAP"

