#!/bin/bash
set -eux

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../config.sh"

# 2. Grant roles to the NEW service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_RUN_FUNCTIONS_SA_EMAIL}" \
    --role="roles/secretmanager.admin" \
    --condition=None

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_RUN_FUNCTIONS_SA_EMAIL}" \
    --role="roles/logging.logWriter" \
    --condition=None

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_RUN_FUNCTIONS_SA_EMAIL}" \
    --role="roles/pubsub.subscriber" \
    --condition=None

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_RUN_FUNCTIONS_SA_EMAIL}" \
    --role="roles/storage.objectViewer" \
    --condition=None

# 3. Grant the role to the DEFAULT Cloud Run Functions SA to act as this new SA
gcloud iam service-accounts add-iam-policy-binding $CLOUD_RUN_FUNCTIONS_SA_EMAIL \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcf-admin-robot.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser" \
    --project=$PROJECT_ID \
    --condition=None

