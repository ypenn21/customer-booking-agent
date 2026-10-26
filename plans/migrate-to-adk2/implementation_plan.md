# Implementation Plan: ADK 1.x to 2.0 Migration

This plan outlines the steps to migrate the `agent-security-patterns` codebase from ADK 1.x (Agent Engine) to ADK 2.0 (Workflows).

## Goals
- Transition from hierarchical delegation (AgentTool pattern) to a graph-based Workflow.
- Improve performance by extracting deterministic logic into function nodes.
- Maintain full compatibility with existing security patterns (IAP, JWT validation).

## Proposed Changes

### [NEW] [workflow.py](file:///Users/yannipeng/git-projects/agent-security-patterns/app/workflow.py)
Create a centralized workflow definition that manages both the `customers` and `bookings` personas.

- **Start Node**: Validates identity and context.
- **Router Node**: Directs traffic based on intent (booking vs. lookup).
- **Customers Node**: Handles customer data retrieval.
- **Bookings Node**: Handles reservation and calendar logic.

### [MODIFY] [agent.py](file:///Users/yannipeng/git-projects/agent-security-patterns/app/agent.py)
Update the main agent entry point to initialize the ADK 2.0 Workflow instead of the legacy `Agent` class.

### [NEW] [utils.py](file:///Users/yannipeng/git-projects/agent-security-patterns/app/utils.py)
Extract shared utilities like `get_secret` and `validate_token` to avoid duplication across nodes.

## Phase 1: Foundation
1.  **Environment Setup**: Ensure ADK 2.0 is installed in the `venv`.
2.  **Shared Utils**: Create `app/utils.py` and move common security/utility functions there.
3.  **Graph Scaffolding**: Initialize the `Workflow` object in `app/workflow.py`.

## Phase 2: Node Implementation
1.  **Auth Node**: Implement the `auth_gate` function node to handle JWT validation.
2.  **Customer Node**: Port the `get_customer` tool logic to a dedicated node.
3.  **Booking Node**: Port the `create_calendar_invite` and `make_booking` tools.
4.  **Router**: Implement a simple LLM-based or regex-based router to replace the `bookings` delegation tool.

## Phase 3: Integration & Testing
1.  **Runner Update**: Update the `main.py` or `Runner` configuration to execute the workflow.
2.  **Functional Testing**: Run the test suite (greetings, customer lookups, bookings) to ensure parity.
3.  **Latency Benchmark**: Compare the performance of the new workflow vs. the legacy delegation.

## Verification Plan

### Automated Tests
- `pytest tests/integration/test_agent.py` (ensure existing tests still pass).
- New unit tests for each function node in the workflow.

### Manual Verification
- Test complex flows: "Look up Alice and then book a meeting for her tomorrow at 2 PM".
- Verify that `create_calendar_invite` still successfully calls the Microsoft Graph API.
- Check logs for the new "deterministic node execution" traces.
