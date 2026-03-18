"""
OpenAI-compatible Chat Completions API router.

Implements: POST /v1/chat/completions
Spec: https://platform.openai.com/docs/api-reference/chat/create

Proxies the last user message to the customers ADK agent on
Vertex AI Agent Engine and wraps the response in the OpenAI schema.
"""
import logging

from fastapi import APIRouter, HTTPException

from ..models.openai_schema import (
    ChatChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
)
from ..services.agent_client import query_agent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["Chat Completions"])


@router.post(
    "/chat/completions",
    response_model=ChatCompletionResponse,
    summary="Create a chat completion",
    description=(
        "OpenAI-compatible chat completions endpoint. "
        "Proxies the last user message to the customers ADK agent on Vertex AI Agent Engine."
    ),
)
async def chat_completions(req: ChatCompletionRequest) -> ChatCompletionResponse:
    # Extract the last user message (standard OpenAI pattern)
    user_msgs = [m for m in req.messages if m.role == "user"]
    if not user_msgs:
        raise HTTPException(status_code=400, detail="No user message found in request.")

    user_input = user_msgs[-1].content

    try:
        agent_reply = await query_agent(user_input)
    except Exception as exc:
        # Log the full traceback so the real GCP error is visible in server logs
        logger.exception("query_agent failed for input=%r", user_input[:80])
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return ChatCompletionResponse(
        model=req.model,
        choices=[
            ChatChoice(
                message=ChatMessage(role="assistant", content=agent_reply),
            )
        ],
    )
