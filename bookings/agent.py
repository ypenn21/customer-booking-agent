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
from fastapi import FastAPI

from a2a.types import AgentCard, AgentCapabilities, AgentSkill, TransportProtocol
from a2a.server.apps.jsonrpc.starlette_app import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from .agent_executor import AdkAgentToA2AExecutor
from vertexai.agent_engines import AdkApp
_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


def make_booking(service: str, date: str, time: str, user_id: str = "default_user") -> dict:
    """Makes a custom booking and returns mock data.

    Args:
        service: The name of the service to book.
        date: The date for the booking (e.g., YYYY-MM-DD).
        time: The time for the booking (e.g., HH:MM).
        user_id: The ID of the user making the booking.

    Returns:
        A dictionary containing the mock response from the booking API.
    """
    print(f"Making booking for {user_id} for {service} on {date} at {time}")
    # Mock data to simulate API response
    return {
        "status": "success",
        "booking_id": "mock_bk_001",
        "details": {
            "service": service,
            "date": date,
            "time": time,
            "user_id": user_id
        },
        "message": "Booking successfully created via mock API."
    }


def request_user_input(message: str) -> dict:
    """Request additional input from the user.

    Use this tool when you need more information from the user to complete a task.
    Calling this tool will pause execution until the user responds.

    Args:
        message: The question or clarification request to show the user.
    """
    return {"status": "pending", "message": message}


root_agent = Agent(
    name="bookings",
    model=Gemini(
        model="gemini-3-flash-preview",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description="An agent that helps users make custom bookings and reservations.",
    instruction="""You are a helpful booking assistant designed to assist users in making reservations. Use the make_booking tool to fulfill requests.
    IMPORTANT RULES:
    1. NEVER guess the date or time of a booking.
    2. If the user does not provide the date, time, or service, you MUST use the request_user_input tool to ask them for it before calling make_booking.
    """,
    tools=[
        make_booking,
        LongRunningFunctionTool(func=request_user_input),
    ],
)

app = AdkApp(
    agent=root_agent,
)

capabilities = AgentCapabilities(streaming=False)
skill = AgentSkill(
    id="bookings_assistant",
    name="Bookings Assistant",
    description="Assists in making custom bookings and reservations.",
    tags=["bookings", "reservations"],
    examples=["Make a booking for alice on 04/04/2026 to 04/05/2026 arriving at 10am for a hotel in Sydney."],
)

agent_card = AgentCard(
    name="bookings",
    description="An agent that helps users make custom bookings and reservations.",
    url="http://127.0.0.1:8000",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=capabilities,
    skills=[skill],
    preferredTransport=TransportProtocol.http_json,
)

request_handler = DefaultRequestHandler(
    agent_executor=AdkAgentToA2AExecutor(root_agent),
    task_store=InMemoryTaskStore(),
)

_base_a2a_app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler,
).build()

a2a_app = FastAPI()
a2a_app.mount("", _base_a2a_app)
