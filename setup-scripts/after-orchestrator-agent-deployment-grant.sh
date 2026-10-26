#!/bin/bash
set -eux

#NOTE: run this AFTER the orchestrator agent has been deployed and ORCHESTRATOR_ENGINE_ID has been set in ../config.sh 
source ../config.sh

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${FRONTEND_UI_SA_EMAIL}" \
  --role="roles/aiplatform.user"
  #TODO: fix this condition so that the frontend can only communicate with the orchestrator engine
  #--condition="title=SpecificAgentAccess,expression=resource.name.startsWith('//aiplatform.googleapis.com/${ORCHESTRATOR_ENGINE_ID}')"

