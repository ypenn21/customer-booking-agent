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

import sys
import os

# Add the 'bookings' directory to the Python path to resolve the module import.
# This is necessary for the Agent Engine environment to find local modules.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import FunctionTool, ToolContext, LongRunningFunctionTool
from google.genai import types
from security import validate_token

import google.auth
from google.auth.transport.requests import Request
import vertexai
import logging
import json
import httpx
from google.cloud import secretmanager

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

# Configure logging to capture INFO level messages
logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)

from a2a.types import AgentCard, AgentCapabilities, AgentSkill, TransportProtocol
from a2a.server.apps.jsonrpc.starlette_app import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from .agent_executor import AdkAgentToA2AExecutor
from vertexai.agent_engines import AdkApp

# ── Identity & Environment Initialization ────────────────────────────────
import google.auth
from google.auth.transport.requests import Request

# 1. Get default project/credentials
credentials, project_id = google.auth.default()

# 2. Log current identity info (without sensitive data)
try:
    if hasattr(credentials, 'service_account_email'):
        logger.info(f"{get_execution_context()} Booking Agent Identity: {credentials.service_account_email}")
    else:
        logger.info(f"{get_execution_context()} Booking Agent Identity Type: {type(credentials)}")
except:
    pass

# 3. Environment Overrides
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# 4. Initialize Vertex AI
vertexai.init(
    project=project_id,
    location=os.environ.get("LOCATION")
)
logging.info(f"{get_execution_context()} Booking Agent: Initialized Vertex AI for project {project_id}")

IAP_EXPECTED_AUDIENCE = os.environ.get("IAP_EXPECTED_AUDIENCE")
# ─────────────────────────────────────────────────────────────────────────


def get_secret(secret_id: str, version_id: str = "latest") -> str:
    """Retrieves a secret from Google Cloud Secret Manager.

    Args:
        secret_id: The ID of the secret to retrieve.
        version_id: The version of the secret to retrieve.

    Returns:
        The secret value.
    """
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode("UTF-8")


def get_jwt_user_id(tool_context: ToolContext = None) -> str:
    """Extracts and securely validates the user ID from the JWT in the tool context."""
    ctx = get_execution_context()
    if tool_context and tool_context.run_config and tool_context.run_config.custom_metadata:
        logger.info(f"{ctx} Received custom_metadata in tool_context: {tool_context.run_config.custom_metadata}")
        token = tool_context.run_config.custom_metadata.get("x-user-identity")

        if token:
            try:
                if not IAP_EXPECTED_AUDIENCE:
                    logger.error(f"{ctx} IAP_EXPECTED_AUDIENCE environment variable is missing.")
                    return "default_user"

                # Securely validate the token; security.py returns the payload dictionary
                decoded_claims = validate_token(token, IAP_EXPECTED_AUDIENCE)
                logger.info(f"{ctx} Decoded and validated JWT claims in get_jwt_user_id: {decoded_claims}")
                
                # Extract 'sub' from GCP Identity Platform or fallback to default
                return decoded_claims.get("gcip", {}).get("sub", decoded_claims.get("email", "default_user"))
            except Exception as e:
                logger.error(f"{ctx} Error validating JWT in get_jwt_user_id: {e}")
    return "default_user"


def get_access_token(jwt_user_id: str) -> str:
    """Retrieves the access token for the given user from Secret Manager."""
    secret_name = f"ms-tokens-{jwt_user_id}"
    secret_json = get_secret(secret_name)
    logger.info(f"{get_execution_context()} Successfully retrieved secret for {jwt_user_id}")
    token_data = json.loads(secret_json)
    return token_data.get("accessToken")


def make_booking(service: str, date: str, time: str, user_id: str = "default_user", tool_context: ToolContext = None) -> dict:
    """Makes a custom booking and returns mock data.

    Args:
        service: The name of the service to book.
        date: The date for the booking (e.g., YYYY-MM-DD).
        time: The time for the booking (e.g., HH:MM).
        user_id: The ID of the user making the booking.
        tool_context: Context provided by the agent runner.

    Returns:
        A dictionary containing the mock response from the booking API.
    """
    ctx = get_execution_context()
    logger.info(f"{ctx} Entering make_booking tool")
    jwt_user_id = get_jwt_user_id(tool_context)

    try:
        secret_name = f"ms-tokens-{jwt_user_id}"
        api_key = get_secret(secret_name)
        logger.info(f"{ctx} Successfully retrieved API key for {jwt_user_id}")
    except Exception as e:
        logger.error(f"{ctx} Error retrieving secret: {e}")
        return {
            "status": "error",
            "message": "Failed to retrieve API credentials. Please check Secret Manager configuration.",
        }

    # Mock data to simulate API response
    return {
        "status": "success",
        "booking_id": "mock_bk_001",
        "details": {
            "service": service,
            "date": date,
            "time": time,
            "user_id": user_id,
            "authenticated_user_id": jwt_user_id
        },
        "message": "Booking successfully created via mock API."
    }


def create_calendar_invite(
    subject: str,
    body_content: str,
    start_time: str,
    end_time: str,
    attendee_email: str = "colleague@example.example.com",
    attendee_name: str = "Project Lead",
    location: str = "Google Meet / Microsoft Teams",
    tool_context: ToolContext = None
) -> dict:
    """Creates a Microsoft Calendar invite using the Graph API."""
    ctx = get_execution_context()
    logger.info(f"{ctx} Inside create_calendar_invite tool.")
    
    jwt_user_id = get_jwt_user_id(tool_context)
    
    # ── Timezone Resolution ──────────────────────────────────────────────
    user_timezone = "UTC"
    if tool_context and tool_context.run_config and tool_context.run_config.custom_metadata:
        user_timezone = tool_context.run_config.custom_metadata.get("x-user-timezone", "UTC")
    
    logger.info(f"{ctx} Creating calendar invite for {jwt_user_id} in timezone {user_timezone}")

    try:
        access_token = get_access_token(jwt_user_id)
    except Exception as e:
        logger.error(f"{ctx} Error retrieving access token: {e}")
        return {"status": "error", "message": f"Could not retrieve access token: {e}"}

    url = "https://graph.microsoft.com/v1.0/me/events"
    
    auth_header = access_token
    if not str(auth_header).startswith("Bearer "):
        auth_header = f"Bearer {access_token}"
        
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json"
    }
    
    data = {
        "subject": subject,
        "body": {
            "contentType": "HTML",
            "content": body_content
        },
        "start": {
            "dateTime": start_time,
            "timeZone": user_timezone
        },
        "end": {
            "dateTime": end_time,
            "timeZone": user_timezone
        },
        "location": {
            "displayName": location
        },
        "attendees": [
            {
                "emailAddress": {
                    "address": attendee_email,
                    "name": attendee_name
                },
                "type": "required"
            }
        ],
        "allowNewTimeProposals": True,
        "isOnlineMeeting": True,
        "onlineMeetingProvider": "teamsForBusiness"
    }

    try:
        response = httpx.post(url, headers=headers, json=data)
        if response.status_code >= 400:
            logger.error(f"{ctx} Graph API Error {response.status_code}: {response.text}")
        response.raise_for_status()
        logger.info(f"{ctx} Calendar invite created successfully for {jwt_user_id}")
        return {
            "status": "success",
            "message": "Calendar invite created successfully.",
            "data": response.json()
        }
    except Exception as e:
        logger.exception(f"{ctx} Exception in create_calendar_invite: {e}")
        return {
            "status": "error",
            "message": f"Failed to create calendar invite: {e}"
        }


def request_user_input(message: str) -> dict:
    """Request additional input from the user."""
    return {"status": "pending", "message": message}


class UncachedGemini(Gemini):
    """Subclass of Gemini that prevents long-term caching of the HTTP client.
    
    This avoids 'Event loop is closed' or 'Different loop' errors in 
    multithreaded environments where a new thread/loop is created per request.
    """
    @property
    def api_client(self):
        # Clear the underlying cache keys to force recreation
        self.__dict__.pop("api_client", None)
        self.__dict__.pop("_api_backend", None)
        self.__dict__.pop("_live_api_client", None)
        
        # Defer to the base class descriptor to cleanly initialize a new client
        return super().api_client

def create_agent() -> Agent:
    """Factory function to create a fresh instance of the bookings agent.
    
    This helps prevent event loop mismatches by ensuring the Gemini model and its
    underlying async clients are initialized within the event loop that will 
    actually execute the agent.
    """
    exec_ctx = get_execution_context()
    logger.info(f"{exec_ctx} Creating fresh Booking Agent instance.")
    
    return Agent(
        name="bookings",
        model=UncachedGemini(
            model="gemini-3-flash-preview",
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        description="An agent that helps users make custom bookings and reservations.",
        instruction="""You are a helpful booking assistant designed to assist users in making reservations and scheduling calendar invites. 
        
        IMPORTANT: When a user asks to "make a booking", "create a reservation", or "schedule a meeting", you should:
        1. First, gather all necessary details: service/subject, date, time, and attendee information.
        2. Use the `create_calendar_invite` tool as the PRIMARY tool to record the booking on the user's Microsoft calendar. This tool is NOT a mock and performs real actions.
        3. Only use the `make_booking` tool if specifically asked to perform a "legacy booking" or if the calendar invite fails. `make_booking` is currently a mock for demonstration.
        
        RULES:
        1. NEVER guess the date or time.
        2. If details are missing, use the `request_user_input` tool to ask the user.
        """,
        tools=[
            make_booking,
            create_calendar_invite,
            LongRunningFunctionTool(func=request_user_input),
        ],
    )

# The AdkApp and Reasoning Engine will use the agent factory directly 
# instead of a shared global instance to avoid loop pollution.
root_agent = create_agent()

