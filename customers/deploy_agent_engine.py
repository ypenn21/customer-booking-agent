import os
import sys
import vertexai
from vertexai import agent_engines
# Add the project root to the Python path to allow for absolute imports
# This assumes deploy_agent_engine.py is inside bookings directory.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from customers.app import app

def main():
    project_id = os.environ.get("PROJECT_ID", "genai-apps-25")
    location = "us-central1" # Assuming this is the desired location
    staging_bucket = os.environ.get("STAGING_BUCKET", f"gs://{project_id}-adk-staging")

    if not project_id:
        print("Error: PROJECT_ID environment variable not set.")
        sys.exit(1)

    vertexai.init(project=project_id, location=location, staging_bucket=staging_bucket)

    print("Attempting to create/get Agent Engine Remote App...")
    environment_variables = {
        "GOOGLE_GENAI_USE_VERTEXAI": "TRUE",
        "GOOGLE_CLOUD_LOCATION": "us-central1",
        "BOOKINGS_AGENT_CARD_URL": "https://us-central1-aiplatform.googleapis.com/v1/projects/genai-apps-25/locations/us-central1/reasoningEngines/9162713079862001664"
    }

    # Create the agent engine
    # We need to pass the bookings package so that the remote environment
    # has access to all needed class definition.
    remote_app = agent_engines.create(
        app,
        requirements=[
            "google-adk>=1.16.0,<2.0.0",
            "a2a-sdk~=0.3.22",
            "nest-asyncio>=1.6.0,<2.0.0",
            "opentelemetry-instrumentation-google-genai>=0.1.0,<1.0.0",
            "gcsfs>=2024.11.0",
            "google-cloud-logging>=3.12.0,<4.0.0",
            "google-cloud-aiplatform[evaluation,agent-engines]>=1.130.0",
            "protobuf>=6.31.1,<7.0.0",
        ],
        extra_packages=["customers"],
        display_name="Customer Assistant",
        description="Assists in finding customer details and making bookings for each customer.",
        env_vars=environment_variables,
    )
    print(f"Agent Engine Remote App created: {remote_app.resource_name}")

if __name__ == "__main__":
    main()