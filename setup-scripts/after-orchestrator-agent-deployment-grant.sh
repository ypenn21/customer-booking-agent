#!/bin/bash
set -eux

# NOTE: fast-api-fe dynamically discovers the Orchestrator Reasoning Engine via Agent Registry.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../config.sh"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${FRONTEND_UI_SA_EMAIL}" \
  --role="roles/aiplatform.user" \
  --condition=None
  #TODO: fix this condition so that the frontend can only communicate with the orchestrator engine
  #--condition="title=SpecificAgentAccess,expression=resource.name.startsWith('//aiplatform.googleapis.com/${ORCHESTRATOR_ENGINE_ID}')"

