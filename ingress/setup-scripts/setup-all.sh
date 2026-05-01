#!/bin/bash
set -eux

# Requements: frontend service deployed
./setup-ingress.sh

# Requirements: Load balancer backend "frontend-ui-backend" exists (from setup-ingress.sh)
./setup-forwarding-rules.sh

# Requirements: URL map exists (from setup-forwarding-rules.sh)
./setup-url-map.sh


