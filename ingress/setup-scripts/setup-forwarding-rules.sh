#!/bin/bash
set -eux

# Source the shared configuration file
source ../../config.sh
source ../../gcip-config.sh

# 1. Create or verify URL map
if gcloud compute url-maps describe frontend-ui-map --global --project="${PROJECT_ID}" &>/dev/null; then
    echo "URL map frontend-ui-map already exists."
else
    echo "Creating URL map frontend-ui-map..."
    gcloud compute url-maps create frontend-ui-map \
        --project="${PROJECT_ID}" \
        --default-service frontend-ui-backend
fi

# 2. Create or verify SSL certificate
if gcloud compute ssl-certificates describe frontend-ui-cert --global --project="${PROJECT_ID}" &>/dev/null; then
    echo "SSL cert frontend-ui-cert already exists."
else
    echo "Creating SSL cert frontend-ui-cert..."
    gcloud compute ssl-certificates create frontend-ui-cert \
        --project="${PROJECT_ID}" \
        --description="bookings ingress cert" \
        --domains="${DOMAIN}" \
        --global
fi

# 3. Target HTTPS proxy
if gcloud compute target-https-proxies describe https-lb-proxy --global --project="${PROJECT_ID}" &>/dev/null; then
    echo "Updating target HTTPS proxy https-lb-proxy..."
    gcloud compute target-https-proxies update https-lb-proxy \
        --project="${PROJECT_ID}" \
        --url-map=frontend-ui-map \
        --ssl-certificates=frontend-ui-cert
else
    echo "Creating target HTTPS proxy https-lb-proxy..."
    gcloud compute target-https-proxies create https-lb-proxy \
        --project="${PROJECT_ID}" \
        --url-map=frontend-ui-map \
        --ssl-certificates=frontend-ui-cert
fi

# 4. Forwarding rule
if gcloud compute forwarding-rules describe https-forwarding-rule --global --project="${PROJECT_ID}" &>/dev/null; then
    echo "Forwarding rule https-forwarding-rule already exists."
else
    echo "Creating forwarding rule https-forwarding-rule..."
    gcloud compute forwarding-rules create https-forwarding-rule \
        --project="${PROJECT_ID}" \
        --address=lb-ip-cr-ue-f \
        --target-https-proxy=https-lb-proxy \
        --ports=443 \
        --global
fi
