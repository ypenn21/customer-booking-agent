import os
import sys
import vertexai

# Add the project root to the Python path to allow for absolute imports
# This assumes deploy_agent_engine.py is inside bookings directory.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vertexai.preview.reasoning_engines import A2aAgent
from bookings.agent import agent_card, root_agent, app
from bookings.agent_executor import AdkAgentToA2AExecutor


def main():
    project_id = os.environ.get("PROJECT_ID", "genai-apps-25")
    location = "us-central1"
    staging_bucket = os.environ.get("STAGING_BUCKET", f"gs://{project_id}-adk-staging")

    if not project_id:
        print("Error: PROJECT_ID environment variable not set.")
        sys.exit(1)

    vertexai.init(project=project_id, location=location, staging_bucket=staging_bucket)

    print("Deploying A2A-enabled bookings agent to Agent Engine...")
    environment_variables = {
        "GOOGLE_GENAI_USE_VERTEXAI": "TRUE",
    }

    # A2aAgent exposes proper A2A endpoints (on_message_send, on_get_task,
    # handle_authenticated_agent_card) on Agent Engine — unlike AdkApp which
    # only exposes ADK streaming query methods with no A2A support.
    #
    # agent_executor_builder MUST be a lambda (not a constructed instance) so
    # the executor is built inside the remote container, not pickled locally.
    # a2a_agent = A2aAgent(
    #     agent_card=agent_card,
    #     agent_executor_builder=lambda: AdkAgentToA2AExecutor(root_agent),
    # )

    remote_app = vertexai.agent_engines.create(
        app,
        requirements=[
            "google-cloud-aiplatform[agent_engines]>=1.130.0",
            "google-adk>=1.16.0,<2.0.0",
            "a2a-sdk~=0.3.22",
            "nest-asyncio>=1.6.0,<2.0.0",
            "opentelemetry-instrumentation-google-genai>=0.1.0,<1.0.0",
            "gcsfs>=2024.11.0",
            "google-cloud-logging>=3.12.0,<4.0.0",
            "protobuf>=6.31.1,<7.0.0",
        ],
        extra_packages=["bookings"],
        display_name="Booking Assistant",
        description="Assists in making custom bookings and reservations.",
        env_vars=environment_variables,
    )
    print(f"Agent Engine Remote App created: {remote_app.resource_name}")


if __name__ == "__main__":
    main()