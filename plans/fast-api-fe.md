# FastAPI Chatbot UI Frontend (`fast-api-fe`)

## Overview

Build a self-contained `fast-api-fe/` directory that runs a single FastAPI server serving:
1. **Chat UI** — a browser-based chatbot UI rendered via Jinja2 HTML templates (mirroring the Django `adk_bug_ticket_agent` app structure).
2. **OpenAI-compatible REST API** — `POST /v1/chat/completions` that proxies messages to the deployed `customers` ADK agent on GCP Vertex AI Agent Engine and returns responses in the OpenAI `ChatCompletion` schema.

The reference architecture for MVC/template patterns is taken from the [`adk_bug_ticket_agent`](https://github.com/ypenn21/adk-agents/tree/main/adk_bug_ticket_agent) Django app (views.py, urls.py, templates/).

---

## Documentation References

### Google Developer Knowledge
> **Ref-1:** OpenAPI Proxy Tutorial (Apigee) — Confirms OpenAPI spec as the standard for proxying API requests; reinforces use of standard HTTP conventions.

### Context7 Library Docs
> **Lib-1:** `/websites/fastapi_tiangolo` — FastAPI Jinja2 templates via `Jinja2Templates`, static file serving via `StaticFiles`, async route handlers, `StreamingResponse` for SSE, `HTMLResponse`.

---

## Current State

- `customers/agent.py` defines `root_agent` (ADK Agent) and an `app` (ADK App). The `bookings()` async tool calls GCP Agent Engine (`projects/genai-apps-25/.../reasoningEngines/9162713079862001664`) via `vertexai.agent_engines`.
- `customers/deploy_agent_engine.py` deploys the `customers` app to Agent Engine.
- No web frontend exists yet; the project is tested via ADK playground or direct API calls.

---

## 📋 Checklist

- [ ] Create folder structure `fast-api-fe/`
- [ ] Create `fast-api-fe/main.py` — FastAPI app entry point (mounts static, registers routers)
- [ ] Create `fast-api-fe/routers/chat.py` — OpenAI-compatible API (`POST /v1/chat/completions`)
- [ ] Create `fast-api-fe/routers/ui.py` — UI routes (`GET /` → render chat template)
- [ ] Create `fast-api-fe/services/agent_client.py` — GCP Agent Engine proxy service
- [ ] Create `fast-api-fe/models/openai_schema.py` — Pydantic models for OpenAI request/response schemas
- [ ] Create `fast-api-fe/templates/chat.html` — Chat UI (HTML/JS, inspired by Django reference template)
- [ ] Create `fast-api-fe/static/` — CSS/JS assets for the UI
- [ ] Create `fast-api-fe/requirements.txt`
- [ ] Create `fast-api-fe/Dockerfile` — Multi-stage, Cloud Run-optimized
- [ ] Create `fast-api-fe/.dockerignore`
- [ ] Create `fast-api-fe/README.md` with run instructions

---

## Proposed Changes

### Folder Structure

```
fast-api-fe/
├── main.py                      # FastAPI app, mount static, include routers
├── routers/
│   ├── __init__.py
│   ├── chat.py                  # POST /v1/chat/completions (OpenAI-compatible)
│   └── ui.py                    # GET /  (renders chat.html)
├── services/
│   ├── __init__.py
│   └── agent_client.py          # Proxy to GCP Agent Engine
├── models/
│   ├── __init__.py
│   └── openai_schema.py         # Pydantic: ChatCompletionRequest, ChatCompletionResponse
├── templates/
│   └── chat.html                # Jinja2 chat UI (mirrors adk_bug_ticket_agent/templates/)
├── static/
│   ├── style.css
│   └── chat.js
├── requirements.txt
├── Dockerfile                   # Multi-stage, Cloud Run-optimized
├── .dockerignore
└── README.md
```

---

### `fast-api-fe/models/openai_schema.py`

OpenAI chat completions request/response Pydantic models:

```python
from pydantic import BaseModel
from typing import Literal, Optional
import time, uuid

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "customers-agent"
    messages: list[ChatMessage]
    stream: bool = False

class ChatChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"

class ChatCompletionResponse(BaseModel):
    id: str = ""
    object: str = "chat.completion"
    created: int = 0
    model: str = "customers-agent"
    choices: list[ChatChoice]

    def __init__(self, **data):
        if not data.get("id"):
            data["id"] = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        if not data.get("created"):
            data["created"] = int(time.time())
        super().__init__(**data)
```

---

### `fast-api-fe/services/agent_client.py`

Proxies to the deployed customers agent on GCP Agent Engine:

```python
import os
import vertexai
from vertexai import agent_engines

PROJECT_ID  = os.environ.get("PROJECT_ID", "genai-apps-25")
LOCATION    = os.environ.get("LOCATION", "us-central1")
ENGINE_ID   = os.environ.get(
    "CUSTOMERS_ENGINE_ID",
    "projects/genai-apps-25/locations/us-central1/reasoningEngines/<RESOURCE_ID>"
)

vertexai.init(project=PROJECT_ID, location=LOCATION)

async def query_agent(user_message: str, user_id: str = "web_user") -> str:
    remote_app = agent_engines.get(ENGINE_ID)
    session    = await remote_app.async_create_session(user_id=user_id)
    final_text = []
    async for event in remote_app.async_stream_query(
        message=user_message,
        user_id=user_id,
        session_id=session["id"]
    ):
        role = event.get("role") or event.get("content", {}).get("role")
        if role == "model":
            for part in event.get("content", {}).get("parts", []):
                if "text" in part:
                    final_text.append(part["text"])
    return "\n".join(final_text) if final_text else "Agent provided no response."
```

> **Note:** `CUSTOMERS_ENGINE_ID` must be set via env var or `.env` file with the actual resource name printed after running `customers/deploy_agent_engine.py`.

---

### `fast-api-fe/routers/chat.py`

OpenAI-compatible `/v1/chat/completions` endpoint:

```python
from fastapi import APIRouter, HTTPException
from ..models.openai_schema import (
    ChatCompletionRequest, ChatCompletionResponse, ChatMessage, ChatChoice
)
from ..services.agent_client import query_agent

router = APIRouter(prefix="/v1", tags=["chat"])

@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(req: ChatCompletionRequest):
    # Extract last user message (standard OpenAI pattern)
    user_msgs = [m for m in req.messages if m.role == "user"]
    if not user_msgs:
        raise HTTPException(status_code=400, detail="No user message provided")
    
    user_input = user_msgs[-1].content
    agent_reply = await query_agent(user_input)
    
    return ChatCompletionResponse(
        model=req.model,
        choices=[
            ChatChoice(
                message=ChatMessage(role="assistant", content=agent_reply)
            )
        ]
    )
```

---

### `fast-api-fe/routers/ui.py`

Renders the chat HTML template (mirrors Django `views.py` GET branch):

```python
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router    = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory="fast-api-fe/templates")

@router.get("/", response_class=HTMLResponse)
async def chat_ui(request: Request):
    return templates.TemplateResponse(
        request=request, name="chat.html", context={"title": "Customer Booking Chat"}
    )
```

---

### `fast-api-fe/main.py`

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .routers import chat, ui

app = FastAPI(title="Customer Booking Chatbot")
app.mount("/static", StaticFiles(directory="fast-api-fe/static"), name="static")
app.include_router(ui.router)
app.include_router(chat.router)
```

---

### `fast-api-fe/templates/chat.html`

A single-page chat UI that:
- Uses `fetch()` to `POST /v1/chat/completions` (OpenAI format)
- Maintains a local `messages[]` array and renders the conversation
- Styled as a modern chat bubble UI

Key JS flow (mirrors Django template AJAX pattern from `adk_bug_ticket_agent`):

```javascript
async function sendMessage() {
    const userText = input.value.trim();
    messages.push({ role: "user", content: userText });
    renderMessages();

    const res = await fetch("/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: "customers-agent", messages })
    });
    const data = await res.json();
    const reply = data.choices[0].message.content;
    messages.push({ role: "assistant", content: reply });
    renderMessages();
}
```

---

### `fast-api-fe/requirements.txt`

```
fastapi>=0.115.0
uvicorn[standard]>=0.29.0
jinja2>=3.1.0
python-multipart>=0.0.9
vertexai>=1.130.0
google-adk>=1.16.0,<2.0.0
```

---

### `fast-api-fe/Dockerfile`

Multi-stage build optimized for Cloud Run:
- **Stage 1 (`builder`)**: Installs Python deps into a virtual env using a full image
- **Stage 2 (`runtime`)**: Copies only the venv + app code into a slim image — minimizes image size
- Runs as **non-root** user (`appuser`) — Cloud Run security best practice
- Binds to `0.0.0.0:8080` — Cloud Run's required port
- Sets `PYTHONUNBUFFERED=1` for real-time Cloud Run logging

```dockerfile
# ── Stage 1: Build dependencies ────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools (needed for some native wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment and install deps
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy virtual env from builder (no pip needed in runtime)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source
COPY . /app/fast-api-fe

# Create non-root user (Cloud Run security best practice)
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

# Cloud Run injects PORT env var; default to 8080
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Expose port for documentation — Cloud Run uses $PORT at runtime
EXPOSE 8080

# Start uvicorn; use $PORT for Cloud Run compatibility
CMD ["sh", "-c", "uvicorn fast-api-fe.main:app --host 0.0.0.0 --port $PORT --workers 1"]
```

> **Why `--workers 1`?** Cloud Run scales horizontally by spinning up more container instances. Multiple workers inside a single container waste resources and complicate memory management. Keep 1 uvicorn worker per container.

---

### `fast-api-fe/.dockerignore`

Keeps image lean by excluding dev artifacts:

```
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
.env
*.env
.venv/
venv/
.git/
.gitignore
*.md
!README.md
tests/
*.egg-info/
dist/
build/
.pytest_cache/
.ruff_cache/
```

---

### Cloud Run Deployment

**Prerequisites:**
- Service account (or Cloud Run's default SA) needs these IAM roles:
  - `roles/aiplatform.user` — to call Vertex AI Agent Engine
  - `roles/logging.logWriter` — for Cloud Run logs

**Build & deploy commands:**

```bash
# 1. Build and push image to Artifact Registry
PROJECT_ID=genai-apps-25
REGION=us-central1
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/fast-api-fe/chatbot:latest"

docker build -t $IMAGE ./fast-api-fe
docker push $IMAGE

# 2. Deploy to Cloud Run (IAP-protected, no public access)
gcloud run deploy customer-chatbot \
  --image=$IMAGE \
  --region=$REGION \
  --platform=managed \
  --no-allow-unauthenticated \
  --port=8080 \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},LOCATION=${REGION},CUSTOMERS_ENGINE_ID=projects/${PROJECT_ID}/locations/${REGION}/reasoningEngines/<RESOURCE_ID>" \
  --service-account=<SA_EMAIL> \
  --min-instances=0 \
  --max-instances=10 \
  --memory=512Mi \
  --cpu=1

# 3. Enable IAP on the Cloud Run backend service
#    (requires a Load Balancer + Serverless NEG in front of Cloud Run)
gcloud compute backend-services update customer-chatbot-backend \
  --global \
  --iap=enabled,oauth2-client-id=<OAUTH_CLIENT_ID>,oauth2-client-secret=<OAUTH_CLIENT_SECRET>
```

**IAP setup prerequisites:**
1. Create an **OAuth 2.0 Client ID** in GCP Console → APIs & Services → Credentials (type: Web application)
2. Set the authorized redirect URI to `https://iap.googleapis.com/v1/oauth/clientIds/<CLIENT_ID>:handleRedirect`
3. Front Cloud Run with a **Global HTTPS Load Balancer** + **Serverless NEG** pointing to the Cloud Run service
4. Grant users `roles/iap.httpsResourceAccessor` on the backend service

> **IAP + Cloud Run**: Cloud Run does not support IAP natively on the Run service URL. IAP must be applied via a **Global Load Balancer** → **Serverless NEG** → **Cloud Run** topology. Direct `*.run.app` URLs bypass IAP.

> **ADC in Cloud Run**: No credentials file needed — Cloud Run attaches the service account automatically. `vertexai.init()` picks it up via Application Default Credentials.

---

## Trade-offs & Considerations

| Approach | Pros | Cons |
|---|---|---|
| **Proxy to Agent Engine** (chosen) | No local ADK runner needed; uses the deployed instance same as prod | Requires `CUSTOMERS_ENGINE_ID` env var; latency per call includes session creation |
| Run ADK locally | Faster for dev | Requires full env setup, not reflective of prod |
| Streaming SSE | Better UX for long responses | Adds complexity; Agent Engine streaming with `async_stream_query` still needed |

> **Streaming**: The plan starts with non-streaming (full response). Streaming via `Server-Sent Events` and `StreamingResponse` can be added as a follow-up.

---

## Next Steps

1. Create `fast-api-fe/` folder structure and all files listed above
2. Set `CUSTOMERS_ENGINE_ID` env var (get resource name from `customers/deploy_agent_engine.py` output)
3. Run locally: `uvicorn fast-api-fe.main:app --reload --port 8080` (from project root)
4. Test API: `curl -X POST http://localhost:8080/v1/chat/completions -H "Content-Type: application/json" -d '{"messages":[{"role":"user","content":"Show me all customers"}]}'`
5. Test UI: open `http://localhost:8080` in browser
6. Verify responses match OpenAI schema format
7. Build Docker image: `docker build -t chatbot:local ./fast-api-fe`
8. Test container locally: `docker run -p 8080:8080 -e CUSTOMERS_ENGINE_ID=... -e GOOGLE_CLOUD_PROJECT=genai-apps-25 chatbot:local`
9. Push to Artifact Registry and deploy to Cloud Run (see Cloud Run Deployment section above)
