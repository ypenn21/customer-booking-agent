# Session Management Refactor - Frontend Storage & Session Listing

## Overview
This plan outlines the changes required to move session management from the server-side memory store to the client-side (frontend). This allows for better scalability and lets users manage their own sessions (e.g., resuming old conversations). We will also implement a way to list all sessions started by a user.

## Documentation References

### Google Developer Knowledge
> **Ref-1:** [Vertex AI Agent Engine Sessions Overview](https://cloud.google.com/agent-builder/docs/agent-engine/sessions/overview) — Sessions provide long-term memory and context, and can be managed via API.
> **Ref-2:** [Manage sessions using API calls](https://cloud.google.com/agent-builder/docs/agent-engine/sessions/manage-sessions-api) — Detailed API for creating, getting, and listing sessions, including filtering by `user_id`.

### Context7 Library Docs
> **Lib-1:** `vertexai` — Used `agent_engines.sessions.list` for listing session resources.

## Current State
- **Backend**: `fast-api-fe/services/agent_client.py` maintains an in-memory `_session_store` mapping `user_id` to `session_id`.
- **API**: `/v1/chat/completions` does not explicitly handle `session_id` in the request/response body (it's handled internally).
- **Frontend**: `chat.js` sends a `force_new_session` flag but doesn't track `session_id`.

## 📋 Checklist
- [ ] Update `openai_schema.py` to include `session_id` in request/response models.
- [ ] Refactor `agent_client.py` to remove `_session_store` and add `list_user_sessions`.
- [ ] Update `chat.py` router to handle `session_id` and add session listing endpoint.
- [ ] Update `chat.js` to store and retrieve `session_id` from `localStorage`.
- [ ] Update `chat.html` and `style.css` for session management UI.

## Proposed Changes

### [Component] API Models & Routers

#### [MODIFY] [openai_schema.py](file:///Users/yannipeng/git-projects/customer-booking-agent/fast-api-fe/models/openai_schema.py)
- Add `session_id` to `ChatCompletionRequest` and `ChatCompletionResponse`.

#### [MODIFY] [chat.py](file:///Users/yannipeng/git-projects/customer-booking-agent/fast-api-fe/routers/chat.py)
- Update `chat_completions` to extract `session_id` from the request and return it in the response.
- Add `GET /v1/sessions` endpoint to list user sessions.

### [Component] Backend Services

#### [MODIFY] [agent_client.py](file:///Users/yannipeng/git-projects/customer-booking-agent/fast-api-fe/services/agent_client.py)
- Remove `_session_store`.
- Modify `query_agent` to accept `session_id` and return `(response_text, session_id)`.
- Add `list_user_sessions(user_id: str)` using `agent_engines.sessions.list`.

```python
async def query_agent(
    user_message: str,
    user_id: str = "web_user",
    session_id: Optional[str] = None,
    force_new: bool = False,
) -> tuple[str, str]:
    # ...
    if force_new or not session_id:
        remote_session = await remote_app.async_create_session(user_id=user_id)
        session_id = remote_session["id"]
    
    # Use session_id in query
    # ...
    return response_text, session_id

async def list_user_sessions(user_id: str):
    # Use agent_engines.sessions.list(filter=f'user_id="{user_id}"')
    pass
```

### [Component] Frontend

#### [MODIFY] [chat.js](file:///Users/yannipeng/git-projects/customer-booking-agent/fast-api-fe/static/chat.js)
- Maintain `currentSessionId` in `localStorage`.
- Send `session_id` in `fetchCompletion` requests.
- Update `currentSessionId` from the agent's response.
- Implement session switching logic by clicking on historical sessions.

#### [MODIFY] [style.css](file:///Users/yannipeng/git-projects/customer-booking-agent/fast-api-fe/static/style.css)
- Add styles for the session list items and active state in the sidebar.

## Verification Plan

### Automated Tests
- Create `tests/integration/test_agent_sessions.py` to verify session persistence and listing logic.
- Run: `uv run pytest tests/integration/test_agent_sessions.py`

### Manual Verification
1. **Start App**: `cd fast-api-fe && uv run python main.py`
2. **First Interaction**: Send a message and verify a session ID is generated and stored in `localStorage`.
3. **Persistence**: Refresh the page and verify the session continues without starting a new one.
4. **New Chat**: Click "New Chat" and verify a brand-new session is started (and `localStorage` is cleared).
5. **Session History**: Check the sidebar for the list of previous sessions (from `GET /v1/sessions`).
6. **Resuming**: Click a previous session and verify it "resumes" (agent context persists).
