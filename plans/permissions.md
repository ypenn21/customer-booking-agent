# User Permissions Implementation Plan

This plan introduces a formal `UserContext` structure and a role mapping system to allow programmatic permission checks in the FastAPI frontend and behavioral adaptations in the backend agents.

## Proposed Changes

### [Component] FastAPI Backend

#### [NEW] [user.py](file:///Users/yannipeng/git-projects/customer-booking-agent/fast-api-fe/models/user.py)
Define a `UserContext` Pydantic model and a `Role` enum.
- `UserContext`: contains [user_id](file:///Users/yannipeng/git-projects/customer-booking-agent/fast-api-fe/routers/chat.py#27-41) (sub), `email`, `domain` (hd), and a list of `roles`.

#### [NEW] [auth.py](file:///Users/yannipeng/git-projects/customer-booking-agent/fast-api-fe/services/auth.py)
Provide a FastAPI dependency `get_user_context`.
- Decodes the `X-Goog-IAP-JWT-Assertion` header.
- Implements a `map_roles(claims: dict)` function to assign roles based on `email` or `hd`.
- Returns a `UserContext` object.

#### [MODIFY] [chat.py](file:///Users/yannipeng/git-projects/customer-booking-agent/fast-api-fe/routers/chat.py)
- Use `get_user_context` as a dependency in all routes.
- Replace [_extract_user_id](file:///Users/yannipeng/git-projects/customer-booking-agent/fast-api-fe/routers/chat.py#27-41) internal function.
- Pass the full `UserContext` to the `agent_client`.

#### [MODIFY] [agent_client.py](file:///Users/yannipeng/git-projects/customer-booking-agent/fast-api-fe/services/agent_client.py)
- Update [query_agent](file:///Users/yannipeng/git-projects/customer-booking-agent/fast-api-fe/services/agent_client.py#50-89) to accept `user_context: UserContext`.
- Forward the roles/claims as additional context to the Agent Engine (typically via the initial message or as a metadata field if the SDK supports it).

### [Component] Customers Agent

#### [MODIFY] [agent.py](file:///Users/yannipeng/git-projects/customer-booking-agent/customers/agent.py)
- Update the `root_agent` instructions to use `{roles}` if passed.
- Example: "You are a customer agent. The current user has roles: {roles}. Only admins can use the [get_all_customers](file:///Users/yannipeng/git-projects/customer-booking-agent/customers/agent.py#130-133) tool."

## Verification Plan

### Automated Tests
- **Unit Test**: Test the `map_roles` logic with various mock JWT payloads.
- **Integration Test**: Update [tests/integration/test_agent_sessions.py](file:///Users/yannipeng/git-projects/customer-booking-agent/tests/integration/test_agent_sessions.py) to mock the IAP JWT header with different emails to verify role-based behavior.
  - Run with: `uv run pytest tests/integration/test_agent_sessions.py`

### Manual Verification
- Log in with different accounts (if possible in the environment) and verify that the "Decoded IAP JWT" log shows the expected claims.
- Verify that the agent responds differently based on the assigned roles (e.g., "I'm sorry, you don't have permission to list all customers").
