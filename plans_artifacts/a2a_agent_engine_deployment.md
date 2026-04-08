# Deploy Bookings Agent to Agent Engine with A2A Support

## Overview

**The problem:** [deploy_agent_engine.py](file:///Users/yannipeng/git-projects/customer-booking-agent/bookings/deploy_agent_engine.py) deploys `app` (an `AdkApp` wrapper). `AdkApp` only exposes ADK-specific streaming query methods — it does not expose A2A protocol endpoints (`on_message_send`, `on_get_task`, `handle_authenticated_agent_card`). The `a2a_app` (a raw `FastAPI` app) is not picklable and cannot be passed to `agent_engines.create()`.

**The solution:** Vertex AI provides a dedicated **`A2aAgent`** template class (`vertexai.preview.reasoning_engines.A2aAgent`) that wraps any `AgentExecutor`+`AgentCard` and exposes the correct A2A operations on Agent Engine. We deploy *this* instead of `AdkApp` or `FastAPI`.

> **Ref-1:** [Develop A2A on Agent Engine](https://docs.cloud.google.com/agent-builder/agent-engine/develop/a2a) — Defines the `A2aAgent` class, `agent_executor_builder` lambda pattern, and the three exposed operations.  
> **Ref-2:** [Deploy to Agent Engine](https://docs.cloud.google.com/agent-builder/agent-engine/deploy) — Shows A2A requirements (`google-cloud-aiplatform[agent_engines]` + `a2a-sdk>=0.3.4`).

---

## 📋 Checklist

- [ ] **bookings/deploy_agent_engine.py** — Replace `AdkApp` with `A2aAgent` built from `agent_card` + `agent_executor_builder` lambda. Update requirements.
- [ ] Verify locally using `A2aAgent.set_up()` + `handle_authenticated_agent_card()`.
- [ ] Deploy and update `BOOKINGS_AGENT_CARD_URL` in customers deploy script.

---

## Current State

```
bookings/agent.py
  root_agent  →  Agent(name="bookings", ...)
  app         →  AdkApp(agent=root_agent)          ← what deploy currently uses
  agent_card  →  AgentCard(...)                    ← already defined ✅
  a2a_app     →  FastAPI wrapping A2AStarletteApplication  ← not deployable

bookings/agent_executor.py
  AdkAgentToA2AExecutor  ← wraps A2aAgentExecutor from google.adk.a2a ✅

bookings/deploy_agent_engine.py
  agent_engines.create(app, ...)   ← deploys AdkApp, no A2A ❌
```

---

## Proposed Changes

### [MODIFY] [deploy_agent_engine.py](file:///Users/yannipeng/git-projects/customer-booking-agent/bookings/deploy_agent_engine.py)

Replace the `AdkApp`-based deploy with an `A2aAgent`-based deploy:

```python
import os
import sys
import vertexai

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vertexai.preview.reasoning_engines import A2aAgent
from bookings.agent import agent_card, root_agent
from bookings.agent_executor import AdkAgentToA2AExecutor

def main():
    project_id = os.environ.get("PROJECT_ID", "genai-apps-25")
    location = "us-central1"
    staging_bucket = os.environ.get("STAGING_BUCKET", f"gs://{project_id}-adk-staging")

    if not project_id:
        print("Error: PROJECT_ID environment variable not set.")
        sys.exit(1)

    vertexai.init(project=project_id, location=location, staging_bucket=staging_bucket)

    # A2aAgent wraps agent_card + executor and exposes proper A2A endpoints
    # agent_executor_builder MUST be a lambda — never a constructed instance —
    # so the executor is built inside the remote container, not pickled locally.
    a2a_agent = A2aAgent(
        agent_card=agent_card,
        agent_executor_builder=lambda: AdkAgentToA2AExecutor(root_agent),
    )

    print("Deploying A2A-enabled bookings agent to Agent Engine...")

    remote_app = vertexai.agent_engines.create(
        a2a_agent,
        requirements=[
            "google-cloud-aiplatform[agent_engines]>=1.130.0",
            "google-adk>=1.16.0,<2.0.0",
            "a2a-sdk~=0.3.22",
            "nest-asyncio>=1.6.0,<2.0.0",
            "opentelemetry-instrumentation-google-genai>=0.1.0,<1.0.0",
            "gcsfs>=2024.11.0",
            "google-cloud-logging>=3.12.0,<4.0.0",
            "protobuf>=6.31.1,<7.0.0",
        ],
        extra_packages=["bookings"],
        display_name="Booking Assistant",
        description="Assists in making custom bookings and reservations.",
        env_vars={"GOOGLE_GENAI_USE_VERTEXAI": "TRUE"},
    )
    print(f"Agent Engine Remote App created: {remote_app.resource_name}")

if __name__ == "__main__":
    main()
```

**Key changes:**
- Import `A2aAgent` from `vertexai.preview.reasoning_engines`
- Import `agent_card` and `root_agent` from `bookings.agent` (both already exported)
- `agent_executor_builder=lambda: AdkAgentToA2AExecutor(root_agent)` — the lambda defers construction so the executor is **never pickled** during deployment, only instantiated in the remote environment
- Requirements: switch `google-cloud-aiplatform[evaluation,agent-engines]` → `google-cloud-aiplatform[agent_engines]` (A2A template requirement per docs)

### bookings/agent.py — No changes required ✅

`agent_card`, `root_agent`, and [AdkAgentToA2AExecutor](file:///Users/yannipeng/git-projects/customer-booking-agent/bookings/agent_executor.py#9-22) are already defined and importable. The `a2a_app` FastAPI app can stay for local `adk web` serving.

> [!IMPORTANT]
> `agent_executor_builder` **must be a lambda/callable** (not a constructed instance). `A2aAgent` calls it inside the remote container, bypassing pickle entirely. Do NOT pass [AdkAgentToA2AExecutor(root_agent)](file:///Users/yannipeng/git-projects/customer-booking-agent/bookings/agent_executor.py#9-22) directly.

---

## Trade-offs & Considerations

| | `AdkApp` | `FastAPI(a2a_app)` | **`A2aAgent` (proposed)** |
|---|---|---|---|
| Deployable to Agent Engine | ✅ | ❌ (not picklable) | ✅ |
| Exposes A2A endpoints | ❌ | ✅ | ✅ |
| `customers` agent can call via `RemoteA2aAgent` | ❌ | N/A (local only) | ✅ |

---

## Verification Plan

### 1. Local smoke test (run before deploying)

```bash
cd /Users/yannipeng/git-projects/customer-booking-agent
uv run python - <<'EOF'
import asyncio, os
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

from bookings.agent import agent_card, root_agent
from bookings.agent_executor import AdkAgentToA2AExecutor
from vertexai.preview.reasoning_engines import A2aAgent

a2a_agent = A2aAgent(
    agent_card=agent_card,
    agent_executor_builder=lambda: AdkAgentToA2AExecutor(root_agent),
)
a2a_agent.set_up()

resp = asyncio.run(a2a_agent.handle_authenticated_agent_card(request=None, context=None))
print("Agent card:", resp)
EOF
```

Expected: prints the agent card JSON with `name="bookings"` and the defined skills.

### 2. Deploy

```bash
uv run python bookings/deploy_agent_engine.py
```

Note the `resource_name` in the output.

### 3. Update customers

Update `BOOKINGS_AGENT_CARD_URL` in [customers/deploy_agent_engine.py](file:///Users/yannipeng/git-projects/customer-booking-agent/customers/deploy_agent_engine.py) to point to the new bookings resource, then redeploy customers.
