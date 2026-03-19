import os
import sys
import vertexai
from vertexai import agent_engines

# Add the project root to the Python path to allow for absolute imports
# This assumes deploy_agent_engine.py is inside customers directory.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from customers.app import app

DISPLAY_NAME = "Customer Assistant"

REQUIREMENTS = [
    "google-cloud-aiplatform[evaluation,agent-engines]>=1.130.0",
    "google-adk>=1.16.0,<2.0.0",
    "a2a-sdk~=0.3.22",
    "nest-asyncio>=1.6.0,<2.0.0",
    "opentelemetry-instrumentation-google-genai>=0.1.0,<1.0.0",
    "gcsfs>=2024.11.0",
    "google-cloud-logging>=3.12.0,<4.0.0",
    "protobuf>=6.31.1,<7.0.0",
]

EXTRA_PACKAGES = ["customers"]

DESCRIPTION = "Assists in finding customer details and making bookings for each customer."


def main():
    project_id = os.environ.get("PROJECT_ID", "genai-apps-25")
    location = "us-central1"
    staging_bucket = os.environ.get("STAGING_BUCKET", f"gs://{project_id}-adk-staging")

    if not project_id:
        print("Error: PROJECT_ID environment variable not set.")
        sys.exit(1)

    vertexai.init(project=project_id, location=location, staging_bucket=staging_bucket)

    environment_variables = {
        "GOOGLE_GENAI_USE_VERTEXAI": "TRUE",
        "GOOGLE_CLOUD_LOCATION": "us-central1",
        "CUSTOMERS_ENGINE_ID": os.environ.get(
            "CUSTOMERS_ENGINE_ID",
            "projects/genai-apps-25/locations/us-central1/reasoningEngines/9102899647310987264",
        ),
        # Enable OpenTelemetry traces and logs for Agent Engine observability.
        # GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY enables agent traces and logs
        # (does NOT include prompt/response content by default).
        # OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT also logs the full
        # input prompts and output responses — disable if you want to avoid PII.
        "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",
    }

    # Check for an existing agent engine with the same display name
    existing = None
    print(f"Searching for existing Agent Engine with display_name='{DISPLAY_NAME}'...")
    for engine in agent_engines.list():
        if engine.display_name == DISPLAY_NAME:
            existing = engine
            print(f"Found existing Agent Engine: {engine.resource_name}")
            break

    if existing is not None:
        print(f"Updating existing Agent Engine: {existing.resource_name}")
        remote_app = existing.update(
            agent_engine=app,
            requirements=REQUIREMENTS,
            extra_packages=EXTRA_PACKAGES,
            display_name=DISPLAY_NAME,
            description=DESCRIPTION,
            env_vars=environment_variables,
        )
        print(f"Agent Engine updated: {remote_app.resource_name}")
    else:
        print(f"No existing Agent Engine found. Creating new '{DISPLAY_NAME}'...")
        remote_app = agent_engines.create(
            app,
            requirements=REQUIREMENTS,
            extra_packages=EXTRA_PACKAGES,
            display_name=DISPLAY_NAME,
            description=DESCRIPTION,
            env_vars=environment_variables,
        )
        print(f"Agent Engine created: {remote_app.resource_name}")


if __name__ == "__main__":
    main()