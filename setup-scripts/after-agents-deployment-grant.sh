#!/bin/bash
set -eux

# Run this script AFTER both the orchestrator and booking agents have been deployed
# Ensure that the Agent Identities have been set in the config.sh file
source ../config.sh

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
