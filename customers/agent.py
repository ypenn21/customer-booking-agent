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
import google.auth

_, project_id = google.auth.default()
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

from google.adk.tools import AgentTool
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

bookings_agent = RemoteA2aAgent(
    "bookings",
    agent_card=os.getenv("BOOKINGS_AGENT_CARD_URL", "http://127.0.0.1:8000/.well-known/agent-card.json")
)

mock_db = {
    "alice": {"user_id": "u4398", "email": "alice@example.com", "loyalty_tier": "gold"},
    "bob": {"user_id": "u1023", "email": "bob@example.com", "loyalty_tier": "silver"},
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
        AgentTool(bookings_agent),
        LongRunningFunctionTool(func=request_user_input),
    ],
)

app = App(
    root_agent=root_agent,
    name="customers",
)
