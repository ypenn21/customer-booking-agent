import os
import logging
from fastapi import Request, HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

logger = logging.getLogger(__name__)

# Global request object to cache IAP public keys efficiently across requests
_HTTP_REQUEST = google_requests.Request()

# Load the expected audience from the environment. 
# For IAP, this is usually your backend service's Client ID or Resource Name.
IAP_EXPECTED_AUDIENCE = os.environ.get("IAP_EXPECTED_AUDIENCE")
IAP_ISSUER = "https://cloud.google.com/iap"
IAP_CERTS_URL = "https://www.gstatic.com/iap/verify/public_key"

def validate_token(request: Request) -> str:
    """
    Extracts and cryptographically validates user identity from the IAP JWT header.
    Returns the user's email if valid, or 'web_user' as a fallback if no token is present.
    """
    iap_jwt = request.headers.get("X-Goog-IAP-JWT-Assertion")

    # Fallback for local development or unauthenticated internal traffic
    if not iap_jwt:
        logger.warning("No IAP JWT found in headers. Falling back to 'web_user'.")
        return "web_user"

    # Enforce audience configuration if a token is present
    if not IAP_EXPECTED_AUDIENCE:
        logger.error("IAP_EXPECTED_AUDIENCE environment variable is missing.")
        raise HTTPException(
            status_code=500, 
            detail="Server misconfiguration: Missing IAP audience string."
        )

    try:
        # Cryptographically verify the signature, audience, and expiration
        decoded = id_token.verify_token(
            iap_jwt,
            _HTTP_REQUEST,
            audience=IAP_EXPECTED_AUDIENCE,
            certs_url=IAP_CERTS_URL
        )

        # IAP tokens must have the correct Google Cloud issuer
        if decoded.get("iss") != IAP_ISSUER:
            raise ValueError("Invalid IAP issuer claim.")

        user_email = decoded.get("email")
        if not user_email:
            raise ValueError("IAP token is missing the email claim.")

        logger.info("Authenticated user from IAP: %s", user_email)
        return user_email

    except ValueError as e:
        # Catch validation errors (e.g., bad signature, expired token, wrong audience)
        logger.warning("IAP JWT validation failed: %s", e)
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid IAP token.")
