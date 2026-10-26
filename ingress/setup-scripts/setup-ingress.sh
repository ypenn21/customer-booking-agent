#!/bin/bash
set -eux

# Source the shared configuration file
source ../../config.sh
source ../../gcip-config.sh

# 1. Create or verify Cloud Armor security policy
if gcloud compute security-policies describe edge-waf-policy --project="${PROJECT_ID}" &>/dev/null; then
    echo "Security policy edge-waf-policy already exists."
else
    echo "Creating security policy edge-waf-policy..."
    gcloud compute security-policies create edge-waf-policy \
        --project="${PROJECT_ID}" \
        --description "WAF protection for Scenario 1"
fi

# 2. Rule 1000: SQLi & XSS protection
# if gcloud compute security-policies rules describe 1000 --security-policy=edge-waf-policy --project="${PROJECT_ID}" &>/dev/null; then
#     echo "Updating rule 1000 on edge-waf-policy..."
#     gcloud compute security-policies rules update 1000 \
#         --security-policy edge-waf-policy \
#         --project="${PROJECT_ID}" \
#         --expression "!request.path.startsWith('/auth') && (evaluatePreconfiguredExpr('sqli-stable') || evaluatePreconfiguredExpr('xss-stable'))" \
#         --action "deny-403" \
#         --description "Block SQLi and XSS"
# else
#     echo "Creating rule 1000 on edge-waf-policy..."
#     gcloud compute security-policies rules create 1000 \
#         --security-policy edge-waf-policy \
#         --project="${PROJECT_ID}" \
#         --expression "!request.path.startsWith('/auth') && (evaluatePreconfiguredExpr('sqli-stable') || evaluatePreconfiguredExpr('xss-stable'))" \
#         --action "deny-403" \
#         --description "Block SQLi and XSS"
# fi

# 3. Rule 2000: IP Rate limiting (60 req/min per IP)
if gcloud compute security-policies rules describe 2000 --security-policy=edge-waf-policy --project="${PROJECT_ID}" &>/dev/null; then
    echo "Updating rule 2000 on edge-waf-policy..."
    gcloud compute security-policies rules update 2000 \
        --security-policy edge-waf-policy \
        --project="${PROJECT_ID}" \
        --expression "true" \
        --action "rate-based-ban" \
        --rate-limit-threshold-count 60 \
        --rate-limit-threshold-interval-sec 60 \
        --ban-duration-sec 600 \
        --conform-action "allow" \
        --exceed-action "deny-429" \
        --enforce-on-key "IP" \
        --description "Prevent prompt brute-force and Denial-of-Wallet attacks"
else
    echo "Creating rule 2000 on edge-waf-policy..."
    gcloud compute security-policies rules create 2000 \
        --security-policy edge-waf-policy \
        --project="${PROJECT_ID}" \
        --expression "true" \
        --action "rate-based-ban" \
        --rate-limit-threshold-count 60 \
        --rate-limit-threshold-interval-sec 60 \
        --ban-duration-sec 600 \
        --conform-action "allow" \
        --exceed-action "deny-429" \
        --enforce-on-key "IP" \
        --description "Prevent prompt brute-force and Denial-of-Wallet attacks"
fi

# 4. Create the IAP service account if it doesn't already exist
gcloud beta services identity create \
    --service=iap.googleapis.com \
    --project="${PROJECT_ID}" || true

# 5. Serverless NEG
if gcloud compute network-endpoint-groups describe frontend-ui-neg --region="${LOCATION}" --project="${PROJECT_ID}" &>/dev/null; then
    echo "NEG frontend-ui-neg already exists."
else
    echo "Creating NEG frontend-ui-neg..."
    gcloud compute network-endpoint-groups create frontend-ui-neg \
        --project="${PROJECT_ID}" \
        --region="${LOCATION}" \
        --network-endpoint-type=serverless \
        --cloud-run-service="${FRONTEND_IMAGE_NAME}"
fi

# 6. Backend Service: frontend-ui-backend
if gcloud compute backend-services describe frontend-ui-backend --global --project="${PROJECT_ID}" &>/dev/null; then
    echo "Updating frontend-ui-backend with security policy..."
    gcloud compute backend-services update frontend-ui-backend \
        --project="${PROJECT_ID}" \
        --global \
        --security-policy=edge-waf-policy
else
    echo "Creating frontend-ui-backend..."
    gcloud compute backend-services create frontend-ui-backend \
        --project="${PROJECT_ID}" \
        --load-balancing-scheme=EXTERNAL_MANAGED \
        --global \
        --security-policy=edge-waf-policy

    gcloud compute backend-services add-backend frontend-ui-backend \
        --project="${PROJECT_ID}" \
        --global \
        --network-endpoint-group=frontend-ui-neg \
        --network-endpoint-group-region="${LOCATION}"
fi

# 7. Apply IAP settings
sed -e "s/{{domain}}/${DOMAIN}/g" \
    -e "s/{{apiKey}}/${API_KEY}/g" \
    -e "s/{{tenantId}}/${TENANT_ID}/g" \
    iap-settings.yaml > iap-settings-temp.yaml

gcloud iap settings set iap-settings-temp.yaml \
    --project="${PROJECT_ID}" \
    --resource-type=backend-services \
    --service=frontend-ui-backend

rm -f iap-settings-temp.yaml

# 8. Backend Service: frontend-auth-backend
if gcloud compute backend-services describe frontend-auth-backend --global --project="${PROJECT_ID}" &>/dev/null; then
    echo "Updating frontend-auth-backend with security policy..."
    gcloud compute backend-services update frontend-auth-backend \
        --project="${PROJECT_ID}" \
        --global \
        --security-policy=edge-waf-policy
else
    echo "Creating frontend-auth-backend..."
    gcloud compute backend-services create frontend-auth-backend \
        --project="${PROJECT_ID}" \
        --global \
        --load-balancing-scheme=EXTERNAL_MANAGED \
        --security-policy=edge-waf-policy

    gcloud compute backend-services add-backend frontend-auth-backend \
        --project="${PROJECT_ID}" \
        --global \
        --network-endpoint-group=frontend-ui-neg \
        --network-endpoint-group-region="${LOCATION}"
fi

# 9. Ensure IAP IAM policy binding on project-level iap_web and frontend-ui-backend
gcloud iap web add-iam-policy-binding \
    --project="${PROJECT_ID}" \
    --member=allUsers \
    --role=roles/iap.httpsResourceAccessor || true

gcloud iap web add-iam-policy-binding \
    --project="${PROJECT_ID}" \
    --resource-type=backend-services \
    --service=frontend-ui-backend \
    --member=allUsers \
    --role=roles/iap.httpsResourceAccessor || true

