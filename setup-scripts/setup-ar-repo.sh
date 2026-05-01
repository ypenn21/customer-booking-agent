#!/bin/bash

# Source the shared configuration file
source ../config.sh

gcloud artifacts repositories create "${REPO_NAME}" \
    --repository-format=docker \
    --location="${LOCATION}" \
    --description="Docker repository for Scenario 1 AI Agents"

