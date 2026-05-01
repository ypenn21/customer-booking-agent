# Feature Implementation Plan: Story 3.1: Extract IAP JWT

## 🔍 Analysis & Context
*   **Objective:** Secure the FastAPI backend by extracting and validating the `x-goog-iap-jwt-assertion` header to authenticate users and establish identity context.
*   **Affected Files:**
    *   `fast-api-fe/requirements.txt`
    *   `fast-api-fe/models/user.py` (New)
    *   `fast-api-fe/services/auth.py` (New)
    *   `fast-api-fe/routers/chat.py`
    *   `tests/unit/test_auth.py` (New)
*   **Key Dependencies:** `PyJWT` (already present) for token decoding/validation, `httpx` (to be added) for async public key fetching.
*   **Risks/Edge Cases:**
    *   **Public Key Rotation:** Google rotates IAP public keys frequently; the system must cache keys but elegantly refresh them on cache miss for a new `kid`.
    *   **Audience Validation:** The `aud` claim must exactly match the deployed backend service ID string to prevent cross-service token replay.
    *   **Local Development:** Without IAP in front of localhost, the app needs a secure mock bypass controlled exclusively by environment variables.
    *   **Missing Headers:** Requests without the token must immediately fail with HTTP 401.

## 📋 Micro-Step Checklist
- [ ] Phase 1: Data Models & Environment Setup
  - [ ] Step 1.A: Define the User Domain Model
  - [ ] Step 1.B: Add HTTP Client Dependency
- [ ] Phase 2: Core Authentication Logic
  - [ ] Step 2.A: Implement Public Key Fetching & Caching
  - [ ] Step 2.B: Implement IAP JWT Decode & Verification
  - [ ] Step 2.C: Create FastAPI Auth Dependency
- [ ] Phase 3: Integration
  - [ ] Step 3.A: Secure Chat Router Endpoints
- [ ] Phase 4: Testing & Verification
  - [ ] Step 4.A: Unit Test JWT Verification Logic
  - [ ] Step 4.B: Integration Verification

## 📝 Step-by-Step Implementation Details

### Prerequisites
None beyond an active Python environment managed by `uv`. 

#### Phase 1: Data Models & Environment Setup
1.  **Step 1.A (The User Domain Model):** Create a robust schema to represent the authenticated identity.
    *   *Target File:* `fast-api-fe/models/user.py`
    *   *Exact Change:* Create a Pydantic `BaseModel` named `User` containing `sub` (string) and `email` (string). Add descriptive `Field` metadata for swagger documentation.
2.  **Step 1.B (Add HTTP Client Dependency):** Add `httpx` for reliable async key fetching.
    *   *Target File:* `fast-api-fe/requirements.txt`
    *   *Exact Change:* Append `httpx>=0.27.0` to the file.

#### Phase 2: Core Authentication Logic
1.  **Step 2.A (Implement Public Key Fetching):** Fetch and cache Google's public keys.
    *   *Target File:* `fast-api-fe/services/auth.py`
    *   *Exact Change:* Implement `async def get_iap_public_keys(force_refresh: bool = False) -> dict[str, str]:`
        *   Maintain a module-level dictionary `_public_keys_cache`.
        *   If the cache is empty or `force_refresh` is True, use `httpx.AsyncClient` to `GET https://www.gstatic.com/iap/verify/public_key`.
        *   Parse the JSON response and update the cache. Return the dictionary.
2.  **Step 2.B (Implement IAP JWT Decode & Verification):** The cryptographic validation.
    *   *Target File:* `fast-api-fe/services/auth.py`
    *   *Exact Change:* Implement `async def verify_iap_jwt(iap_jwt: str) -> User:`
        *   Use `jwt.get_unverified_header(iap_jwt)` to extract the `kid` (Key ID).
        *   Look up the `kid` in `await get_iap_public_keys()`. If missing, call with `force_refresh=True`.
        *   If the `kid` is still missing, raise `HTTPException(status_code=401, detail="Public key not found")`.
        *   Decode using `jwt.decode(...)` passing the `key`, `algorithms=["ES256"]`, `issuer="https://cloud.google.com/iap"`, and `audience=os.getenv("IAP_EXPECTED_AUDIENCE")`.
        *   Catch `jwt.ExpiredSignatureError` and `jwt.InvalidTokenError`, raising appropriate 401 exceptions.
        *   Map the decoded payload to a `User` instance and return it.
3.  **Step 2.C (Create FastAPI Auth Dependency):** Tie the verifier to FastAPI's request lifecycle.
    *   *Target File:* `fast-api-fe/services/auth.py`
    *   *Exact Change:* Implement `async def get_current_user(request: Request) -> User:`
        *   Extract the header: `iap_jwt = request.headers.get("x-goog-iap-jwt-assertion")`.
        *   *Local Dev Fallback:* If `iap_jwt` is None and `os.getenv("ENVIRONMENT") == "development"`, return a mock `User(sub="dev-sub", email="dev@example.com")`.
        *   If `iap_jwt` is None, raise `HTTPException(status_code=401, detail="Missing X-Goog-IAP-JWT-Assertion")`.
        *   Return `await verify_iap_jwt(iap_jwt)`.

#### Phase 3: Integration
1.  **Step 3.A (Secure Chat Router Endpoints):** Enforce authentication on all API routes.
    *   *Target File:* `fast-api-fe/routers/chat.py`
    *   *Exact Change:* 
        *   Remove the insecure `_extract_user_id` function.
        *   Import `Depends` from `fastapi` and `get_current_user`, `User` from `..services.auth`.
        *   Update `chat_completions` signature: `async def chat_completions(req: ChatCompletionRequest, current_user: User = Depends(get_current_user)) -> ChatCompletionResponse:`
        *   Replace `user_id = _extract_user_id(request)` with `user_id = current_user.email` (or `.sub` depending on downstream requirement).
        *   Apply the same dependency injection to `list_sessions` and `get_session_messages`.

#### Phase 4: Testing & Verification
1.  **Step 4.A (The Unit Test Harness):** Define verification requirements for token handling.
    *   *Target File:* `tests/unit/test_auth.py`
    *   *Test Cases to Write:*
        *   Write a test mocking `httpx.AsyncClient` to return dummy public keys.
        *   Test a valid signed JWT returns a `User` object.
        *   Test an expired JWT raises `HTTPException` with 401.
        *   Test an invalid signature raises `HTTPException` with 401.
        *   Test a JWT missing the `kid` header raises `HTTPException` with 401.
2.  **Step 4.B (The Verification):** Verify the integration locally.
    *   *Action:* Run `ENVIRONMENT=production uvicorn fast-api-fe.main:app --reload`.
    *   *Success:* Running `curl -X POST http://localhost:8000/v1/chat/completions` without the header returns `401 Unauthorized`.

### 🧪 Global Testing Strategy
*   **Unit Tests:** Focus on the cryptographic validation (`verify_iap_jwt`) using a generated ES256 key pair to mock Google's keys and sign test tokens.
*   **Integration Tests:** Start the FastAPI application via `TestClient` and assert that protected routes reject unauthorized requests but accept requests bearing a valid (or mocked for development) `x-goog-iap-jwt-assertion`.

## 🎯 Success Criteria
*   The `x-goog-iap-jwt-assertion` header is robustly parsed and cryptographically validated on every request to `/v1/*`.
*   Google IAP public keys are automatically fetched and intelligently cached.
*   Invalid, expired, or missing tokens correctly yield HTTP 401 errors.
*   The authenticated user's identity (`sub` and `email`) is safely injected into FastAPI route handlers via standard dependency injection.