#!/bin/bash
# Local build script for fast-api-fe

set -e

# Build the docker image locally
echo "Building Docker image locally..."
docker build -t fast-api-fe:latest .

echo "Local build complete."
