"""
OpenAI-compatible Chat Completions API router.

Implements: POST /v1/chat/completions
Spec: https://platform.openai.com/docs/api-reference/chat/create

Proxies the last user message to the customers ADK agent on
Vertex AI Agent Engine and wraps the response in the OpenAI schema.
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
async def chat_completions(req: ChatCompletionRequest, request: Request) -> ChatCompletionResponse:
    # 1. Extract user identity from IAP JWT
    iap_jwt = request.headers.get("X-Goog-IAP-JWT-Assertion")
    user_id = "web_user"  # Default for local testing
    
    if iap_jwt:
        try:
            # Note: For strict production security, you should verify the signature against Google's public keys.
            # Since the Google HTTP Load Balancer automatically strips forged X-Goog-IAP-JWT-Assertion headers,
            # decoding without verification here is a common pattern to extract the identity behind the LB.
            decoded = jwt.decode(iap_jwt, options={"verify_signature": False})
            # The IAP JWT contains the user's email in the 'email' claim
            user_id = decoded.get("email", user_id)
            logger.info("Authenticated user from IAP: %s", user_id)
        except Exception as e:
            logger.warning("Failed to decode IAP JWT: %s", e)

    # 2. Extract the last user message (standard OpenAI pattern)
    user_msgs = [m for m in req.messages if m.role == "user"]
    if not user_msgs:
        raise HTTPException(status_code=400, detail="No user message found in request.")

    user_input = user_msgs[-1].content

    # 3. Query the agent with the user_id
    try:
        agent_reply = await query_agent(user_input, user_id=user_id)
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

