"""
OpenAI-compatible Chat Completions API router.

Implements:
  POST /v1/chat/completions  — proxy to Agent Engine, reusing the user's session
  POST /v1/sessions/new      — reset the session (triggered by "New chat")

Spec: https://platform.openai.com/docs/api-reference/chat/create
"""
import logging
import jwt

from fastapi import APIRouter, HTTPException, Request

from ..models.openai_schema import (
    ChatChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
)
from ..services.agent_client import query_agent, reset_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["Chat Completions"])


def _extract_user_id(request: Request) -> str:
    """Extract user identity from IAP JWT, falling back to 'web_user'."""
    iap_jwt = request.headers.get("X-Goog-IAP-JWT-Assertion")
    user_id = "web_user"
    if iap_jwt:
        try:
            decoded = jwt.decode(iap_jwt, options={"verify_signature": False})
            user_id = decoded.get("email", user_id)
            logger.info("Authenticated user from IAP: %s", user_id)
        except Exception as e:
            logger.warning("Failed to decode IAP JWT: %s", e)
    return user_id


@router.post(
    "/chat/completions",
    response_model=ChatCompletionResponse,
    summary="Create a chat completion",
    description=(
        "OpenAI-compatible chat completions endpoint. "
        "Proxies the last user message to the customers ADK agent on Vertex AI Agent Engine. "
        "The same Agent Engine session is reused across calls for the same user. "
        "Pass force_new_session=true in the request body to start a fresh session."
    ),
)
async def chat_completions(req: ChatCompletionRequest, request: Request) -> ChatCompletionResponse:
    # 1. Extract user identity from IAP JWT
    user_id = _extract_user_id(request)

    # 2. Extract the last user message (standard OpenAI pattern)
    user_msgs = [m for m in req.messages if m.role == "user"]
    if not user_msgs:
        raise HTTPException(status_code=400, detail="No user message found in request.")

    user_input = user_msgs[-1].content

    # 3. Query the agent, reusing or creating a session as requested
    force_new = getattr(req, "force_new_session", False)
    try:
        agent_reply = await query_agent(user_input, user_id=user_id, force_new=force_new)
    except Exception as exc:
        logger.exception("query_agent failed for input=%r", user_input[:80])
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ChatCompletionResponse(
        model=req.model,
        choices=[
            ChatChoice(
                message=ChatMessage(role="assistant", content=agent_reply),
            )
        ],
    )


@router.post(
    "/sessions/new",
    summary="Start a new chat session",
    description="Discards the current Agent Engine session so the next message starts a fresh one.",
)
async def new_session(request: Request):
    user_id = _extract_user_id(request)
    await reset_session(user_id)
    return {"status": "ok", "message": "Session reset. Next message will start a new session."}
