#!/bin/bash
set -eux

echo "Starting complete ingress and security DMZ provisioning..."

# Requirements: frontend service deployed
./setup-ingress.sh

# Requirements: Load balancer backend "frontend-ui-backend" exists (from setup-ingress.sh)
./setup-forwarding-rules.sh

# Requirements: URL map exists (from setup-forwarding-rules.sh)
./setup-url-map.sh

# Provision Model Armor guardrails and Vertex AI Agent Gateway
./setup-model-armor.sh
./setup-agent-gateway.sh

echo "All platform-native security guardrails deployed successfully."
