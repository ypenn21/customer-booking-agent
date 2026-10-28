#!/bin/bash

set -eux

# Load environment configuration
source "$(dirname "$0")/../../config.sh"

GATEWAY_ID="booking-agent-gateway"
AUTHZ_EXT_ID="booking-ma-authz-ext"
AUTHZ_POLICY_ID="booking-ma-authz-policy"
TEMPLATE_ID="orchestrator-agent"

# Resolve numeric Project Number if not set in config.sh
PROJECT_NUMBER="${PROJECT_NUMBER:-$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")}"

GATEWAY_YAML="$(mktemp -t agent-gateway-XXXXXX)"
AUTHZ_EXT_YAML="$(mktemp -t authz-ext-XXXXXX)"
AUTHZ_POLICY_YAML="$(mktemp -t authz-policy-XXXXXX)"

echo "============================================================"
echo "Provisioning Single Unified Agent Gateway: ${GATEWAY_ID}"
echo "Project ID:     ${PROJECT_ID}"
echo "Project Number: ${PROJECT_NUMBER}"
echo "Location:       ${LOCATION}"
echo "============================================================"

# ------------------------------------------------------------
# Step 0: Ensure Required APIs & Service Identities Exist
# ------------------------------------------------------------
echo "Step 0: Ensuring Network Services, Network Security, Model Armor, DLP, Agent Registry, and AI Platform APIs are enabled..."
gcloud services enable \
    networkservices.googleapis.com \
    networksecurity.googleapis.com \
    modelarmor.googleapis.com \
    dlp.googleapis.com \
    aiplatform.googleapis.com \
    agentregistry.googleapis.com \
    --project="${PROJECT_ID}"

gcloud beta services identity create --service=networkservices.googleapis.com --project="${PROJECT_ID}" || true
gcloud beta services identity create --service=aiplatform.googleapis.com --project="${PROJECT_ID}" || true
gcloud beta services identity create --service=modelarmor.googleapis.com --project="${PROJECT_ID}" || true


# ------------------------------------------------------------
# Step 1: Create Unified Agent Gateway (MCP Protocol Spec)
# ------------------------------------------------------------
echo "Step 1: Creating Agent Gateway ${GATEWAY_ID}..."

cat <<EOF > "${GATEWAY_YAML}"
name: projects/${PROJECT_ID}/locations/${LOCATION}/agentGateways/${GATEWAY_ID}
protocols:
  - MCP
googleManaged:
  governedAccessPath: CLIENT_TO_AGENT
EOF

gcloud beta network-services agent-gateways import "${GATEWAY_ID}" \
    --source="${GATEWAY_YAML}" \
    --location="${LOCATION}" \
    --project="${PROJECT_ID}"


# ------------------------------------------------------------
# Step 2: Create Model Armor Authorization Extension
# (Importing the first authz-extension triggers GCP to provision
#  service-${PROJECT_NUMBER}@gcp-sa-dep.iam.gserviceaccount.com)
# ------------------------------------------------------------
echo "Step 2: Creating Model Armor Authz Extension ${AUTHZ_EXT_ID}..."

cat <<EOF > "${AUTHZ_EXT_YAML}"
name: projects/${PROJECT_ID}/locations/${LOCATION}/authzExtensions/${AUTHZ_EXT_ID}
service: modelarmor.${LOCATION}.rep.googleapis.com
metadata:
  model_armor_settings: '[
    {
      "response_template_id": "projects/${PROJECT_NUMBER}/locations/${LOCATION}/templates/${TEMPLATE_ID}",
      "request_template_id": "projects/${PROJECT_NUMBER}/locations/${LOCATION}/templates/${TEMPLATE_ID}"
    }
  ]'
failOpen: false
timeout: 3s
EOF

gcloud beta service-extensions authz-extensions import "${AUTHZ_EXT_ID}" \
    --source="${AUTHZ_EXT_YAML}" \
    --location="${LOCATION}" \
    --project="${PROJECT_ID}"


# ------------------------------------------------------------
# Step 3: Grant Required IAM Roles to Google Service Agents
# ------------------------------------------------------------
echo "Step 3: Granting mandatory IAM roles to Service Agents..."

# Service Dependency SA (Network Services / Extension Callouts)
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-dep.iam.gserviceaccount.com" \
    --role="roles/modelarmor.user" \
    --condition=None \
    --quiet

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-dep.iam.gserviceaccount.com" \
    --role="roles/modelarmor.calloutUser" \
    --condition=None \
    --quiet

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-dep.iam.gserviceaccount.com" \
    --role="roles/serviceusage.serviceUsageConsumer" \
    --condition=None \
    --quiet

# Vertex AI Reasoning Engine SA (Inlining Agent Gateway & Model Armor)
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
    --role="roles/modelarmor.calloutUser" \
    --condition=None \
    --quiet

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
    --role="roles/modelarmor.user" \
    --condition=None \
    --quiet

# Model Armor Service Agent (Sensitive Data Protection / DLP Inspection)
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-modelarmor.iam.gserviceaccount.com" \
    --role="roles/modelarmor.serviceAgent" \
    --condition=None \
    --quiet


# ------------------------------------------------------------
# Step 4: Create Content Authorization Policy
# ------------------------------------------------------------
echo "Step 4: Binding Content Authz Policy ${AUTHZ_POLICY_ID} to Agent Gateway..."

cat <<EOF > "${AUTHZ_POLICY_YAML}"
name: projects/${PROJECT_ID}/locations/${LOCATION}/authzPolicies/${AUTHZ_POLICY_ID}
target:
  resources:
    - "projects/${PROJECT_ID}/locations/${LOCATION}/agentGateways/${GATEWAY_ID}"
policyProfile: CONTENT_AUTHZ
action: CUSTOM
customProvider:
  authzExtension:
    resources:
      - "projects/${PROJECT_ID}/locations/${LOCATION}/authzExtensions/${AUTHZ_EXT_ID}"
EOF

gcloud beta network-security authz-policies import "${AUTHZ_POLICY_ID}" \
    --source="${AUTHZ_POLICY_YAML}" \
    --location="${LOCATION}" \
    --project="${PROJECT_ID}"

# Clean up temporary YAML files
rm -f "${GATEWAY_YAML}" "${AUTHZ_EXT_YAML}" "${AUTHZ_POLICY_YAML}"


# ------------------------------------------------------------
# Step 5: Verification
# ------------------------------------------------------------
echo ""
echo "============================================================"
echo "Verifying Gateway & Security Resources"
echo "============================================================"

echo "--> Describing Agent Gateway:"
gcloud beta network-services agent-gateways describe "${GATEWAY_ID}" \
    --location="${LOCATION}" \
    --project="${PROJECT_ID}"

echo "--> Describing Model Armor Authz Extension:"
gcloud beta service-extensions authz-extensions describe "${AUTHZ_EXT_ID}" \
    --location="${LOCATION}" \
    --project="${PROJECT_ID}"

echo "--> Describing Content Authz Policy:"
gcloud beta network-security authz-policies describe "${AUTHZ_POLICY_ID}" \
    --location="${LOCATION}" \
    --project="${PROJECT_ID}"
