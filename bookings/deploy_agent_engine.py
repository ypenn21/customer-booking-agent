import os
import sys
import subprocess
import vertexai
from vertexai import agent_engines
from vertexai import types
import google.auth
from google.auth.transport.requests import Request

# Add the project root to the Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from bookings.app import app

DISPLAY_NAME = "Booking Assistant"

def get_requirements_from_uv():
    """Generates a flat requirements list from the local pyproject.toml using uv."""
    # Export only the main dependencies as a flat list
    # Using shell=True and grep to filter out comments as per manual fix
    result = subprocess.run(
        f"uv export --format requirements-txt --no-hashes --no-dev --package bookings --no-emit-workspace | grep -v '#'",
        shell=True,
        capture_output=True,
        text=True,
        check=True,
        cwd=PROJECT_ROOT
    )
    # Filter out empty lines and comments
    return [line.strip() for line in result.stdout.splitlines() if line.strip() and not line.startswith("#")]

REQUIREMENTS = get_requirements_from_uv()

EXTRA_PACKAGES = ["bookings"]
DESCRIPTION = "Assists in making custom bookings and reservations."

def main():
    project_id = os.environ.get("PROJECT_ID")
    location = os.environ.get("LOCATION", "us-central1")
    staging_bucket = os.environ.get("STAGING_BUCKET", f"gs://{project_id}-adk-staging")

    # 1. FIX: Manually refresh credentials to ensure the 'email' field is populated
    # This prevents the "missing email field" error in Cloud Shell environments.
    credentials, _ = google.auth.default()
    try:
        if not credentials.valid:
            credentials.refresh(Request())
    except Exception as e:
        print(f"Note: Metadata credential refresh failed: {e}. Attempting gcloud fallback...")
        try:
            import subprocess
            from google.oauth2.credentials import Credentials as OAuth2Credentials
            token = subprocess.check_output(["gcloud", "auth", "print-access-token"], encoding="utf-8").strip()
            credentials = OAuth2Credentials(token)
            print("Successfully initialized credentials using gcloud fallback.")
        except Exception as fallback_err:
            print(f"Error: Auth fallback failed: {fallback_err}")
            # We continue and hope the SDK can handle it, but it likely will fail later.

    if not project_id:
        print("Error: PROJECT_ID environment variable not set.")
        sys.exit(1)

    # Initialize Vertex AI with the refreshed credentials
    vertexai.init(
        project=project_id, 
        location=location, 
        staging_bucket=staging_bucket,
        credentials=credentials
    )

    client = vertexai.Client(project=project_id, location=location, credentials=credentials)

    # Validate required environment variables for audience
    iap_expected_audience = os.environ.get("IAP_EXPECTED_AUDIENCE")

    if not iap_expected_audience:
        print("Error: IAP_EXPECTED_AUDIENCE environment variable not set.")
        print("This should be the aud claim in the IAP token.")
        sys.exit(1)

    environment_variables = {
        "GOOGLE_GENAI_USE_VERTEXAI": "TRUE",
        "GOOGLE_CLOUD_LOCATION": "global",
        "LOCATION": location,
        "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",
        "IAP_EXPECTED_AUDIENCE": iap_expected_audience,
    }

    # Check for an existing agent engine
    existing_resource_name = os.environ.get("BOOKINGS_ENGINE_ID")

    if existing_resource_name:
        print(f"Using BOOKINGS_ENGINE_ID from environment: {existing_resource_name}")
    else:
        print(f"Searching for existing Agent Engine with display_name='{DISPLAY_NAME}'...")
        try:
            # We pass the credentials here too for listing
            for engine in client.agent_engines.list():
                if engine.api_resource.display_name == DISPLAY_NAME:
                    existing_resource_name = engine.api_resource.name
                    print(f"Found existing Agent Engine: {existing_resource_name}")
                    break
        except Exception as e:
            print(f"Note: Could not list engines due to authentication limits: {e}")
            print("If you know your Engine ID, set it in BOOKINGS_ENGINE_ID in config.sh to skip this check.")

    config = {
        "display_name": DISPLAY_NAME,
        "description": DESCRIPTION,
        "requirements": REQUIREMENTS,
        "extra_packages": EXTRA_PACKAGES,
        "env_vars": environment_variables,
        "identity_type": types.IdentityType.AGENT_IDENTITY,
        "staging_bucket": staging_bucket,
    }

    if existing_resource_name:
        print(f"Updating existing Agent Engine: {existing_resource_name}")
        remote_app = client.agent_engines.update(
            name=existing_resource_name,
            agent=app,
            config=config
        )
        print(f"Agent Engine updated: {remote_app.api_resource.name}")
    else:
        print(f"No existing Agent Engine found. Creating new '{DISPLAY_NAME}'...")
        remote_app = client.agent_engines.create(
            agent=app,
            config=config
        )
        print(f"Agent Engine created: {remote_app.api_resource.name}")

if __name__ == "__main__":
    main()


