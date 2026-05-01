#!/bin/bash
set -eux

# Source the shared configuration file
source ../../config.sh

gcloud run deploy before-sign-in-gen2 \
  --source ./src \
  --function beforeSignIn \
  --base-image nodejs22 \
  --region "${LOCATION}" \
  --build-service-account "projects/${PROJECT_ID}/serviceAccounts/${CLOUD_BUILD_RUNNER_SA_EMAIL}" \
  --service-account "${CLOUD_RUN_FUNCTIONS_SA_EMAIL}" \
  --set-env-vars "PROJECT_ID=${PROJECT_ID}"

# Grant invoker access to allUsers to comply with 'constraints/run.managed.requireInvokerIam'
gcloud run services add-iam-policy-binding before-sign-in-gen2 \
  --region "${LOCATION}" \
  --member="allUsers" \
  --role="roles/run.invoker"

