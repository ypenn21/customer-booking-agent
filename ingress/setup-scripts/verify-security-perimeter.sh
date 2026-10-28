#!/bin/bash
set -eux
source "$(dirname "$0")/../../config.sh"

export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false
export CLOUDSDK_CONTEXT_AWARE_USE_ECP_HTTP_PROXY=false

echo "=== 1. Verifying Cloud Armor Backend Policy Attachment ==="
ATTACHED_POLICY=$(gcloud compute backend-services describe frontend-ui-backend --global --project="${PROJECT_ID}" --format="value(securityPolicy)" || echo "None")
echo "Attached Policy on frontend-ui-backend: ${ATTACHED_POLICY}"

echo "=== 2. Verifying Cloud Armor Edge Rate-Limiting Policy ==="
gcloud compute security-policies describe edge-waf-policy --project="${PROJECT_ID}" --format="json(rules)" || true

echo "=== 3. Verifying Regional Model Armor Template (orchestrator-agent) ==="
CLOUDSDK_API_ENDPOINT_OVERRIDES_MODELARMOR="https://modelarmor.${LOCATION}.rep.googleapis.com/" \
  gcloud beta model-armor templates describe orchestrator-agent \
  --location="${LOCATION}" \
  --project="${PROJECT_ID}"

echo "=== 4. Verifying Agent Gateway (booking-agent-gateway) ==="
gcloud beta network-services agent-gateways describe booking-agent-gateway \
  --location="${LOCATION}" \
  --project="${PROJECT_ID}"

echo "=== 5. Verifying Service Extensions AuthzExtension (booking-ma-authz-ext) ==="
gcloud beta service-extensions authz-extensions describe booking-ma-authz-ext \
  --location="${LOCATION}" \
  --project="${PROJECT_ID}"

echo "=== 6. Verifying Network Security AuthzPolicy (booking-ma-authz-policy) ==="
gcloud beta network-security authz-policies describe booking-ma-authz-policy \
  --location="${LOCATION}" \
  --project="${PROJECT_ID}"
