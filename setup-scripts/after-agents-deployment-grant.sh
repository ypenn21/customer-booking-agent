#!/bin/bash
set -eux

# Run this script AFTER both the orchestrator and booking agents have been deployed.
# If ORCHESTRATOR_PRINCIPAL or BOOKINGS_PRINCIPAL are empty in config.sh, this script
# automatically discovers the latest deployed Reasoning Engine effective identities.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../config.sh"

discover_principal() {
    local display_name="$1"
    local raw_identity
    raw_identity=$(curl -s -H "Authorization: Bearer $(gcloud auth print-access-token)" \
        "https://${LOCATION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${LOCATION}/reasoningEngines" \
        | jq -r --arg NAME "${display_name}" '
            [.reasoningEngines[]? | select(.displayName == $NAME)]
            | sort_by(.createTime)
            | last
            | .spec.effectiveIdentity // empty
        ')
    if [[ -z "${raw_identity}" ]]; then
        echo "ERROR: Could not discover effectiveIdentity for Reasoning Engine with displayName='${display_name}'" >&2
        exit 1
    fi
    if [[ "${raw_identity}" == principal://* ]]; then
        echo "${raw_identity}"
    else
        echo "principal://${raw_identity}"
    fi
}

if [[ -z "${ORCHESTRATOR_PRINCIPAL:-}" ]]; then
    echo "Auto-discovering ORCHESTRATOR_PRINCIPAL for '${ORCHESTRATOR_AGENT_DISPLAY_NAME:-Orchestrator Agent}'..."
    ORCHESTRATOR_PRINCIPAL="$(discover_principal "${ORCHESTRATOR_AGENT_DISPLAY_NAME:-Orchestrator Agent}")"
fi

if [[ -z "${BOOKINGS_PRINCIPAL:-}" ]]; then
    echo "Auto-discovering BOOKINGS_PRINCIPAL for '${BOOKINGS_AGENT_DISPLAY_NAME:-Booking Assistant}'..."
    BOOKINGS_PRINCIPAL="$(discover_principal "${BOOKINGS_AGENT_DISPLAY_NAME:-Booking Assistant}")"
fi

echo "----------------------------------------------------------------"
echo "Granting roles to Orchestrator Agent..."
echo "Principal: ${ORCHESTRATOR_PRINCIPAL}"
echo "----------------------------------------------------------------"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="${ORCHESTRATOR_PRINCIPAL}" \
    --role="roles/serviceusage.serviceUsageConsumer" \
    --condition=None

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="${ORCHESTRATOR_PRINCIPAL}" \
    --role="roles/browser" \
    --condition=None

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="${ORCHESTRATOR_PRINCIPAL}" \
    --role="roles/cloudtrace.agent" \
    --condition=None

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="${ORCHESTRATOR_PRINCIPAL}" \
    --role="roles/logging.logWriter" \
    --condition=None

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="${ORCHESTRATOR_PRINCIPAL}" \
    --role="roles/monitoring.metricWriter" \
    --condition=None

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="${ORCHESTRATOR_PRINCIPAL}" \
    --role="roles/telemetry.tracesWriter" \
    --condition=None

# TODO: scope this permission down to only the Orchestrator -> Booking Agent engine deployments
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="${ORCHESTRATOR_PRINCIPAL}" \
    --role="roles/aiplatform.user" \
    --condition=None

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="${ORCHESTRATOR_PRINCIPAL}" \
    --role="roles/agentregistry.viewer" \
    --condition=None

echo ""
echo "----------------------------------------------------------------"
echo "Granting roles to Bookings Agent..."
echo "Principal: ${BOOKINGS_PRINCIPAL}"
echo "----------------------------------------------------------------"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="${BOOKINGS_PRINCIPAL}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="${BOOKINGS_PRINCIPAL}" \
    --role="roles/serviceusage.serviceUsageConsumer" \
    --condition=None

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="${BOOKINGS_PRINCIPAL}" \
    --role="roles/browser" \
    --condition=None

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="${BOOKINGS_PRINCIPAL}" \
    --role="roles/cloudtrace.agent" \
    --condition=None

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="${BOOKINGS_PRINCIPAL}" \
    --role="roles/logging.logWriter" \
    --condition=None

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="${BOOKINGS_PRINCIPAL}" \
    --role="roles/monitoring.metricWriter" \
    --condition=None

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="${BOOKINGS_PRINCIPAL}" \
    --role="roles/telemetry.tracesWriter" \
    --condition=None



echo ""
echo "Done."
