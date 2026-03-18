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

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import LongRunningFunctionTool
from google.genai import types
import os
import vertexai
from vertexai import agent_engines

vertexai.init(project="genai-apps-25", location="us-central1")
os.environ["GOOGLE_CLOUD_PROJECT"] = "genai-apps-25"
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

def request_user_input(message: str) -> dict:
    """Request additional input from the user.

    Use this tool when you need more information from the user to complete a task.
    Calling this tool will pause execution until the user responds.

    Args:
        message: The question or clarification request to show the user.
    """
    return {"status": "pending", "message": message}

async def bookings(request: str) -> str:
    """Delegates a booking request to the bookings agent.
    
    Args:
        request: The booking request from the user (e.g., "make a hotel reservation").
    """
    try:
        remote_app = agent_engines.get(
            "projects/genai-apps-25/locations/us-central1/reasoningEngines/9162713079862001664"
        )
        remote_session = await remote_app.async_create_session(user_id="customer_agent_a2a_user")
        
        final_text = []
        async for event in remote_app.async_stream_query(
            message=request, 
            user_id="customer_agent_a2a_user", 
            session_id=remote_session["id"]
        ):
            role = event.get("role") or event.get("content", {}).get("role")
            if role == "model":
                parts = event.get("content", {}).get("parts", [])
                for part in parts:
                    if "text" in part:
                        final_text.append(part["text"])
                        
        if final_text:
            return "\n".join(final_text)
        return "The bookings agent finished but provided no text response."
    except Exception as e:
        return f"Error communicating with bookings agent: {e}"

mock_db = {
    "alice": {"user_id": "u1022", "email": "alice@gmail.com", "loyalty_tier": "gold"},
    "bob": {"user_id": "u1023", "email": "bob@gmail.com", "loyalty_tier": "silver"},
    "charlie": {"user_id": "u1024", "email": "charlie@gmail.com", "loyalty_tier": "bronze"},
    "david": {"user_id": "u1025", "email": "david@gmail.com", "loyalty_tier": "gold"},
    "eve": {"user_id": "u1026", "email": "eve@gmail.com", "loyalty_tier": "silver"},
    "frank": {"user_id": "u1027", "email": "frank@gmail.com", "loyalty_tier": "bronze"},
    "grace": {"user_id": "u1028", "email": "grace@gmail.com", "loyalty_tier": "gold"},
    "harry": {"user_id": "u1029", "email": "harry@gmail.com", "loyalty_tier": "silver"},
    "ian": {"user_id": "u1030", "email": "ian@gmail.com", "loyalty_tier": "bronze"},
    "jane": {"user_id": "u1031", "email": "jane@gmail.com", "loyalty_tier": "gold"},
    "jack": {"user_id": "u1032", "email": "jack@gmail.com", "loyalty_tier": "silver"},
    "jill": {"user_id": "u1033", "email": "jill@gmail.com", "loyalty_tier": "bronze"}
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


root_agent = Agent(
    name="customers",
    model=Gemini(
        model="gemini-3-flash-preview",
        retry_options=types.HttpRetryOptions(attempts=3),
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

app = App(
    root_agent=root_agent,
    name="customers",
)
