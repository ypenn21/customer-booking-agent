# USER_STORIES.md

### Section 1: Feature Overview
- **Feature Name:** Secure Microsoft-Authenticated Multi-Agent Booking System
- **Target Persona:** Corporate Traveler
- **Value Proposition:** Enable corporate travelers to securely manage their travel bookings by authenticating via Microsoft and delegating actions to a multi-agent system. This ensures seamless identity integration and secure management of access tokens via Google Cloud Identity Platform (GCIP) and Secret Manager.

### Section 2: User Stories

#### Story 1: Microsoft Authentication via IAP/GCIP
- **Description:** As a corporate traveler, I want to authenticate using my existing Microsoft corporate account, so that I can securely access the booking agent without needing a separate set of credentials.
- **INVEST Analysis:**
  - **Independent:** This story covers the initial login flow and can be tested before any downstream agent features are built.
  - **Negotiable:** The specific Microsoft OIDC configuration details are negotiable based on IT policies.
  - **Valuable:** Essential for security, compliance, and user experience in a corporate environment.
  - **Estimable:** Configuring IAP and GCIP for Microsoft authentication is a well-understood task.
  - **Small:** Focused on the authentication handshake and redirection.
  - **Testable:** Can verify the redirection and successful receipt of a valid IAP-signed JWT.
- **Acceptance Criteria (Gherkin Format):**
  ```gherkin
  Scenario: Successful login with Microsoft Account
    Given the traveler navigates to the booking agent website
    When the traveler clicks the login button
    Then the traveler is redirected to the Microsoft sign-in page
    And after providing valid corporate credentials, the traveler is redirected back to the booking agent dashboard.

  Scenario: Failed Microsoft Authentication
    Given the traveler is on the Microsoft sign-in page
    When the traveler enters invalid credentials or cancels the login
    Then Microsoft displays an authentication error
    And the traveler is not granted access to the booking agent application.
  ```

#### Story 2: Secure Token Storage via Identity Platform Blocking Function
- **Description:** As a system administrator, I want to use a GCIP "before-sign-in" blocking function to capture the user's Microsoft access tokens and store them securely in Secret Manager, so that agents can perform delegated actions on the user's behalf.
- **INVEST Analysis:**
  - **Independent:** Relies on Story 1 for the auth response but focuses on the backend token capture logic.
  - **Negotiable:** The choice of Secret Manager as the vault is preferred, but the implementation details are negotiable.
  - **Valuable:** Crucial for the "acting on behalf of" functionality required for travel bookings.
  - **Estimable:** Writing a Cloud Function for GCIP triggers is a standard task.
  - **Small:** Single logical unit of work within the sign-in pipeline.
  - **Testable:** Verify that Microsoft tokens are saved in Secret Manager and the `emailVerified` flag is set to true for the user.
- **Acceptance Criteria (Gherkin Format):**
  ```gherkin
  Scenario: Tokens are securely stored during the sign-in process
    Given a traveler successfully authenticates via Microsoft
    When the "before-sign-in" blocking function is triggered by GCIP
    Then the Microsoft access tokens are extracted from the identity provider response
    And the tokens are saved in Secret Manager using the traveler's unique ID (sub) as an index
    And the user's profile is updated with "emailVerified: true".

  Scenario: Token storage failure during sign-in
    Given a traveler authenticates via Microsoft
    When the blocking function fails to write to Secret Manager or profile update fails
    Then the sign-in process is interrupted
    And an error is logged with the reason for failure.
  ```

#### Story 3: User Identity Extraction and Context Propagation
- **Description:** As a system, I want to extract the traveler's identity (email and sub) from the IAP-signed JWT header in the FastAPI frontend and pass it to the orchestrator agent, so that the agent can maintain the correct user context throughout the conversation.
- **INVEST Analysis:**
  - **Independent:** Can be implemented and tested using mock IAP headers in the frontend.
  - **Negotiable:** The method of extraction (header parsing) is standard, but the specific middleware design can vary.
  - **Valuable:** Necessary for mapping the request to the correct user for personalized responses.
  - **Estimable:** Standard header parsing and context management task.
  - **Small:** Very small scope within the web application layer.
  - **Testable:** Verify that the "sub" and "email" are available in the backend request logs and passed to the Customers agent.
- **Acceptance Criteria (Gherkin Format):**
  ```gherkin
  Scenario: Successfully extract and propagate user identity from IAP JWT
    Given a request arrives at the FastAPI frontend with a valid "x-goog-iap-jwt-assertion" header
    When the frontend parses and validates the JWT
    Then the user's unique identity (sub) should be extracted
    And passed along with the request to the Customers orchestrator agent.

  Scenario: Request with missing IAP JWT header
    Given a request arrives at the FastAPI frontend without the "x-goog-iap-jwt-assertion" header
    When the identity extraction logic is executed
    Then the request should be rejected with a 401 Unauthorized error.
  ```

#### Story 4: Delegated Action Execution via Bookings Agent
- **Description:** As a traveler, I want the booking agent to use my stored Microsoft token to perform travel actions on my behalf, so that my bookings are automatically registered in my corporate account without manual intervention.
- **INVEST Analysis:**
  - **Independent:** Relies on the availability of tokens in Secret Manager but focuses on the agent's tool execution logic.
  - **Negotiable:** The specific Microsoft API endpoints and the nature of the action (e.g., calendar invite, flight booking) are flexible.
  - **Valuable:** This is the core value proposition of the multi-agent system.
  - **Estimable:** Implementing the tool logic and Secret Manager retrieval is moderately complex but estimable.
  - **Small:** Focused on the "Bookings" agent's ability to act as a delegate.
  - **Testable:** Verify that the Bookings agent retrieves the correct token from Secret Manager and the downstream Microsoft API call succeeds.
- **Acceptance Criteria (Gherkin Format):**
  ```gherkin
  Scenario: Agent successfully performs a booking action using stored token
    Given the Customers agent detects a booking intent
    And the Bookings agent tool is invoked with the traveler's unique ID (sub)
    When the Bookings agent retrieves the traveler's token from Secret Manager
    And executes a call to the Microsoft API (or Mock) using that token
    Then the action should succeed and the agent should return a confirmation message to the traveler.

  Scenario: Expired or missing token during delegated action
    Given the Bookings agent attempts to perform a delegated action
    When the required token is missing from Secret Manager or has expired
    Then the agent should return a meaningful error message to the traveler
    And the traveler should be prompted to re-authenticate to refresh their tokens.
  ```

### Section 3: Traceability Matrix

| Input Requirement (from future_state.md) | User Story ID |
| :--- | :--- |
| Login Request + Redirect + Microsoft Auth | Story 1 |
| Blocking Function Trigger + Save Tokens | Story 2 |
| Set emailVerified: true | Story 2 |
| Grant Access + IAP JWT | Story 1, Story 3 |
| Extract User Identity (sub/email) from IAP JWT | Story 3 |
| Detect Booking Intent (Customers Agent) | Story 4 |
| Call Tool (Bookings Agent) | Story 4 |
| Retrieve Tokens from Secret Manager using sub | Story 4 |
| Action with Tokens (Microsoft API / Mock) | Story 4 |
