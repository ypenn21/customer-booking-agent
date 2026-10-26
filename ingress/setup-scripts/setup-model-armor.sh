#!/bin/bash
set -eux
source "$(dirname "$0")/../../config.sh"

# Ensure gcloud uses the correct modelarmor endpoint without local certificate proxy issues
export CLOUDSDK_API_ENDPOINT_OVERRIDES_MODELARMOR="https://modelarmor.googleapis.com/"
export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false
export CLOUDSDK_CONTEXT_AWARE_USE_ECP_HTTP_PROXY=false

FULL_URI="projects/${PROJECT_ID}/locations/global/floorSetting"

echo "Provisioning Model Armor Guardrails via gcloud CLI..."

gcloud alpha model-armor floorsettings update \
  --full-uri="${FULL_URI}" \
  --pi-and-jailbreak-filter-settings-enforcement=enabled \
  --pi-and-jailbreak-filter-settings-confidence-level=high \
  --basic-config-filter-enforcement=ENABLED \
  --rai-settings-filters='[{"filterType": "HATE_SPEECH", "confidenceLevel": "HIGH"}]' \
  --enable-floor-setting-enforcement=TRUE

echo ""
echo "Verifying Model Armor Floor Setting configuration via gcloud CLI..."
gcloud alpha model-armor floorsettings describe --full-uri="${FULL_URI}"



