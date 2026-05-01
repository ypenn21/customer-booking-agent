#!/bin/bash
set -eux

source ../config.sh

# 1. Create the custom Service Account
gcloud iam service-accounts create $CLOUD_BUILD_RUNNER_SA \
    --display-name="Cloud Build Runner Service Account"

# 2. Grant roles to the NEW service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_BUILD_RUNNER_SA_EMAIL}" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_BUILD_RUNNER_SA_EMAIL}" \
    --role="roles/logging.logWriter"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_BUILD_RUNNER_SA_EMAIL}" \
    --role="roles/artifactregistry.writer"

# 3. Grant the role to the DEFAULT Cloud Build SA to act as this new SA
# This allows the default Cloud Build process to "assume" this custom identity
gcloud iam service-accounts add-iam-policy-binding $CLOUD_BUILD_RUNNER_SA_EMAIL \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser" \
    --project=$PROJECT_ID

CLOUD_BUILD_SA="projects/${PROJECT_ID}/serviceAccounts/${CLOUD_BUILD_RUNNER_SA_EMAIL}"
sed -e "s|REPLACE_ME_SA|$CLOUD_BUILD_SA|g" \
    -e "s|REPLACE_ME_PROJECT_ID|$PROJECT_ID|g" \
    ../.cloudbuild/build-fast-api-fe.yaml.tpl > ../.cloudbuild/build-fast-api-fe.yaml

