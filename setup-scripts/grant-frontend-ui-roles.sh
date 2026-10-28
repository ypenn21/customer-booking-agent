#!/bin/bash
set -eux

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../config.sh"

SA_EMAIL="$FRONTEND_UI_SA_EMAIL"

# 1. Grant Log Writing access (Project Level)
# This allows the SA to write its own execution logs to Cloud Logging
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/logging.logWriter" \
    --condition=None

# 2. Grant Discovery Engine Viewer access
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/discoveryengine.viewer" \
    --condition=None

# 3. Grant Agent Registry Viewer access so fast-api-fe can discover the Orchestrator Agent
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/agentregistry.viewer" \
    --condition=None

# 4. Grant Vertex AI User access so fast-api-fe can manage sessions and query the discovered Orchestrator Engine
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/aiplatform.user" \
    --condition=None

echo "Service Account $SA_EMAIL configured successfully."

