# Walkthrough - Passing IAP JWT Claims to Agents

I've implemented the changes to extract and forward all Identity-Aware Proxy (IAP) JWT claims to the ADK agents. This provides the agents with full user context (ID, email, roles, access levels, etc.) for more personalized and secure interactions.

## Changes Made

### 1. FastAPI Frontend
- **Enhanced JWT Extraction**: Updated [fast-api-fe/routers/chat.py](file:///Users/yannipeng/git-projects/customer-booking-agent/fast-api-fe/routers/chat.py) to decode the full IAP JWT and extract all claims, not just the email.
- **Service Layer Propagation**: Modified [query_agent](file:///Users/yannipeng/git-projects/customer-booking-agent/fast-api-fe/services/agent_client.py#64-108) in [fast-api-fe/services/agent_client.py](file:///Users/yannipeng/git-projects/customer-booking-agent/fast-api-fe/services/agent_client.py) to accept these claims and forward them as additional context (via `jwt_claims` keyword argument) to the Vertex AI Agent Engine.

### 2. Customer Agent
- **Instruction Injection**: Updated the `root_agent` instruction in [customers/agent.py](file:///Users/yannipeng/git-projects/customer-booking-agent/customers/agent.py) to include `{jwt_claims}`. ADK automatically injects the claims into the system prompt.
- **A2A Delegation**: Updated the [bookings](file:///Users/yannipeng/git-projects/customer-booking-agent/customers/agent.py#47-79) tool to retrieve the claims from the agent's state and pass them along when calling the Bookings agent via A2A.

### 3. Bookings Agent
- **Instruction Injection**: Similarly updated [bookings/agent.py](file:///Users/yannipeng/git-projects/customer-booking-agent/bookings/agent.py) to include the user context in its instructions.

## Verification Results

### Code Review
- **Syntax**: All modified files follow Python 3.10 syntax and naming conventions.
- **Robustness**: The extraction logic handles missing JWT headers gracefully, falling back to an empty dictionary and "web_user" ID.
- **Dependencies**: Verified that `PyJWT` is already a requirement in the FE. The agents do not need it as they receive the claims as a dictionary.

### Manual Verification Path
1. **Redeploy Agents**: Run `make deploy` to push the updated agents to Vertex AI.
2. **Test with IAP Emulator or Headers**: If testing via `make playground`, you can mock the `X-Goog-IAP-JWT-Assertion` header to verify the claims are reflected in the agent's behavior (e.g., "Tell me my user ID from my token").

## Detail of JWT Claims

Apart from the **email** (the primary identifier used initially), the IAP JWT token exposes several other useful fields:

- **`sub`**: A unique, stable identifier for the user (Subject).
- **`google`**:
  - **`access_levels`**: A list of Access Context Manager access levels currently satisfied by the request.
- **`gcip`**: (Only if using Google Cloud Identity Platform/Firebase)
  - **`name`**: Full name of the user.
  - **`picture`**: URL to the user's profile picture.
  - **`firebase`**:
    - **`identities`**: Dictionary of identity provider info.
    - **`sign_in_attributes`**: Custom attributes from the identity provider (e.g., `role`, `tier`, `department`).
- **Standard Claims**:
  - **`aud`**: Audience (the target backend resource).
  - **`iss`**: Issuer (`https://cloud.google.com/iap`).
  - **`exp` / `iat`**: Expiration and issuance timestamps.

These additional claims can be used by the customer agent to refine its personality, check permissions, or provide more tailored information.

## Files Modified
- [chat.py](file:///Users/yannipeng/git-projects/customer-booking-agent/fast-api-fe/routers/chat.py)
- [agent_client.py](file:///Users/yannipeng/git-projects/customer-booking-agent/fast-api-fe/services/agent_client.py)
- [customers/agent.py](file:///Users/yannipeng/git-projects/customer-booking-agent/customers/agent.py)
- [bookings/agent.py](file:///Users/yannipeng/git-projects/customer-booking-agent/bookings/agent.py)
