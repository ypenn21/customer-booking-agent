# Implementation Plan - Refactor Customers Agent to Orchestrator Agent

## 1. 🔍 Analysis & Context
*   **Objective:** Refactor the existing `customers/` agent into an `orchestrator/` agent. This involves renaming the directory and files, removing customer-specific logic, updating the agent's role to focus on routing to subagents (like the bookings agent), and updating all references throughout the repository.
*   **Affected Files:**
    *   `customers/` (Entire directory renamed to `orchestrator/`)
    *   `customers/agent.py`
    *   `customers/app.py`
    *   `customers/deploy_agent_engine.py`
    *   `customers/pyproject.toml`
    *   `pyproject.toml` (root)
    *   `fast-api-fe/main.py`
    *   `fast-api-fe/routers/chat.py`
    *   `fast-api-fe/services/agent_client.py`
    *   `fast-api-fe/models/openai_schema.py`
    *   `fast-api-fe/static/chat.js`
    *   `fast-api-fe/templates/chat.html`
    *   `setup-scripts/after-customers-agent-deployment-grant.sh`
    *   `setup-scripts/after-agents-deployment-grant.sh`
    *   `tests/integration/test_agent_engine_delegation.py`
    *   `config.example.sh`
    *   `README.md`
    *   `.gemini/GEMINI.md`
*   **Key Dependencies:**
    *   Google ADK 1.x
    *   Vertex AI Agent Engine (Reasoning Engine)
*   **Risks/Unknowns:**
    *   Ensure all environment variable references (e.g., `CUSTOMERS_ENGINE_ID`) are updated consistently to avoid deployment or runtime errors.
    *   Breaking existing integrations if they rely on the "customers" agent name or endpoint.

## 2. 📋 Checklist
- [x] Step 1: Rename directory and core files
  Status: ✅ Implemented. Renamed customers/ to orchestrator/ and updated internal references in pyproject.toml, deploy_agent_engine.py, and app.py.
- [x] Step 2: Refactor Orchestrator agent logic
  Status: ✅ Implemented. Removed mock customer database and lookup tools. Updated agent name, description, and system prompt in orchestrator/agent.py.
- [x] Step 3: Update project configuration and workspace members
  Status: ✅ Implemented. Updated root pyproject.toml and config.example.sh with new project name and environment variable names.
- [x] Step 4: Update Frontend (FastAPI) references
  Status: ✅ Implemented. Updated agent_client.py, chat.py, main.py, openai_schema.py, chat.js, and chat.html to use 'orchestrator' references and model names.
- [x] Step 5: Update setup scripts and IAM grants
  Status: ✅ Implemented. Renamed after-customers-agent-deployment-grant.sh to after-orchestrator-agent-deployment-grant.sh and updated variable names in both grant scripts.
- [x] Step 6: Update documentation and tests
  Status: ✅ Implemented. Updated README.md, GEMINI.md, and test_agent_engine_delegation.py to reflect the orchestrator architecture.
- [x] Verification: Run tests and verify orchestration logic
  Status: ✅ Completed. `uv sync` succeeded, agent instantiation verified, and all references cleaned up.

## 3. 📝 Step-by-Step Implementation Details

### Step 1: Rename directory and core files
*   **Goal:** Move `customers/` to `orchestrator/` and rename internal files/variables.
*   **Action:**
    *   Rename `customers/` to `orchestrator/`.
    *   Rename internal references in `orchestrator/deploy_agent_engine.py` (e.g., package names, environment variable strings).
    *   Update `orchestrator/pyproject.toml` to change the project name to `orchestrator`.
*   **Verification:** `ls orchestrator/` shows the renamed files.

### Step 2: Refactor Orchestrator agent logic
*   **Goal:** Transform the agent from a customer lookup tool to a pure orchestrator.
*   **Action:**
    *   Modify `orchestrator/agent.py`:
        *   Remove `mock_db`.
        *   Remove `get_customer` and `get_all_customers` functions.
        *   Update `create_agent` factory:
            *   Change agent name to `"orchestrator"`.
            *   Update `description` and `instruction` (system prompt) to focus on routing and delegation.
            *   Remove `get_customer` and `get_all_customers` from `tools` list.
        *   Update logging messages (e.g., "Customer Agent" -> "Orchestrator Agent").
*   **Verification:** Code review of `orchestrator/agent.py` ensures no customer logic remains.

### Step 3: Update project configuration and workspace members
*   **Goal:** Update root-level project references.
*   **Action:**
    *   Modify root `pyproject.toml`: Change `"customers"` to `"orchestrator"` in `tool.uv.workspace.members` and `dependencies`.
    *   Modify `config.example.sh`: Change `CUSTOMERS_ENGINE_ID` to `ORCHESTRATOR_ENGINE_ID` and `CUSTOMERS_PRINCIPAL` to `ORCHESTRATOR_PRINCIPAL`.
*   **Verification:** `uv sync` runs successfully.

### Step 4: Update Frontend (FastAPI) references
*   **Goal:** Ensure the web UI and API proxy point to the new orchestrator.
*   **Action:**
    *   Modify `fast-api-fe/services/agent_client.py`: Update `CUSTOMERS_ENGINE_ID` to `ORCHESTRATOR_ENGINE_ID`.
    *   Modify `fast-api-fe/routers/chat.py` and `fast-api-fe/main.py`: Update descriptions and comments.
    *   Modify `fast-api-fe/models/openai_schema.py`: Update default model name to `orchestrator-agent`.
    *   Modify `fast-api-fe/static/chat.js`: Update model name.
    *   Modify `fast-api-fe/templates/chat.html`: Update placeholders and suggestion chips (remove customer-specific ones).
*   **Verification:** Frontend runs and connects to the correct environment variables.

### Step 5: Update setup scripts and IAM grants
*   **Goal:** Ensure deployment and permission scripts are updated.
*   **Action:**
    *   Rename `setup-scripts/after-customers-agent-deployment-grant.sh` to `setup-scripts/after-orchestrator-agent-deployment-grant.sh`.
    *   Update variable names and comments in both `after-agents-deployment-grant.sh` and the newly renamed script.
*   **Verification:** Scripts use the new `ORCHESTRATOR_*` variable names.

### Step 6: Update documentation and tests
*   **Goal:** Keep docs and tests in sync.
*   **Action:**
    *   Update `README.md` and `.gemini/GEMINI.md` to reflect the new architecture.
    *   Update `tests/integration/test_agent_engine_delegation.py` to use `ORCHESTRATOR_ENGINE_ID` and query the orchestrator.
*   **Verification:** Tests pass (or fail with expected auth errors rather than 404s).

## 4. 🧪 Testing Strategy
*   **Unit Tests:** Verify `orchestrator/agent.py` can be instantiated without errors.
*   **Integration Tests:** Run `tests/integration/test_agent_engine_delegation.py` (updated) to verify the orchestrator is reachable.
*   **Manual Verification:**
    1.  Deploy the orchestrator agent using `orchestrator/deploy_agent_engine.py`.
    2.  Start the FastAPI frontend.
    3.  Send a message like "Make a booking" and verify it attempts to call the bookings tool.

## 5. ✅ Success Criteria
*   The `customers/` directory is completely removed/renamed to `orchestrator/`.
*   The orchestrator agent no longer contains logic for customer retrieval.
*   All environment variables and UI labels refer to "Orchestrator" instead of "Customer".
*   The system successfully routes requests from the orchestrator to the bookings subagent.
