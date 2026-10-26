#!/bin/bash
set -eux

source ../config.sh

# 2. Grant roles to the NEW service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_RUN_FUNCTIONS_SA_EMAIL}" \
    --role="roles/secretmanager.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_RUN_FUNCTIONS_SA_EMAIL}" \
    --role="roles/logging.logWriter"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_RUN_FUNCTIONS_SA_EMAIL}" \
    --role="roles/pubsub.subscriber"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_RUN_FUNCTIONS_SA_EMAIL}" \
    --role="roles/storage.objectViewer"

# 3. Grant the role to the DEFAULT Cloud Run Functions SA to act as this new SA
gcloud iam service-accounts add-iam-policy-binding $CLOUD_RUN_FUNCTIONS_SA_EMAIL \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcf-admin-robot.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser" \
    --project=$PROJECT_ID

