# booking

ReAct agent with A2A protocol [experimental]
Agent generated with [`googleCloudPlatform/agent-starter-pack`](https://github.com/GoogleCloudPlatform/agent-starter-pack) version `0.39.3`

## Project Structure

```
booking/
├── app/         # Core agent code
│   ├── agent.py               # Main agent logic
│   ├── deploy_agent_engine.py    # Agent Engine application logic
│   └── app_utils/             # App utilities and helpers
├── .cloudbuild/               # CI/CD pipeline configurations for Google Cloud Build
├── deployment/                # Infrastructure and deployment scripts
├── notebooks/                 # Jupyter notebooks for prototyping and evaluation
├── tests/                     # Unit, integration, and load tests
├── GEMINI.md                  # AI-assisted development guide
├── Makefile                   # Development commands
└── pyproject.toml             # Project dependencies
```

> 💡 **Tip:** Use [Gemini CLI](https://github.com/google-gemini/gemini-cli) for AI-assisted development - project context is pre-configured in `GEMINI.md`.

## Requirements

Before you begin, ensure you have:

- **uv**: Python package manager (used for all dependency management in this project) - [Install](https://docs.astral.sh/uv/getting-started/installation/) ([add packages](https://docs.astral.sh/uv/concepts/dependencies/) with `uv add <package>`)
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)
- **Terraform**: For infrastructure deployment - [Install](https://developer.hashicorp.com/terraform/downloads)
- **make**: Build automation tool - [Install](https://www.gnu.org/software/make/) (pre-installed on most Unix-based systems)

## Quick Start

Install required packages and launch the local development environment:

```bash
make install && make playground
```

## Commands

| Command                           | Description                                              |
| --------------------------------- | -------------------------------------------------------- |
| `make install`                    | Install dependencies using uv                            |
| `make playground`                 | Launch local development environment                     |
| `make lint`                       | Run code quality checks                                  |
| `make test`                       | Run unit and integration tests                           |
| `make deploy`                     | Deploy agent to Agent Engine                             |
| `make register-gemini-enterprise` | Register deployed agent to Gemini Enterprise             |
| `make inspector`                  | Launch A2A Protocol Inspector                            |
| `make setup-dev-env`              | Set up development environment resources using Terraform |

For full command options and usage, refer to the [Makefile](Makefile).

## 🛠️ Project Management

| Command                             | What It Does                                                   |
| ----------------------------------- | -------------------------------------------------------------- |
| `uvx agent-starter-pack setup-cicd` | One-command setup of entire CI/CD pipeline + infrastructure    |
| `uvx agent-starter-pack upgrade`    | Auto-upgrade to latest version while preserving customizations |
| `uvx agent-starter-pack extract`    | Extract minimal, shareable version of your agent               |

---

## Development

Edit your agent logic in `app/agent.py` and test with `make playground` - it auto-reloads on save.
Use notebooks in `notebooks/` for prototyping and Vertex AI Evaluation.
See the [development guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/development-guide) for the full workflow.

## Deployment

```bash
gcloud config set project <your-project-id>
make deploy
```

To set up your production infrastructure, run `uvx agent-starter-pack setup-cicd`.
See the [deployment guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/deployment) for details.

## Observability

Built-in telemetry exports to Cloud Trace, BigQuery, and Cloud Logging.
See the [observability guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/observability) for queries and dashboards.

## A2A Inspector

This agent supports the [A2A Protocol](https://a2a-protocol.org/). Use `make inspector` to test interoperability.
See the [A2A Inspector docs](https://github.com/a2aproject/a2a-inspector) for details.

## Add Permission to Agent Engine Default SA

```bash
gcloud projects add-iam-policy-binding genai-apps-25 --member="serviceAccount:service-803095609412@gcp-sa-aiplatform-re.iam.gserviceaccount.com" --role="roles/aiplatform.user"
```

## How to Run:

1. start bookings agent

```bash
uv run uvicorn bookings.agent:a2a_app --reload --port 8000
```

2. deploy bookings agent to agent engine

```bash
uv run python bookings/deploy_agent_engine.py
```

3. start customers agent

```bash
uv run adk web --port 8001
```

4. deploy customers agent to agent engine

```bash
uv run python customers/deploy_agent_engine.py
```

```
# a2a

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import LongRunningFunctionTool
from google.genai import types
from google.adk.tools import AgentTool
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
import os
import httpx
import google.auth
from google.auth.transport.requests import Request

class GoogleAuth(httpx.Auth):
    def __init__(self):
        self.credentials, self.project_id = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )

    def auth_flow(self, request):
        if not self.credentials.valid:
            self.credentials.refresh(Request())
        request.headers["Authorization"] = f"Bearer {self.credentials.token}"
        yield request


_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = "genai-apps-25"
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
agent_card=os.getenv("BOOKINGS_AGENT_CARD_URL", "https://us-central1-aiplatform.googleapis.com/v1/projects/genai-apps-25/locations/us-central1/reasoningEngines/9162713079862001664")
#agent_card=os.getenv("BOOKINGS_AGENT_CARD_URL", "http://127.0.0.1:8000/.well-known/agent-card.json")

def request_user_input(message: str) -> dict:
    """Request additional input from the user.

    Use this tool when you need more information from the user to complete a task.
    Calling this tool will pause execution until the user responds.

    Args:
        message: The question or clarification request to show the user.
    """
    return {"status": "pending", "message": message}

class AuthedRemoteA2aAgent(RemoteA2aAgent):
    async def _ensure_httpx_client(self) -> httpx.AsyncClient:
        client = await super()._ensure_httpx_client()
        if client.auth is None:
            client.auth = GoogleAuth()
        return client

bookings_agent = AuthedRemoteA2aAgent(
    "bookings",
    agent_card=agent_card,
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

```

```
# no a2a
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
```
