# Agent Auth and Deployment Troubleshooting

## Authentication Architecture & Token Vaulting

### Microsoft Entra ID Federation
The system uses **GCP Identity Platform (GCIP)** to federate identity with Microsoft Entra ID. This allows users to log in with their corporate or personal Microsoft accounts, inheriting existing organizational security policies.

### Secure Token Flow (Steps 5-8)
1. **App Registration (Step 5):** Microsoft provides a Client ID and Secret. Scopes like `Calendars.ReadWrite` and `offline_access` are configured to allow the agent to manage schedules.
2. **Identity Federation (Step 6):** GCIP is configured to trust Microsoft. The `offline_access` scope ensures a **Refresh Token** is issued for persistent access.
3. **Perimeter Security (Step 7):** **Identity-Aware Proxy (IAP)** handles the redirect to GCIP. The application code (FastAPI) never sees an unauthenticated request; it only receives a verified JWT.
4. **The Blocking Function (Step 8):** A "Before Sign-in" Cloud Function intercepts the Microsoft Access and Refresh tokens *before* the login is finalized on the Google side.

### Token Vaulting in Secret Manager
- **Storage:** Tokens are securely vaulted in **GCP Secret Manager** as a JSON secret named `ms-tokens-[USER_UID]`.
- **Offline Access:** The `refresh_token` allows agents to obtain new `access_token`s silently, enabling them to perform tasks even when the user is not actively logged into the app.
- **Security Benefit:** This "Server-Side Token Vault" pattern prevents sensitive credentials from ever being stored in the browser or touching the frontend application logic.

### Insights
- **Zero-Trust for Agents:** Agents use their own unique Service Account identities to access the vault, maintaining a strict least-privilege boundary.
- **Indefinite Persistence:** Using the Refresh Token, the Bookings Agent can perform calendar operations long after the initial login session has expired, provided the user hasn't revoked the app's permission.

---

## Issue: 500 INTERNAL Error during Deployment

### Symptom
When running `deploy_agent_engine.py` for either the `bookings` or `customers` agent, the deployment failed with a `google.genai.errors.ServerError: 500 INTERNAL`.

### Root Cause Analysis
The stack trace revealed a backend timeout in the Vertex AI Reasoning Engine control plane:
`generic::DEADLINE_EXCEEDED: Deadline missed (delayed locks): Delayed lock acquisition 57.4867 secs on tablet z3436_613180425`

**Root Cause:** Severe regional instability or resource contention in the `us-central1` region's Spanner backend for Reasoning Engines. This caused a deadlock during the creation/update of engine resources, preventing the deployment from completing even for minimal test agents.

---

## Resolution Steps

### 1. Diagnostic Verification
Created a minimal test script (`test_minimal_deploy.py`) to isolate the issue. The minimal deployment failed with the same `500 INTERNAL` error in `us-central1`, confirming the issue was region-specific and not related to the agent code or requirements.

### 2. Regional Migration
Transitioned the entire deployment pipeline to the `us-east1` region, which was verified as stable.

### 3. Configuration Refactoring
Updated the project configuration to be region-agnostic where possible:
- **`config.sh`**: Changed default `LOCATION` to `us-east1`.
- **Deployment Scripts**: Refactored `bookings/deploy_agent_engine.py` and `customers/deploy_agent_engine.py` to use the `LOCATION` environment variable instead of hardcoded strings.

### 4. Resource Cleanup
Identified and force-deleted "stuck" or duplicate reasoning engine instances in `us-central1` that were partially created during the failed attempts to prevent billing leakage and naming collisions.

### 5. Identity & IAM Alignment
Updated the **Agent Identity** principals in `config.sh` to match the new resource IDs in `us-east1`. These use the `principalSet://` format for granular IAM permissions:
- `CUSTOMERS_PRINCIPAL`: `principalSet://agents.global.org-419713829424.system.id.goog/resources/aiplatform/projects/48196429354/locations/us-east1/reasoningEngines/4902238563136962560`
- `BOOKINGS_PRINCIPAL`: `principalSet://agents.global.org-419713829424.system.id.goog/resources/aiplatform/projects/48196429354/locations/us-east1/reasoningEngines/3140205208928256000`

---

## Deployment Summary (Current State)

| Agent | Region | Resource ID |
| :--- | :--- | :--- |
| **Booking Assistant** | `us-east1` | `projects/48196429354/locations/us-east1/reasoningEngines/3140205208928256000` |
| **Customer Assistant** | `us-east1` | `projects/48196429354/locations/us-east1/reasoningEngines/4902238563136962560` |

**Verification:** Successful deployment confirmed. Documentation in `fast-api-fe/README.md` and environment variables in `config.sh` are updated to match this state.
