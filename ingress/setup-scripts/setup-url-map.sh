#!/bin/bash
set -eux

# Source the shared configuration file
source ../../config.sh
source ../../gcip-config.sh

URL_MAP_NAME="frontend-ui-map"
UI_BACKEND="frontend-ui-backend"
AUTH_BACKEND="frontend-auth-backend"

gcloud compute url-maps export $URL_MAP_NAME --destination=tmp-url-map.yaml --global --project="${PROJECT_ID}"

if grep -q "matcher1" tmp-url-map.yaml; then
  echo "URL map matcher1 already present in ${URL_MAP_NAME}. Skipping append."
else
  cat <<EOF >> tmp-url-map.yaml
hostRules:
- hosts:
  - ${DOMAIN}
  pathMatcher: matcher1
pathMatchers:
- defaultService: global/backendServices/${UI_BACKEND}
  name: matcher1
  pathRules:
  - paths:
    - /auth/*
    - /auth
    service: global/backendServices/${AUTH_BACKEND}
EOF
fi

echo "Applying URL map config:"
cat tmp-url-map.yaml

gcloud compute url-maps import $URL_MAP_NAME --source=tmp-url-map.yaml --global --project="${PROJECT_ID}" --quiet

rm -f tmp-url-map.yaml
