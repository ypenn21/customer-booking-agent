import asyncio
import logging
import os
from typing import Any

import nest_asyncio
import vertexai
from a2a.types import AgentCapabilities, AgentCard, TransportProtocol
from dotenv import load_dotenv
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder
from google.adk.apps import App
from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.cloud import logging as google_cloud_logging
from vertexai.preview.reasoning_engines import A2aAgent

from customers.agent import app as adk_app

# Load environment variables from .env file at runtime
load_dotenv()


class AgentEngineApp(A2aAgent):
    @staticmethod
    def create(
        app: App | None = None,
        artifact_service: Any = None,
        session_service: Any = None,
    ) -> Any:
        """Create an AgentEngineApp instance."""
        if app is None:
            app = adk_app

        def create_runner() -> Runner:
            """Create a Runner for the AgentEngineApp."""
            return Runner(
                app=app,
                session_service=session_service,
                artifact_service=artifact_service,
            )

        # Build agent card in an async context if needed
        try:
            asyncio.get_running_loop()
            # Running event loop detected - enable nested asyncio.run()
            nest_asyncio.apply()
        except RuntimeError:
            pass

        agent_card = asyncio.run(AgentEngineApp.build_agent_card(app=app))

        return AgentEngineApp(
            agent_executor_builder=lambda: A2aAgentExecutor(runner=create_runner()),
            agent_card=agent_card,
        )

    @staticmethod
    async def build_agent_card(app: App) -> AgentCard:
        """Builds the Agent Card dynamically from the app."""
        skill = AgentSkill(
            id="customers_booking_assistant",
            name="Customers Booking Assistant",
            description="Assists in making custom bookings and reservations.",
            tags=["customers", "bookings", "reservations"],
            examples=["Look up customer alice. Make a booking for alice on 04/04/2026 to 04/05/2026 arriving at 10am for a hotel in Sydney."],
        )
        agent_card_builder = AgentCardBuilder(
            agent=app.root_agent,
            # Agent Engine does not support streaming yet
            capabilities=AgentCapabilities(streaming=False),
            description="Customer management agent. Use this agent to look up customer details, and make bookings.",
            agent_version=os.getenv("AGENT_VERSION", "0.1.0"),
            skills=[skill],
        )
        agent_card = await agent_card_builder.build()
        agent_card.preferred_transport = TransportProtocol.http_json  # Http Only.
        agent_card.supports_authenticated_extended_card = True
        return agent_card

    def set_up(self) -> None:
        """Initialize the agent engine app with logging."""
        vertexai.init()
        super().set_up()
        logging.basicConfig(level=logging.INFO)
        logging_client = google_cloud_logging.Client()
        self.logger = logging_client.logger(__name__)
        if gemini_location:
            os.environ["GOOGLE_CLOUD_LOCATION"] = gemini_location

    def clone(self) -> "AgentEngineApp":
        """Returns a clone of the Agent Engine application."""
        return self


gemini_location = os.environ.get("GOOGLE_CLOUD_LOCATION")
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")
agent_engine = AgentEngineApp.create(
    app=adk_app,
    artifact_service=(
        GcsArtifactService(bucket_name=logs_bucket_name)
        if logs_bucket_name
        else InMemoryArtifactService()
    ),
    session_service=InMemorySessionService(),
)
