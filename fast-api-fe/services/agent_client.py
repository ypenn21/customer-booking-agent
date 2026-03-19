"""
Agent Engine proxy service — calls the customers ADK agent via
Vertex AI Agent Engine API only. No local agent imports.

Configuration (via environment variables):
  PROJECT_ID            GCP project (default: genai-apps-25)
  LOCATION              Vertex AI region (default: us-central1)
  CUSTOMERS_ENGINE_ID   Full Agent Engine resource name
                        e.g. projects/<P>/locations/<L>/reasoningEngines/<ID>

Session management:
  Sessions are persisted in memory (per user_id) so conversation context is
  maintained across multiple HTTP calls.  Pass force_new=True to discard the
  existing session and start a fresh one (triggered by the "New chat" button).
"""
import asyncio
import logging
import os

import vertexai
from vertexai import agent_engines

logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("PROJECT_ID", "genai-apps-25")
LOCATION   = os.environ.get("LOCATION", "us-central1")
ENGINE_ID  = os.environ.get(
    "CUSTOMERS_ENGINE_ID",
    "projects/genai-apps-25/locations/us-central1/reasoningEngines/4698379211742642176"
)

vertexai.init(project=PROJECT_ID, location=LOCATION)
logger.info("vertexai initialised: project=%s location=%s engine=%s", PROJECT_ID, LOCATION, ENGINE_ID)

# In-memory store: user_id -> session_id
# (simple dict is fine — single-process uvicorn; use Redis/DB for multi-replica)
_session_store: dict[str, str] = {}


async def get_or_create_session(remote_app, user_id: str, force_new: bool = False) -> str:
    """
    Return an existing session_id for the user, or create a new one.

    Args:
        remote_app: The Agent Engine app handle.
        user_id:    Stable user identifier.
        force_new:  If True, always create a brand-new session.

    Returns:
        A session_id string.
    """
    if not force_new and user_id in _session_store:
        session_id = _session_store[user_id]
        logger.debug("Reusing session %s for user %s", session_id, user_id)
        return session_id

    remote_session = await remote_app.async_create_session(user_id=user_id)
    session_id = remote_session["id"]
    _session_store[user_id] = session_id
    logger.info("Created %ssession %s for user %s", "new " if force_new else "", session_id, user_id)
    return session_id


async def query_agent(
    user_message: str,
    user_id: str = "web_user",
    force_new: bool = False,
) -> str:
    """
    Send a message to the customers Agent Engine and return the final text response.

    Reuses the existing session for `user_id` unless `force_new` is True.

    Args:
        user_message: The user's chat message.
        user_id:      A stable identifier for the caller.
        force_new:    If True, start a brand-new session (clears context).

    Returns:
        The agent's final text response, or an error string on failure.
    """
    try:
        if not ENGINE_ID:
            return "Error: CUSTOMERS_ENGINE_ID is not set."
        remote_app = agent_engines.get(ENGINE_ID)
        session_id = await get_or_create_session(remote_app, user_id, force_new=force_new)

        final_text = []
        async for event in remote_app.async_stream_query(
            message=user_message,
            user_id=user_id,
            session_id=session_id,
        ):
            role = event.get("role") or event.get("content", {}).get("role")
            if role == "model":
                for part in event.get("content", {}).get("parts", []):
                    if "text" in part:
                        final_text.append(part["text"])

        if final_text:
            return "\n".join(final_text)
        return "The agent finished but provided no text response."
    except Exception as e:
        logger.exception("query_agent failed for engine=%s", ENGINE_ID)
        return f"Error communicating with agent: {e}"


async def reset_session(user_id: str) -> None:
    """
    Discard the stored session for `user_id` so the next query creates a fresh one.
    """
    _session_store.pop(user_id, None)
    logger.info("Session reset for user %s", user_id)
