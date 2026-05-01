# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# NOTE: This is a template. Run the setup-scripts/grant-cloud-build-roles.sh script to create the runnable version
# that replaces the 'REPLACE_ME' field in the Service Account

steps:
  # Build the container image for fast-api-fe
  - name: 'gcr.io/cloud-builders/docker'
    dir: 'fast-api-fe'
    args:
      - 'build'
      - '-t'
      - 'us-central1-docker.pkg.dev/REPLACE_ME_PROJECT_ID/agent-repo/fast-api-fe:$COMMIT_SHA'
      - '-t'
      - 'us-central1-docker.pkg.dev/REPLACE_ME_PROJECT_ID/agent-repo/fast-api-fe:latest'
      - '.'

# Images to be pushed upon successful build
images:
  - 'us-central1-docker.pkg.dev/REPLACE_ME_PROJECT_ID/agent-repo/fast-api-fe:$COMMIT_SHA'
  - 'us-central1-docker.pkg.dev/REPLACE_ME_PROJECT_ID/agent-repo/fast-api-fe:latest'

options:
  default_logs_bucket_behavior: REGIONAL_USER_OWNED_BUCKET

serviceAccount: 'REPLACE_ME_SA'

