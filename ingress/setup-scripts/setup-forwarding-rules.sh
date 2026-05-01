#!/bin/bash
set -eux

# Source the shared configuration file
source ../../config.sh
source ../../gcip-config.sh

# Create a URL map
gcloud compute url-maps create frontend-ui-map \
    --default-service frontend-ui-backend

# Create the certificate
gcloud compute ssl-certificates create frontend-ui-cert \
    --description="bookings ingress cert" \
    --domains="${DOMAIN}" \
    --global

# Create a target HTTPS proxy
gcloud compute target-https-proxies create https-lb-proxy \
    --url-map=frontend-ui-map \
    --ssl-certificates=frontend-ui-cert

# Create a forwarding rule
gcloud compute forwarding-rules create https-forwarding-rule \
    --address=lb-ip-cr-ue-f \
    --target-https-proxy=https-lb-proxy \
    --ports=443 \
    --global
