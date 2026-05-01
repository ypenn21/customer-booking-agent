#!/bin/bash
set -eux

# Source the shared configuration file
source ../../config.sh

# 1. Fetch the exact HTTPS trigger URL of your deployed Gen 2 function
FUNCTION_URI=$(gcloud run services describe before-sign-in-gen2 \
    --project=$PROJECT_ID \
    --region=$LOCATION \
    --format="value(status.url)")

# 2. Patch the Identity Platform configuration
curl -X PATCH \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  -H "Content-Type: application/json" \
  "https://identitytoolkit.googleapis.com/v2/projects/$PROJECT_ID/config?updateMask=blockingFunctions.triggers" \
  -d '{
    "blockingFunctions": {
      "triggers": {
        "beforeSignIn": {
          "functionUri": "'$FUNCTION_URI'"
        }
      }
    }
  }'

