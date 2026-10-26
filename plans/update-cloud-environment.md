# Implementation Plan - Update Cloud Environment for Orchestrator Agent

## 1. 🔍 Analysis & Context
*   **Objective:** Update the existing Google Cloud environment to deploy the new Orchestrator agent and reconfigure the FastAPI frontend to communicate with it instead of the legacy Customers agent. This includes rebuilding the container image due to source code changes.
*   **Affected Files:**
    *   `config.sh` (Local configuration file)
    *   `fast-api-fe/deploy.sh` (Deployment script)
    *   `orchestrator/deploy_agent_engine.py` (Orchestrator deployment script)
    *   `fast-api-fe/build-on-cloud-build.sh` (Build script)
*   **Key Dependencies:**
    *   Google Cloud SDK (gcloud)
    *   Vertex AI Agent Engine (Reasoning Engine)
    *   Cloud Build
    *   Cloud Run
*   **Risks/Unknowns:**
    *   **Org Policy Constraint:** The `run.managed.requireInvokerIam` policy is enforced, so `deploy.sh` must not use `--no-invoker-iam-check`.
    *   **Build Artifacts:** Ensuring the latest code is packaged into the Docker image.

## 2. 📋 Checklist
- [ ] Step 1: Deploy Orchestrator Agent
- [ ] Step 2: Update Local Configuration
- [ ] Step 3: Grant IAM Permissions for Orchestrator
- [ ] Step 4: Build FastAPI Frontend Image
- [ ] Step 5: Redeploy FastAPI Frontend
- [ ] Verification

## 3. 📝 Step-by-Step Implementation Details

### Step 1: Deploy Orchestrator Agent
*   **Goal:** Create a new Reasoning Engine resource for the Orchestrator.
*   **Action:**
    *   Run the deployment script:
        ```bash
        source config.sh
        uv run python orchestrator/deploy_agent_engine.py
        ```
    *   Note the resource name printed at the end (e.g., `projects/[PROJECT_ID]/locations/[LOCATION]/reasoningEngines/[ID]`).
*   **Verification:** `gcloud ai reasoning-engines list` shows "Orchestrator Agent".

### Step 2: Update Local Configuration
*   **Goal:** Update `config.sh` with the new Engine ID, Principal, and IAP Audience.
*   **Action:**
    *   Open `config.sh`.
    *   Set `ORCHESTRATOR_ENGINE_ID` to the full resource name from Step 1.
    *   Update `ORCHESTRATOR_PRINCIPAL` following the format: `principal://agents.global.org-${ORG_ID}.system.id.goog/resources/aiplatform/${ORCHESTRATOR_ENGINE_ID}`.
        *   **Note:** Use `principal://` (singular), NOT `principalSet://`. Using `principalSet://` will cause IAM policy update failures.
    *   Update `IAP_EXPECTED_AUDIENCE` (retrieved via `gcloud compute backend-services list`).
*   **Verification:** `source config.sh && echo $ORCHESTRATOR_ENGINE_ID` returns the new ID.

### Step 3: Grant IAM Permissions for Orchestrator
*   **Goal:** Enable cross-agent communication and frontend access.
*   **Action:**
    *   Run the general agents grant script:
        ```bash
        cd setup-scripts
        ./after-agents-deployment-grant.sh
        ```
    *   **Note:** This step is critical to prevent `403 PermissionDenied` errors when the Orchestrator attempts to call the Bookings agent via `agent_engines.get()`. It grants the Orchestrator agent's system identity the `roles/aiplatform.user` role.
    *   Run the orchestrator-specific grant script:
        ```bash
        ./after-orchestrator-agent-deployment-grant.sh
        cd ..
        ```
*   **Verification:** Check IAM policy bindings for `ORCHESTRATOR_PRINCIPAL` in the Cloud Console.

### Step 4: Build FastAPI Frontend Image
*   **Goal:** Package the refactored frontend code into a new container image.
*   **Action:**
    *   Execute the build script:
        ```bash
        cd fast-api-fe
        ./build-on-cloud-build.sh
        cd ..
        ```
*   **Verification:** Check Artifact Registry for a new image tagged with the latest commit SHA or `latest`.

### Step 5: Redeploy FastAPI Frontend
*   **Goal:** Update the Cloud Run service with the new image and environment variables.
*   **Action:**
    *   **Important:** Ensure `fast-api-fe/deploy.sh` does **NOT** contain the `--no-invoker-iam-check` flag to avoid Org Policy violations.
    *   Execute the deployment script:
        ```bash
        cd fast-api-fe
        ./deploy.sh
        cd ..
        ```
*   **Verification:** `gcloud run services describe frontend-ui` shows the new `ORCHESTRATOR_ENGINE_ID`.

## 4. 🧪 Testing Strategy
*   **Manual Verification:**
    1.  Access the public URL of the chat frontend.
    2.  Send a message like "Hello".
    3.  Verify the response is successful and check Cloud Logging for "Orchestrator Agent" log entries.
    4.  Send a message like "Make a hotel booking in London" to verify delegation.

## 5. ✅ Success Criteria
*   The Orchestrator agent is successfully deployed.
*   The FastAPI frontend is running the latest code and pointing to the Orchestrator.
*   Deployment is compliant with the `run.managed.requireInvokerIam` Org Policy.
