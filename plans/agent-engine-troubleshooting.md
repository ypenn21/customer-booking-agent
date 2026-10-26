# Agent Engine Troubleshooting — Complete Summary

A consolidated record of every issue encountered, root-caused, and fixed while deploying the customers and bookings agents on Vertex AI Agent Engine (Reasoning Engine).

---

## 1. Regional Deployment Failure (500 INTERNAL / DEADLINE_EXCEEDED)

### Symptom
`google.genai.errors.ServerError: 500 INTERNAL` when running either `deploy_agent_engine.py`.

### Root Cause
Backend Spanner deadlock in the `us-central1` Reasoning Engine control plane:
```
generic::DEADLINE_EXCEEDED: Delayed lock acquisition 57.4867 secs on tablet z3436_613180425
```

### Fix
Migrated all deployments to `us-east1`. Updated `config.sh`:
```bash
export LOCATION="us-east1"
```
Deleted orphaned `us-central1` instances to prevent billing leakage.

---

## 2. Module Shadowing (`ModuleNotFoundError: No module named 'bookings.app'`)

### Symptom
Deployment script failed with `ModuleNotFoundError: No module named 'bookings.app'`.

### Root Cause
`bookings/__init__.py` exported `from .agent import app`. Because a variable named `app` now existed in the `bookings` namespace, Python resolved `bookings.app` to that variable instead of the `app.py` file.

### Fix
- Emptied `bookings/__init__.py` and `customers/__init__.py`.
- Changed `sys.path.append(...)` to `sys.path.insert(0, ...)` in deploy scripts so the local project root takes priority.

---

## 3. Event Loop Error (`RuntimeError: Task got Future attached to a different loop` or `RuntimeError: Event loop is closed`)

### Symptom
1. `RuntimeError: Task got Future attached to a different loop`
2. `RuntimeError: Event loop is closed` (occurs on subsequent requests)

### Root Cause — Threading and Caching Mismatch
ADK's `Runner` spawns a new OS thread and a new `asyncio` event loop for every incoming request. However, the `Gemini.api_client` is a `@cached_property` on the `Gemini` model instance, which is typically a singleton.

**The Race Condition:**
The initial fix (popping `api_client` from `model.__dict__`) was not thread-safe. During concurrent requests:
1. Request A pops the client and starts creating a new one bound to Loop A.
2. Request B pops the client and starts creating a new one bound to Loop B.
3. If Request B stores its client in the shared `model.__dict__` while Request A is still running, Request A might inadvertently pick up Request B's client (bound to Loop B) for its next LLM call.
4. If Request B finishes and Loop B is closed, Request A hits `RuntimeError: Event loop is closed`.
### The Definitive Fix — Loop-Based Isolation with Data Descriptors
Instead of `contextvars` (which can be unreliable if threads are reused across different event loops), we patch `Gemini.api_client` to be a **Data Descriptor** (a property with a dummy setter). This ensures that Python's attribute lookup always calls our property, even if ADK's `@cached_property` has already stored a value in the instance's `__dict__`.

We store the `google.genai.Client` in a cache on the `Gemini` instance, keyed by `id(asyncio.get_running_loop())`. This guarantees that each request's loop gets its own private, isolated client that is never reused across different loops.

**Note:** This pattern aligns with the official ADK fix for similar resource leaks in session management (see [google/adk-python@7937e9e](https://github.com/google/adk-python/commit/7937e9ed4016d746a8bb0605c215f7fb44653634)), which enforces short-lived clients and explicit cleanup.

```python
# bookings/app.py (identical pattern in customers/app.py)
...
import asyncio
from google.genai import Client, types
from google.adk.models import Gemini
from vertexai.agent_engines import AdkApp

def _create_client(model: Gemini, is_live: bool = False) -> Client:
    if is_live:
        return Client(http_options=types.HttpOptions(
            headers=model._tracking_headers(), api_version=model._live_api_version))
    return Client(http_options=types.HttpOptions(
        headers=model._tracking_headers(),
        retry_options=model.retry_options,
        base_url=model.base_url))

def _get_loop_safe_client(model: Gemini, is_live: bool = False) -> Client:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return _create_client(model, is_live)
    
    # Store cache on the model instance, keyed by loop ID.
    if not hasattr(model, "_loop_client_cache"):
        model._loop_client_cache = {}
    
    key = (id(loop), is_live)
    client = model._loop_client_cache.get(key)
    if client is None:
        client = _create_client(model, is_live)
        model._loop_client_cache[key] = client
    return client

# Patch Gemini using a Data Descriptor (fget + fset).
# The fset (setter) ensures this property overrides model.__dict__.
Gemini.api_client = property(
    fget=lambda self: _get_loop_safe_client(self, is_live=False),
    fset=lambda self, val: None
)
Gemini._live_api_client = property(
    fget=lambda self: _get_loop_safe_client(self, is_live=True),
    fset=lambda self, val: None
)

class FreshClientAdkApp(AdkApp):
    async def _aclose_current_loop_clients(self) -> None:
        """Closes all clients bound to the current loop."""
        try:
            loop = asyncio.get_running_loop()
            # Navigate to the model instance from the runner
            model = self._tmpl_attrs["runner"].agent.canonical_model
            cache = getattr(model, "_loop_client_cache", {})
            for key in list(cache.keys()):
                if key[0] == id(loop):
                    client = cache.pop(key)
                    try: await client.aio.aclose()
                    except: pass
        except: pass

    async def async_stream_query(self, **kwargs):
        try:
            async for event in super().async_stream_query(**kwargs): yield event
        finally: await self._aclose_current_loop_clients()

    async def streaming_agent_run_with_events(self, request_json: str):
        try:
            async for event in super().streaming_agent_run_with_events(request_json): yield event
        finally: await self._aclose_current_loop_clients()

app = FreshClientAdkApp(agent=root_agent)
```

**Why this works:**
1. **Bypassing Cache:** The Data Descriptor property (with setter) always wins against `model.__dict__`.
2. **True Isolation:** Every request loop is a different object with a different `id()`, so it's guaranteed to get a fresh client.
3. **Safe Reuse:** Multiple LLM calls within the *same* request reuse the same client via the cache keyed by the same loop ID.
4. **Reliable Cleanup:** `aclose()` is called in the `finally` block, and the client is removed from the cache.

---

## 4. `config.sh` Stray Line / Leading Slash on Engine IDs

### Symptom
`source config.sh` would attempt to execute a bare resource path as a shell command and fail. Engine IDs caused 404s when used as resource names.

### Root Cause
Two bugs in `config.sh`:
1. An unassigned resource path on its own line was executed as a shell command on `source`.
2. Engine ID values had a leading `/`, e.g. `/projects/48196429354/...` instead of `projects/48196429354/...`.

### Fix
Removed the stray line and the leading slashes. Correct format:
```bash
export CUSTOMERS_ENGINE_ID="projects/48196429354/locations/us-east1/reasoningEngines/4902238563136962560"
export BOOKINGS_ENGINE_ID="projects/48196429354/locations/us-east1/reasoningEngines/1246441565618962432"
CUSTOMERS_PRINCIPAL="principal://agents.global.org-419713829424.system.id.goog/resources/aiplatform/projects/48196429354/locations/us-east1/reasoningEngines/4902238563136962560"
BOOKINGS_PRINCIPAL="principal://agents.global.org-419713829424.system.id.goog/resources/aiplatform/projects/48196429354/locations/us-east1/reasoningEngines/1246441565618962432"
```

---

## 5. 404 on `create_session` from Customers Agent

### Symptom
```
404: projects/48196429354/locations/us-east1/reasoningEngines/1246441565618962432
```
Returned by `remote_app.create_session()` inside the customers agent running in Agent Engine. Direct `create_session` from local environment succeeds on the same engine ID.

### Root Cause
`customers/deploy_agent_engine.py` was missing `"LOCATION": location` from its `environment_variables` dict. The bookings deploy had it; the customers deploy did not.

At runtime inside Agent Engine:
```python
vertexai.init(
    project=project_id,
    location=os.environ.get("LOCATION")  # None — env var not set!
)
```
`location=None` causes the Vertex AI SDK to default to `us-central1`, while the agents are deployed in `us-east1`. This location mismatch causes the API client to route requests incorrectly, returning 404.

### Fix
Added `"LOCATION": location` to `customers/deploy_agent_engine.py`:
```python
environment_variables = {
    "GOOGLE_GENAI_USE_VERTEXAI": "TRUE",
    "GOOGLE_CLOUD_LOCATION": "global",
    "LOCATION": location,               # ← added
    "BOOKINGS_ENGINE_ID": os.environ.get("BOOKINGS_ENGINE_ID"),
    ...
}
```
Redeploy the customers agent after this change.

---

## 6. 403 on Secret Manager (`secretmanager.versions.access` denied)

### Symptom
```
ERROR:bookings.agent: Error retrieving access token:
403 Permission 'secretmanager.versions.access' denied on resource
[reason: "IAM_PERMISSION_DENIED"]
```

### Root Cause
The bookings agent reads per-user OAuth tokens from Secret Manager (`ms-tokens-{user_id}`). The IAM grant `roles/secretmanager.secretAccessor` was bound to the **old** bookings engine principal. After the bookings engine was redeployed with a new resource ID (`1246441565618962432`), the new principal had no Secret Manager access.

### Fix
Re-run `setup-scripts/after-agents-deployment-grant.sh` with the updated `BOOKINGS_PRINCIPAL` from `config.sh`:
```bash
cd setup-scripts
source ../config.sh
./after-agents-deployment-grant.sh
```

This re-applies all IAM bindings for both agents against the current principals:
- `BOOKINGS_PRINCIPAL` → `roles/secretmanager.secretAccessor`, logging, tracing, monitoring
- `CUSTOMERS_PRINCIPAL` → `roles/aiplatform.user`, logging, tracing, monitoring

> **Rule of thumb:** Any time either agent engine is redeployed with a new resource ID, re-run `after-agents-deployment-grant.sh`. The agent identity principal is tied to the engine resource ID — a new ID = a new principal = existing IAM grants no longer apply.

---

## Post-Deployment Checklist

After deploying or redeploying either agent:

- [ ] `source config.sh` — verify `BOOKINGS_ENGINE_ID` and `CUSTOMERS_ENGINE_ID` are correct (no leading slash, no stray lines)
- [ ] Run `python -m bookings.deploy_agent_engine` and/or `python -m customers.deploy_agent_engine`
- [ ] Re-run `setup-scripts/after-agents-deployment-grant.sh` if the bookings engine ID changed
- [ ] Re-run `setup-scripts/after-customers-agent-deployment-grant.sh` if the customers engine ID changed
- [ ] Verify the new engine is in ACTIVE state before testing (can take a few minutes after deploy completes)
- [ ] Test end-to-end: customers agent → `bookings()` tool → bookings agent → Secret Manager access

---

## Current Deployed State

| Agent | Region | Resource ID |
|-------|--------|-------------|
| Customer Assistant | `us-east1` | `projects/48196429354/locations/us-east1/reasoningEngines/4902238563136962560` |
| Booking Assistant | `us-east1` | `projects/48196429354/locations/us-east1/reasoningEngines/1246441565618962432` |
