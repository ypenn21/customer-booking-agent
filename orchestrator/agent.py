# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo
import logging
import asyncio
import os
import sys
import jwt

# This is necessary for the Agent Engine environment to find local modules.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging to capture INFO level messages
logging.basicConfig(level=logging.INFO, force=True)

# [LEGACY - NOT UTILIZED]
# Previously used by the legacy `bookings()` function tool to consume stream_query()
# events when calling the Bookings agent via a hardcoded Reasoning Engine ID.
# Superseded by A2A subagent delegation (`discover_bookings_a2a_agent`).
def _consume_response_stream(response_stream) -> str:
    """Helper to consolidate text from an ADK response stream."""
    final_text = []
    for event in response_stream:
        # ADK stream events can be dicts (common in remote calls) or objects
        if isinstance(event, dict):
            content = event.get("content", {})
            role = event.get("role") or content.get("role")
            if role == "model":
                for part in content.get("parts", []):
                    if "text" in part:
                        final_text.append(part["text"])
        elif hasattr(event, "content") and hasattr(event.content, "role"):
            if event.content.role == "model":
                for part in event.content.parts:
                    if hasattr(part, "text"):
                        final_text.append(part.text)
    return "\n".join(final_text)

import google.auth
from google.auth.transport.requests import Request
import vertexai
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import LongRunningFunctionTool
from google.adk.tools.tool_context import ToolContext
from google.genai import Client, types
from vertexai import agent_engines

try:
    from .security import validate_token
    from .a2a_discovery import discover_bookings_a2a_agent
except ImportError:
    from security import validate_token
    from a2a_discovery import discover_bookings_a2a_agent

# ── Identity & Environment Initialization ────────────────────────────────
import google.auth
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

# 1. Get default project/credentials
credentials, project_id = google.auth.default()

# 2. Log current identity info (without sensitive data)
try:
    if hasattr(credentials, 'service_account_email'):
        logger.info(f"Orchestrator Agent Identity: {credentials.service_account_email}")
    else:
        logger.info(f"Orchestrator Agent Identity Type: {type(credentials)}")
except:
    pass

# 3. Environment Overrides
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# 4. Initialize Vertex AI
# We only pass credentials if we're not in Reasoning Engine (where ADC is preferred)
# RE sets AIP_ENGINE_ID, so we can check for that or just rely on ADC.
vertexai.init(
    project=project_id,
    location=os.environ.get("LOCATION")
)
logging.info(f"Orchestrator Agent: Initialized Vertex AI for project {project_id}")

# [LEGACY - NOT UTILIZED]
# Previously used by the legacy `bookings()` function tool.
# Dynamic discovery via Google Cloud Agent Registry (`a2a_discovery.py`) is used instead.
ENGINE_ID  = os.environ.get(
    "BOOKINGS_ENGINE_ID"
)
IAP_EXPECTED_AUDIENCE = os.environ.get("IAP_EXPECTED_AUDIENCE")
# ─────────────────────────────────────────────────────────────────────────

def request_user_input(message: str) -> dict:
    """Request additional input from the user.

    Use this tool when you need more information from the user to complete a task.
    Calling this tool will pause execution until the user responds.

    Args:
        message: The question or clarification request to show the user.
    """
    return {"status": "pending", "message": message}

# ── Booking Session Design Decision ──────────────────────────────────────
# A new session is created for every booking tool call (one-shot pattern).
#
# Why NOT reuse the same session across calls:
#   - The orchestrator agent is the state aggregator; the booking agent is a
#     stateless executor that receives all required data in a single request.
#   - Context isolation: independent booking requests won't bleed into each
#     other (e.g. hotel booking context polluting a later flight booking).
#   - Automatic recovery: if a session errors out, the next call starts fresh.
#
# Why NOT use the orchestrator's session_id for the booking session:
#   - The Agent Engine API (async_create_session) does NOT accept a custom
#     session_id when called remotely. The underlying AdkApp layer supports it,
#     but the default Vertex AI session service backing Agent Engine always
#     generates its own ID.
#
# If session reuse is ever needed (e.g. multi-turn booking workflows):
#   1. Store the server-generated session ID in tool_context.state
#      (tool_context.state["booking_session_id"]) after the first call.
#   2. On subsequent calls, check for the stored ID and skip creation.
#   3. Or use remote_app.list_sessions(user_id=...) to find an existing session.
# ─────────────────────────────────────────────────────────────────────────
# [LEGACY - NOT UTILIZED]
# This function tool is retained for reference only and is no longer registered on
# the orchestrator agent. Delegation to the Bookings agent now happens via
# `sub_agents=[bookings_remote_agent]` using Agent Registry discovery and A2A
# (see `orchestrator/a2a_discovery.py` and `create_agent()` below).
def bookings(request: str, tool_context: ToolContext) -> str:
    """Delegates a booking request to the bookings agent.
    
    Args:
        request: The booking request from the user (e.g., "make a hotel reservation").
    """
    user_id = tool_context.user_id
    user_timezone = "UTC"
    
    received_token = None
    if tool_context.run_config and tool_context.run_config.custom_metadata:
        received_token = tool_context.run_config.custom_metadata.get("x-user-identity")
        user_timezone = tool_context.run_config.custom_metadata.get("x-user-timezone", "UTC")

    if not received_token:
        return "Error: Missing authentication token."
    if not IAP_EXPECTED_AUDIENCE:
        return "Error: Orchestrator agent audience not configured."
        
    try:
        # Log claims of the token received
        try:
            decoded_claims = jwt.decode(received_token, options={"verify_signature": False})
            logger.info(f"Orchestrator Agent: Decoded claims: {decoded_claims}")
        except Exception as e:
            logger.error(f"Orchestrator Agent: Failed to decode received token: {e}")

        # 1. Validate the token received through the x-user-identity metadata
        validate_token(received_token, IAP_EXPECTED_AUDIENCE)
        logger.info("Successfully validated token for orchestrator agent.")

    except Exception as e:
        logger.exception("Token validation failed.")
        return f"Authentication error: {e}"

    headers = {
        "x-user-identity": received_token,
        "x-user-timezone": user_timezone
    }
    remote_run_config = {"custom_metadata": headers}
    logger.info(f"Orchestrator Agent: Delegating to Bookings agent (ID: {ENGINE_ID}). Request: {request}")

    try:
        # We use the SYNCHRONOUS version of the SDK methods here.
        # Reasoning Engine (Vertex AI Agent Engine) sync methods use 'requests' internally,
        # which avoids the 'Event loop is closed' or 'attached to a different loop' 
        # errors that plague aiohttp in multi-threaded Python environments.
        remote_app = agent_engines.get(
            ENGINE_ID
        )
        logger.info(f"Orchestrator Agent: Creating remote session for user {user_id}...")
        remote_session = remote_app.create_session(
            user_id=user_id,
        )
        logger.info(f"Orchestrator Agent: Remote session created: {remote_session['id']}. Sending query...")

        # For ADK agents, we use stream_query (sync) to avoid loop errors.
        # It returns an iterable of events.
        response_stream = remote_app.stream_query(
            message=request, 
            user_id=user_id, 
            session_id=remote_session["id"],
            run_config=remote_run_config,
        )

        response = _consume_response_stream(response_stream)
        
        if response:
            logger.info(f"Orchestrator Agent: Received response from Bookings agent: {response[:100]}...")
            return response
        
        logger.warning("Orchestrator Agent: Bookings agent provided no text response in the stream.")
        return "The bookings agent finished but provided no text response."

    except Exception as e:
        logger.exception(f"Orchestrator Agent: Error communicating with bookings agent: {e}")
        return f"Error communicating with bookings agent: {e}"

import threading
import asyncio

def get_execution_context() -> str:
    """Returns a string identifying the current thread and event loop."""
    thread_id = threading.get_ident()
    try:
        loop_id = id(asyncio.get_running_loop())
    except RuntimeError:
        loop_id = "no_running_loop"
    return f"[Thread: {thread_id}, Loop: {loop_id}]"

class UncachedGemini(Gemini):
    """Subclass of Gemini that prevents long-term caching of the HTTP client.
    
    This avoids 'Event loop is closed' or 'Different loop' errors in 
    multithreaded environments where a new thread/loop is created per request.
    
    NOTE: This creates a fresh google.genai.Client (and thus a fresh aiohttp 
    session) on every access. While this solves loop binding issues, it 
    sacrifices HTTP connection pooling. For Agent Engine traffic this is 
    typically acceptable, but may introduce slight latency overhead due to 
    repeated TCP/TLS handshakes at high concurrency.
    """
    @property
    def api_client(self) -> Client:
        kwargs = {
            'http_options': types.HttpOptions(
                headers=self._tracking_headers(),
                retry_options=self.retry_options,
                base_url=self.base_url,
            )
        }
        if self.model.startswith('projects/'):
            kwargs['vertexai'] = True

        return Client(**kwargs)

def create_agent() -> Agent:
    """Factory function to create a fresh instance of the orchestrator agent.
    
    Initializing the agent and its model within a factory prevents stateful async clients
    from being reused across different event loops, which is a common cause of 
    'Event loop is closed' errors in multi-threaded environments like Agent Engine.
    """
    registry_location = (
        os.environ.get("LOCATION")
        or os.environ.get("AGENT_REGISTRY_LOCATION", "us-central1")
    )
    target_display_name = os.environ.get(
        "BOOKINGS_AGENT_DISPLAY_NAME", "Booking Assistant"
    )
    bookings_remote_agent = discover_bookings_a2a_agent(
        project_id=project_id,
        location=registry_location,
        target_display_name=target_display_name,
    )

    return Agent(
        name="orchestrator",
        model=UncachedGemini(
            model="gemini-3.8-flash",
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        description="Main orchestrator agent that routes user requests to specialized subagents.",
        instruction="""You are the main orchestrator agent. Your primary goal is to understand the user's intent and route their request to the appropriate specialized subagent.
        
        Currently, you have access to the following subagents:
        1. **Bookings Agent** (`bookings`): Transfer to the `bookings` subagent for any requests related to travel bookings, hotel reservations, flight scheduling, or calendar invites.
        
        If a user's request doesn't match any specialized subagent, try to help them directly or ask for clarification.
        """,
        sub_agents=[bookings_remote_agent],
        tools=[
            LongRunningFunctionTool(func=request_user_input),
        ],
    )

# For backward compatibility and local testing
root_agent = create_agent()
