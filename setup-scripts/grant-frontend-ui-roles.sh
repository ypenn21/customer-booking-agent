#!/bin/bash
set -eux

source "../config.sh"

SA_EMAIL="$FRONTEND_UI_SA_EMAIL"

# 1. Create the Service Account
gcloud iam service-accounts create $FRONTEND_UI_SA \
    --display-name="SA for Agent Engine Execution"

# 2. Grant Log Writing access (Project Level)
# This allows the SA to write its own execution logs to Cloud Logging
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/logging.logWriter"

# 3. Grant Access to call the Agent
# Project-wide access to all agents (Simpler)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/discoveryengine.viewer"

echo "Service Account $SA_EMAIL created and configured successfully."

