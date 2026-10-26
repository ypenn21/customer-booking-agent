#!/bin/bash
# Cloud Build submission script for fast-api-fe

set -e

# Define PROJECT_ROOT
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)

# Load configuration (assumes running from project root or having config.sh accessible)
if [ -f "../config.sh" ]; then
    source ../config.sh
elif [ -f "./config.sh" ]; then
    source ./config.sh
fi

if [ -z "$PROJECT_ID" ]; then
    echo "Error: PROJECT_ID is not set. Please ensure config.sh is present and contains PROJECT_ID."
    exit 1
fi

COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "v1")

# Submit to Cloud Build from the root
echo "Submitting build to Cloud Build for project $PROJECT_ID from project root..."
cd "$PROJECT_ROOT"
gcloud builds submit --config .cloudbuild/build-fast-api-fe.yaml \
    --substitutions=COMMIT_SHA=$COMMIT_SHA \
    --project=$PROJECT_ID

echo "Cloud Build submission complete."
