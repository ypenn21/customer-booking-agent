#!/bin/bash
set -eux

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../config.sh"

# 2. Grant roles to the NEW service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_BUILD_RUNNER_SA_EMAIL}" \
    --role="roles/storage.admin" \
    --condition=None

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_BUILD_RUNNER_SA_EMAIL}" \
    --role="roles/logging.logWriter" \
    --condition=None

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_BUILD_RUNNER_SA_EMAIL}" \
    --role="roles/artifactregistry.writer" \
    --condition=None

# 3. Grant the role to the DEFAULT Cloud Build SA to act as this new SA
# This allows the default Cloud Build process to "assume" this custom identity
gcloud iam service-accounts add-iam-policy-binding $CLOUD_BUILD_RUNNER_SA_EMAIL \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser" \
    --project=$PROJECT_ID \
    --condition=None

CLOUD_BUILD_SA="projects/${PROJECT_ID}/serviceAccounts/${CLOUD_BUILD_RUNNER_SA_EMAIL}"
sed -e "s|REPLACE_ME_SA|$CLOUD_BUILD_SA|g" \
    -e "s|REPLACE_ME_PROJECT_ID|$PROJECT_ID|g" \
    "${SCRIPT_DIR}/../.cloudbuild/build-fast-api-fe.yaml.tpl" > "${SCRIPT_DIR}/../.cloudbuild/build-fast-api-fe.yaml"

