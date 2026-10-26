#!/bin/bash
set -eux

# Create a global static IP address
gcloud compute addresses create lb-ip-cr-ue-f \
    --ip-version=IPV4 \
    --network-tier=PREMIUM \
    --global

gcloud compute addresses describe lb-ip-cr-ue-f --global --format="value(address)"

