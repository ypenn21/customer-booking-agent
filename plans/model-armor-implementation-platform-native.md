# Model Armor & Vertex AI Agent Gateway Platform-Native Security Architecture

## Executive Summary

This document provides the full implementation record and architectural blueprint for the platform-native security perimeter deployed across the **Customer Booking Agent** multi-agent system (`Orchestrator Agent`, `Booking Assistant`, and `Customer Assistant`). 

All guardrails and ingress/egress policies are implemented using native Google Cloud `gcloud` CLI commands, Vertex AI Reasoning Engine SDK (`google-adk`), Model Armor Floor Settings, and Vertex AI Agent Gateways.

---

## Architecture Diagram

```
[ User / Client Request ]
           │
           │ HTTP / gRPC streamQuery
           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. Frontend Gateway (`fast-api-fe/services/agent_client.py`)           │
│    • `client = vertexai.Client(...)`                                    │
│    • `engine = client.agent_engines.get(...)`                           │
│    • `engine.stream_query(...)`                                         │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     │ Routed via Agent Gateway Config
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. Single Unified Agent Gateway (`booking-agent-gateway`)               │
│    • Location: `us-central1`                                            │
│    • Access Path: `googleManaged: CLIENT_TO_AGENT`                      │
│    • Protocols: `[MCP]`                                                 │
│    • Registry Scope: Default Project Registry (`us-central1`)          │
├─────────────────────────────────────────────────────────────────────────┤
│ 3. Content Authorization Policy (`booking-ma-authz-policy`)              │
│    • `policyProfile: CONTENT_AUTHZ` (Inspects prompt body)             │
│    • Action: `CUSTOM` (Delegates to Model Armor AuthzExtension)         │
├─────────────────────────────────────────────────────────────────────────┤
│ 4. Model Armor Authorization Extension (`booking-ma-authz-ext`)         │
│    • Endpoint: `modelarmor.us-central1.rep.googleapis.com`             │
│    • Template Target: `projects/${PROJECT_NUMBER}/locations/global/floorSetting` │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                        ┌────────────┴────────────┐
                        │                         │
             [ 🛡️ Security Violation ]      [ ✅ Clean Prompt ]
                        │                         │
            Prompt BLOCKED at Gateway   Forwarded to Target Agent
            (Never reaches LLM)         in Agent Registry:
                                         • Orchestrator Engine (`1818476233864773632`)
                                         • Bookings Engine (`697851783812218880`)
                                         • Customers Engine (`1067146953256599552`)
```

---

## Configured Components & Scripts

### 1. Shared Configuration (`config.sh`)
Centralized environment variables mapping shared Reasoning Engine instances and principals:
* `PROJECT_ID`: `agent-security-patterns`
* `PROJECT_NUMBER`: `48196429354`
* `LOCATION`: `us-central1`
* `CUSTOMERS_ENGINE_ID`: `projects/48196429354/locations/us-central1/reasoningEngines/1067146953256599552`
* `BOOKINGS_ENGINE_ID`: `projects/48196429354/locations/us-central1/reasoningEngines/697851783812218880`
* `ORCHESTRATOR_ENGINE_ID`: `projects/48196429354/locations/us-central1/reasoningEngines/1818476233864773632`

---

### 2. Model Armor Floor Setting Provisioning (`ingress/setup-scripts/setup-model-armor.sh`)
Establishes project-wide baseline guardrails enforced automatically across all Model Armor callouts:
* **Resource Path:** `projects/agent-security-patterns/locations/global/floorSetting`
* **Prompt Injection & Jailbreak:** `filterEnforcement: ENABLED`, `confidenceLevel: HIGH`
* **Responsible AI Filters:** `filterType: HATE_SPEECH`, `confidenceLevel: HIGH`
* **Sensitive Data Protection (SDP/DLP):** `basicConfig: { filterEnforcement: ENABLED }`
* **Enforcement:** `enableFloorSettingEnforcement: true`

```bash
gcloud alpha model-armor floorsettings update \
  --full-uri="projects/agent-security-patterns/locations/global/floorSetting" \
  --pi-and-jailbreak-filter-settings-enforcement=enabled \
  --pi-and-jailbreak-filter-settings-confidence-level=high \
  --basic-config-filter-enforcement=ENABLED \
  --rai-settings-filters='[{"filterType": "HATE_SPEECH", "confidenceLevel": "HIGH"}]' \
  --enable-floor-setting-enforcement=TRUE
```

---

### 3. Agent Gateway & Content Authz Policy (`ingress/setup-scripts/setup-agent-gateway.sh`)
Provisions a single unified Agent Gateway governing all three Reasoning Engines in the project registry:

1. **Agent Gateway (`booking-agent-gateway`):**
   * Command: `gcloud network-services agent-gateways import booking-agent-gateway --location=us-central1`
   * Spec: `protocols: [MCP]`, `googleManaged: { governedAccessPath: CLIENT_TO_AGENT }`.

2. **Model Armor Authorization Extension (`booking-ma-authz-ext`):**
   * Command: `gcloud service-extensions authz-extensions import booking-ma-authz-ext --location=us-central1`
   * Service: `modelarmor.us-central1.rep.googleapis.com`
   * Metadata settings: Reassacts `request_template_id` and `response_template_id` to `projects/48196429354/locations/global/floorSetting`.

3. **Content Authorization Policy (`booking-ma-authz-policy`):**
   * Command: `gcloud beta network-security authz-policies import booking-ma-authz-policy --location=us-central1`
   * `policyProfile`: `CONTENT_AUTHZ`
   * Target: `projects/agent-security-patterns/locations/us-central1/agentGateways/booking-agent-gateway`
   * Custom Provider: `booking-ma-authz-ext`

---

### 4. Required Service Agent IAM Bindings

Granted callout and consumer roles to GCP service agents:

```bash
# 1. AI Platform Reasoning Engine Service Agent
gcloud projects add-iam-policy-binding agent-security-patterns \
  --member=serviceAccount:service-48196429354@gcp-sa-aiplatform-re.iam.gserviceaccount.com \
  --role=roles/modelarmor.calloutUser

gcloud projects add-iam-policy-binding agent-security-patterns \
  --member=serviceAccount:service-48196429354@gcp-sa-aiplatform-re.iam.gserviceaccount.com \
  --role=roles/modelarmor.user

# 2. Service Extensions Service Agent
gcloud projects add-iam-policy-binding agent-security-patterns \
  --member=serviceAccount:service-48196429354@gcp-sa-dep.iam.gserviceaccount.com \
  --role=roles/modelarmor.calloutUser

gcloud projects add-iam-policy-binding agent-security-patterns \
  --member=serviceAccount:service-48196429354@gcp-sa-dep.iam.gserviceaccount.com \
  --role=roles/modelarmor.user

gcloud projects add-iam-policy-binding agent-security-patterns \
  --member=serviceAccount:service-48196429354@gcp-sa-dep.iam.gserviceaccount.com \
  --role=roles/serviceusage.serviceUsageConsumer
```

---

### 5. Agent Engine Deployment Updates

Updated both deployment scripts (`orchestrator/deploy_agent_engine.py` and `bookings/deploy_agent_engine.py`) to pass `agent_gateway_config`:

```python
client_to_agent_gateway_id = os.environ.get("CLIENT_TO_AGENT_GATEWAY_ID", "booking-agent-gateway")
client_to_agent_gateway = (
    f"projects/{project_id}/locations/us-central1/agentGateways/{client_to_agent_gateway_id}"
)

agent_gateway_config = {
    "client_to_agent_config": {"agent_gateway": client_to_agent_gateway},
}

config = {
    "display_name": DISPLAY_NAME,
    "description": DESCRIPTION,
    "requirements": REQUIREMENTS,
    "extra_packages": EXTRA_PACKAGES,
    "env_vars": environment_variables,
    "agent_gateway_config": agent_gateway_config,
    "identity_type": types.IdentityType.AGENT_IDENTITY,
    "staging_bucket": staging_bucket,
    "max_instances": 3,
}
```

Both agents were deployed successfully to Vertex AI Agent Engine:
* **Orchestrator Agent:** `projects/48196429354/locations/us-central1/reasoningEngines/1818476233864773632`
* **Bookings Agent:** `projects/48196429354/locations/us-central1/reasoningEngines/697851783812218880`

---

### 6. Frontend Client Refactoring (`fast-api-fe/services/agent_client.py`)

Refactored `query_agent()` to use `vertexai.Client` and **`engine.stream_query()`** (`reasoningEngines.streamQuery`):

```python
import vertexai
from vertexai import agent_engines

_VERTEX_CLIENT = None

def get_vertex_client():
    global _VERTEX_CLIENT
    if _VERTEX_CLIENT is None:
        _VERTEX_CLIENT = vertexai.Client(project=PROJECT_ID, location=LOCATION)
    return _VERTEX_CLIENT

async def query_agent(...):
    client = get_vertex_client()
    engine = client.agent_engines.get(name=ENGINE_ID)

    # Invoke stream_query (triggers reasoningEngines.streamQuery Model Armor ADK interception)
    response_stream = engine.stream_query(
        message=user_message,
        user_id=user_id,
        session_id=session_id,
        run_config=run_config,
    )
    ...
```

---

## Important Technical Quirks & Constraints

1. **Model Armor Location:** Model Armor `floorSetting` resources **MUST** be located in `global` (`projects/${PROJECT_ID}/locations/global/floorSetting`). Regional locations (like `us-central1`) trigger admission control errors (`location "us-central1" is not allowed (must be one of map[global:true])`).
2. **ADK Method Requirement:** For ADK agents on Agent Runtime, Model Armor Client-to-Agent ingress inspection **only intercepts `reasoningEngines.streamQuery`**. Non-streaming `query()` calls bypass Model Armor.
3. **mTLS / ECP Proxy Override:** On local development environments with client certificates / ECP HTTP proxy enabled, set the following environment variables before executing `gcloud model-armor` commands:
   ```bash
   export CLOUDSDK_API_ENDPOINT_OVERRIDES_MODELARMOR="https://modelarmor.googleapis.com/"
   export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false
   export CLOUDSDK_CONTEXT_AWARE_USE_ECP_HTTP_PROXY=false
   ```

---

## Operational Commands Quick Reference

```bash
# Provision Model Armor Guardrails
./ingress/setup-scripts/setup-model-armor.sh

# Provision Unified Agent Gateway & Content Authz Policy
./ingress/setup-scripts/setup-agent-gateway.sh

# Redeploy Orchestrator Agent with Gateway Binding
source ./config.sh && uv run python orchestrator/deploy_agent_engine.py

# Redeploy Bookings Agent with Gateway Binding
source ./config.sh && uv run python bookings/deploy_agent_engine.py

# Audit Model Armor Security Callouts
gcloud logging read 'resource.type="audited_resource" AND resource.labels.service="modelarmor.googleapis.com"' --limit=10
```
