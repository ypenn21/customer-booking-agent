#!/bin/bash
set -eux
source "$(dirname "$0")/../../config.sh"

TEMPLATE_ID="orchestrator-agent"
FULL_URI="projects/${PROJECT_ID}/locations/global/floorSetting"

# Ensure gcloud uses the correct modelarmor endpoint without local certificate proxy issues
export CLOUDSDK_API_ENDPOINT_OVERRIDES_MODELARMOR="https://modelarmor.googleapis.com/"
export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false
export CLOUDSDK_CONTEXT_AWARE_USE_ECP_HTTP_PROXY=false

echo "============================================================"
echo "Step 1: Provisioning Global Model Armor Floor Setting..."
echo "============================================================"
gcloud alpha model-armor floorsettings update \
  --full-uri="${FULL_URI}" \
  --pi-and-jailbreak-filter-settings-enforcement=enabled \
  --pi-and-jailbreak-filter-settings-confidence-level=high \
  --basic-config-filter-enforcement=ENABLED \
  --rai-settings-filters='[{"filterType": "HATE_SPEECH", "confidenceLevel": "HIGH"}]' \
  --enable-floor-setting-enforcement=TRUE

gcloud alpha model-armor floorsettings describe --full-uri="${FULL_URI}"

echo ""
echo "============================================================"
echo "Step 2: Provisioning Regional Model Armor Template (${TEMPLATE_ID} in ${LOCATION})..."
echo "============================================================"
export CLOUDSDK_API_ENDPOINT_OVERRIDES_MODELARMOR="https://modelarmor.${LOCATION}.rep.googleapis.com/"

if gcloud beta model-armor templates describe "${TEMPLATE_ID}" --location="${LOCATION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Template ${TEMPLATE_ID} already exists in ${LOCATION}. Updating..."
  gcloud beta model-armor templates update "${TEMPLATE_ID}" \
    --location="${LOCATION}" \
    --project="${PROJECT_ID}" \
    --pi-and-jailbreak-filter-settings-enforcement=ENABLED \
    --pi-and-jailbreak-filter-settings-confidence-level=MEDIUM_AND_ABOVE \
    --malicious-uri-filter-settings-enforcement=ENABLED \
    --basic-config-filter-enforcement=ENABLED \
    --rai-settings-filters='[{"filterType":"HATE_SPEECH","confidenceLevel":"HIGH"},{"filterType":"DANGEROUS","confidenceLevel":"HIGH"},{"filterType":"SEXUALLY_EXPLICIT","confidenceLevel":"HIGH"},{"filterType":"HARASSMENT","confidenceLevel":"HIGH"}]' \
    --template-metadata-enforcement-type=INSPECT_AND_BLOCK
else
  echo "Creating regional Model Armor template ${TEMPLATE_ID} in ${LOCATION}..."
  gcloud beta model-armor templates create "${TEMPLATE_ID}" \
    --location="${LOCATION}" \
    --project="${PROJECT_ID}" \
    --pi-and-jailbreak-filter-settings-enforcement=ENABLED \
    --pi-and-jailbreak-filter-settings-confidence-level=MEDIUM_AND_ABOVE \
    --malicious-uri-filter-settings-enforcement=ENABLED \
    --basic-config-filter-enforcement=ENABLED \
    --rai-settings-filters='[{"filterType":"HATE_SPEECH","confidenceLevel":"HIGH"},{"filterType":"DANGEROUS","confidenceLevel":"HIGH"},{"filterType":"SEXUALLY_EXPLICIT","confidenceLevel":"HIGH"},{"filterType":"HARASSMENT","confidenceLevel":"HIGH"}]' \
    --template-metadata-enforcement-type=INSPECT_AND_BLOCK
fi

echo ""
echo "Verifying Regional Model Armor Template (${TEMPLATE_ID}):"
gcloud beta model-armor templates describe "${TEMPLATE_ID}" \
  --location="${LOCATION}" \
  --project="${PROJECT_ID}"
