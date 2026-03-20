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

from typing import Optional

async def query_agent(
    user_message: str,
    user_id: str = "web_user",
    session_id: Optional[str] = None,
    force_new: bool = False,
) -> tuple[str, str]:
    """
    Send a message to the customers Agent Engine and return the final text response.
    
    Returns:
        tuple[str, str]: The text response and the session_id used.
    """
    try:
        if not ENGINE_ID:
            return "Error: CUSTOMERS_ENGINE_ID is not set.", ""
        remote_app = agent_engines.get(ENGINE_ID)
        
        if force_new or not session_id:
            remote_session = await remote_app.async_create_session(user_id=user_id)
            session_id = remote_session["id"]
        
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
            return "\n".join(final_text), session_id
        return "The agent finished but provided no text response.", session_id
    except Exception as e:
        logger.exception("query_agent failed for engine=%s", ENGINE_ID)
        return f"Error communicating with agent: {e}", session_id or ""

async def list_user_sessions(user_id: str) -> list[dict]:
    """
    List all sessions started by a user.
    """
    try:
        if not ENGINE_ID:
            return []
        # Uses the Reasoning Engine API to list sessions
        
        client = vertexai.Client(project=PROJECT_ID, location=LOCATION)
        sessions_iterator = client.agent_engines.sessions.list(
            name=ENGINE_ID,
            config={"filter": f'user_id="{user_id}"'}
        )
        return [{"id": s.name.split("/")[-1], "user_id": s.user_id} for s in sessions_iterator]
    except Exception as e:
        logger.exception("list_user_sessions failed")
        return []
