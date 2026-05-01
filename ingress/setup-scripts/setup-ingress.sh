#!/bin/bash
set -eux

# Source the shared configuration file
source ../../config.sh
source ../../gcip-config.sh

# Create the Cloud Armor security policy
gcloud compute security-policies create edge-waf-policy \
    --description "WAF protection for Scenario 1"

# Add a security rule to block common web attacks (SQLi, XSS)
gcloud compute security-policies rules create 1000 \
    --security-policy edge-waf-policy \
    --expression "evaluatePreconfiguredExpr('sqli-stable') || evaluatePreconfiguredExpr('xss-stable')" \
    --action "deny-403" \
    --description "Block SQLi and XSS"

# Create the IAP service account if it doesn't already exist
gcloud beta services identity create \
    --service=iap.googleapis.com

# Grant roles/run.invoker EXCLUSIVELY to the IAP Service Agent
# This ensures that bypassing IAP via the *.run.app URL results in a 403 (AC-01)
gcloud run services add-iam-policy-binding "${FRONTEND_IMAGE_NAME}" \
    --region "${LOCATION}" \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-iap.iam.gserviceaccount.com" \
    --role="roles/run.invoker"

gcloud compute network-endpoint-groups create frontend-ui-neg \
    --region="${LOCATION}" \
    --network-endpoint-type=serverless \
    --cloud-run-service="${FRONTEND_IMAGE_NAME}"

gcloud compute backend-services create frontend-ui-backend \
    --load-balancing-scheme=EXTERNAL_MANAGED \
    --global

gcloud compute backend-services add-backend frontend-ui-backend \
    --global \
    --network-endpoint-group=frontend-ui-neg \
    --network-endpoint-group-region="${LOCATION}"


# Create a temporary IAP settings file with placeholders replaced
cp iap-settings.yaml iap-settings-temp.yaml
sed -i "s/{{domain}}/${DOMAIN}/g" iap-settings-temp.yaml
sed -i "s/{{apiKey}}/${API_KEY}/g" iap-settings-temp.yaml
sed -i "s/{{tenantId}}/${TENANT_ID}/g" iap-settings-temp.yaml

gcloud iap settings set iap-settings-temp.yaml \
    --project="${PROJECT_ID}" \
    --resource-type=backend-services \
    --service=frontend-ui-backend

# Clean up the temporary file
rm iap-settings-temp.yaml


# Configure a seperate backend to use as an unprotected path the handler.js client library for authentication
gcloud compute backend-services create frontend-auth-backend \
    --project="${PROJECT_ID}" \
    --global \
    --load-balancing-scheme=EXTERNAL_MANAGED

gcloud compute backend-services add-backend frontend-auth-backend \
    --project="${PROJECT_ID}" \
    --global \
    --network-endpoint-group=frontend-ui-neg \
    --network-endpoint-group-region="${LOCATION}"

