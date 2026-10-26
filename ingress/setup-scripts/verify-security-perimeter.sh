#!/bin/bash
set -eux
source "$(dirname "$0")/../../config.sh"

echo "=== 1. Verifying Cloud Armor Backend Policy Attachment ==="
ATTACHED_POLICY=$(gcloud compute backend-services describe frontend-ui-backend --global --format="value(securityPolicy)" || echo "None")
echo "Attached Policy on frontend-ui-backend: ${ATTACHED_POLICY}"

echo "=== 2. Verifying Cloud Armor Edge Rate-Limiting Policy ==="
gcloud compute security-policies describe edge-waf-policy --format="json(rules)" || true

echo "=== 3. Verifying Model Armor Template Deployment ==="
curl -s -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://modelarmor.googleapis.com/v1alpha1/projects/${PROJECT_ID}/locations/${LOCATION}/templates/booking-service-guardrails" || true

echo "=== 4. Verifying Agent Gateway Deployment ==="
curl -s -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://${LOCATION}-enterpriseagent.googleapis.com/v1alpha1/projects/${PROJECT_ID}/locations/${LOCATION}/agentGateways/booking-agent-gateway" || true
