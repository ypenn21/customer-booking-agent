# Accessing HTTP Headers in Agent Engine

## Key Finding

**Agent Engine does not forward HTTP headers into the agent context.** The `X-Goog-Authenticated-User-Email` (set by Cloud IAP) or any other incoming request header is not accessible inside your ADK tools or callbacks when the agent is deployed on Vertex AI Agent Engine (`AdkApp`).

## Recommended Pattern: Pass email as `user_id`

Whoever calls Agent Engine (e.g. a Cloud Run frontend) should extract the header and pass it as `user_id` at session creation time:

```python
# In your calling layer (Cloud Run, API gateway, etc.)
user_email = request.headers.get("X-Goog-Authenticated-User-Email", "anonymous")

remote_session = await remote_app.async_create_session(user_id=user_email)
async for event in remote_app.async_stream_query(
    message=request_body,
    user_id=user_email,
    session_id=remote_session["id"]
):
    ...
```

Then inside agent tools, read it from the invocation context:

```python
from google.adk.tools import ToolContext

def my_tool(query: str, tool_context: ToolContext) -> dict:
    user_id = tool_context._invocation_context.user_id  # the email passed above
    ...
```

## Alternative: Inject into session state

Pass the email as initial session state instead of (or in addition to) `user_id`:

```python
remote_session = await remote_app.async_create_session(
    user_id=user_email,
    session_state={"user:authenticated_email": user_email}
)
```

Read in tools via:

```python
email = tool_context.state.get("user:authenticated_email")
```

## What Does NOT Work in Agent Engine

- `invocation_context.http_request` — only available when using `adk api_server` (local FastAPI)
- `before_agent_callback` reading raw HTTP headers — same limitation
- Cloud IAP headers are stripped/not forwarded to the Agent Engine SDK call
