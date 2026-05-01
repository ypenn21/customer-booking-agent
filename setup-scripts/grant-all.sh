#!/bin/bash
set -eux

./grant-frontend-ui-roles.sh
./grant-cloud-build-roles.sh
./grant-cloud-run-functions-roles.sh
./grant-before-sign-in-hander-roles.sh

