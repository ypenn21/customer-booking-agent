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
from google.genai import types
from vertexai import agent_engines

from .security import validate_token

# ── Identity & Environment Initialization ────────────────────────────────
import google.auth
from google.auth.transport.requests import Request

# 1. Get default project/credentials
credentials, project_id = google.auth.default()

# 2. Log current identity info (without sensitive data)
try:
    if hasattr(credentials, 'service_account_email'):
        logger.info(f"Customer Agent Identity: {credentials.service_account_email}")
    else:
        logger.info(f"Customer Agent Identity Type: {type(credentials)}")
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
logging.info(f"Customer Agent: Initialized Vertex AI for project {project_id}")

ENGINE_ID  = os.environ.get(
    "BOOKINGS_ENGINE_ID"
)
IAP_EXPECTED_AUDIENCE = os.environ.get("IAP_EXPECTED_AUDIENCE")
# ─────────────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

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
#   - The customer agent is the state aggregator; the booking agent is a
#     stateless executor that receives all required data in a single request.
#   - Context isolation: independent booking requests won't bleed into each
#     other (e.g. hotel booking context polluting a later flight booking).
#   - Automatic recovery: if a session errors out, the next call starts fresh.
#
# Why NOT use the customer's session_id for the booking session:
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
async def bookings(request: str, tool_context: ToolContext) -> str:
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
        return "Error: Customer agent audience not configured."
        
    try:
        # Log claims of the token received
        try:
            decoded_claims = jwt.decode(received_token, options={"verify_signature": False})
            logger.info(f"Customer Agent: Decoded claims: {decoded_claims}")
        except Exception as e:
            logger.error(f"Customer Agent: Failed to decode received token: {e}")

        # 1. Validate the token received through the x-user-identity metadata
        validate_token(received_token, IAP_EXPECTED_AUDIENCE)
        logger.info("Successfully validated token for customer agent.")

    except Exception as e:
        logger.exception("Token validation failed.")
        return f"Authentication error: {e}"

    headers = {
        "x-user-identity": received_token,
        "x-user-timezone": user_timezone
    }
    remote_run_config = {"custom_metadata": headers}
    logger.info(f"Customer Agent: Delegating to Bookings agent (ID: {ENGINE_ID}). Request: {request}")

    try:
        # We use the ASYNCHRONOUS version of the SDK methods here as requested.
        remote_app = agent_engines.get(ENGINE_ID)
        logger.info(f"Customer Agent: Creating remote session for user {user_id}...")
        remote_session = await remote_app.async_create_session(user_id=user_id)
        logger.info(f"Customer Agent: Remote session created: {remote_session['id']}. Sending query...")

        final_text = []
        async for event in remote_app.async_stream_query(
            message=request, 
            user_id=user_id, 
            session_id=remote_session["id"],
            run_config=remote_run_config,
        ):
            # ADK stream events can be dicts or objects
            if isinstance(event, dict):
                content = event.get("content", {})
                role = event.get("role") or content.get("role")
                if role == "model":
                    parts = content.get("parts", [])
                    for part in parts:
                        if "text" in part:
                            final_text.append(part["text"])
            elif hasattr(event, "content") and hasattr(event.content, "role"):
                if event.content.role == "model":
                    for part in event.content.parts:
                        if hasattr(part, "text"):
                            final_text.append(part.text)
                        
        if final_text:
            response = "\n".join(final_text)
            logger.info(f"Customer Agent: Received response from Bookings agent: {response[:100]}...")
            return response
        
        logger.warning("Customer Agent: Bookings agent provided no text response.")
        return "The bookings agent finished but provided no text response."

    except Exception as e:
        logger.exception(f"Customer Agent: Error communicating with bookings agent: {e}")
        return f"Error communicating with bookings agent: {e}"
mock_db = {
    "alice": {"user_id": "u1022", "email": "alice@example.com", "loyalty_tier": "gold"},
    "bob": {"user_id": "u1023", "email": "bob@example.com", "loyalty_tier": "silver"},
    "charlie": {"user_id": "u1024", "email": "charlie@example.com", "loyalty_tier": "bronze"},
    "david": {"user_id": "u1025", "email": "david@example.com", "loyalty_tier": "gold"},
    "eve": {"user_id": "u1026", "email": "eve@example.com", "loyalty_tier": "silver"},
    "frank": {"user_id": "u1027", "email": "frank@example.com", "loyalty_tier": "bronze"},
    "grace": {"user_id": "u1028", "email": "grace@example.com", "loyalty_tier": "gold"},
    "harry": {"user_id": "u1029", "email": "harry@example.com", "loyalty_tier": "silver"},
    "ian": {"user_id": "u1030", "email": "ian@example.com", "loyalty_tier": "bronze"},
    "jane": {"user_id": "u1031", "email": "jane@example.com", "loyalty_tier": "gold"},
    "jack": {"user_id": "u1032", "email": "jack@example.com", "loyalty_tier": "silver"},
    "jill": {"user_id": "u1033", "email": "jill@example.com", "loyalty_tier": "bronze"}
}

def get_customer(name: str) -> dict:
    """Gets customer information by name.

    Args:
        name: The name of the customer to look up.

    Returns:
        dict: The customer information or all customers.
    """
        
    customer = mock_db.get(name.lower())
    if customer:
        return {"status": "success", "customer": customer}
    return {"status": "error", "message": f"Customer '{name}' not found."}

def get_all_customers() -> dict:
    """Gets all customers."""
    return {"status": "success", "customers": mock_db}


def create_agent() -> Agent:
    """Factory function to create a fresh instance of the customers agent.
    
    Initializing the agent and its model within a factory prevents stateful async clients
    from being reused across different event loops, which is a common cause of 
    'Event loop is closed' errors in multi-threaded environments like Agent Engine.
    """
    return Agent(
        name="customers",
        model=Gemini(
            model="gemini-3-flash-preview",
            retry_options=types.HttpRetryOptions(attempts=3),
            api_client=None, # Force fresh client creation for this instance
        ),
        description="Customer management agent. Use this agent to look up customer details.",
        instruction="""You are the main customer orchestrator. Look up customer details using the `get_customer` or get_all_customers tools.
        If the user wants to make a booking, look up their user_id first, then delegate to the bookings agent using the `bookings` tool.
        """,
        tools=[
            get_customer,
            get_all_customers,
            bookings,
            LongRunningFunctionTool(func=request_user_input),
        ],
    )

# For backward compatibility and local testing
root_agent = create_agent()
