#!/bin/bash
set -eux

#NOTE: run this AFTER the customers agent has been deployed and CUSTOMERS_ENGINE_ID has been set in ../config.sh 
source ../config.sh

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${FRONTEND_UI_SA_EMAIL}" \
  --role="roles/aiplatform.user"
  #TODO: fix this condition so that the frontend can only communicate with the customers engine
  #--condition="title=SpecificAgentAccess,expression=resource.name.startsWith('//aiplatform.googleapis.com/${CUSTOMERS_ENGINE_ID}')"

