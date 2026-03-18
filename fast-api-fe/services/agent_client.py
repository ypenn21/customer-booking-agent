"""
Agent Engine proxy service — calls the customers ADK agent via
Vertex AI Agent Engine API only. No local agent imports.

Configuration (via environment variables):
  PROJECT_ID            GCP project (default: genai-apps-25)
  LOCATION              Vertex AI region (default: us-central1)
  CUSTOMERS_ENGINE_ID   Full Agent Engine resource name
                        e.g. projects/<P>/locations/<L>/reasoningEngines/<ID>
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
    "projects/genai-apps-25/locations/us-central1/reasoningEngines/5452169199373778944"
)

vertexai.init(project=PROJECT_ID, location=LOCATION)
logger.info("vertexai initialised: project=%s location=%s engine=%s", PROJECT_ID, LOCATION, ENGINE_ID)


async def query_agent(user_message: str, user_id: str = "web_user") -> str:
    """
    Send a message to the customers Agent Engine and return the final text response.

    Uses create_session + stream_query — the same pattern as customers/agent.py
    uses to call the bookings engine.

    Args:
        user_message: The user's chat message.
        user_id:      A stable identifier for the caller.

    Returns:
        The agent's final text response, or an error string on failure.
    """
    try:
        if not ENGINE_ID:
            return "Error: CUSTOMERS_ENGINE_ID is not set." 
        remote_app = agent_engines.get(ENGINE_ID)
        remote_session = await remote_app.async_create_session(user_id=user_id)

        final_text = []
        async for event in remote_app.async_stream_query(
            message=user_message,
            user_id=user_id,
            session_id=remote_session["id"],
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
