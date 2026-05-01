#!/bin/bash
set -eux

# Source the shared configuration file
source ../../config.sh
source ../../gcip-config.sh

# Your existing resources
URL_MAP_NAME="frontend-ui-map"
DEFAULT_BACKEND="frontend-auth-backend"
NEG_NAME="frontend-ui-neg" # from ingress setup script

UI_BACKEND="frontend-ui-backend"
AUTH_BACKEND="frontend-auth-backend"

gcloud compute url-maps export $URL_MAP_NAME --destination=tmp-url-map.yaml --global

# Append the config to the end of the file using '>>'
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


echo "apply new url map:"
cat tmp-url-map.yaml

gcloud compute url-maps import $URL_MAP_NAME --source=tmp-url-map.yaml --global
