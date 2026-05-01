import os
import logging
from fastapi import HTTPException
from google.oauth2 import id_token
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

IAP_ISSUER = "https://cloud.google.com/iap"
IAP_CERTS_URL = "https://www.gstatic.com/iap/verify/public_key"

def validate_token(token: str, audience: str) -> dict:
    """Validates a JWT token and its audience claim, returning the decoded payload."""
    try:
        # Instantiate the Request object required by google-auth
        request = Request()
        
        # Cryptographically verify the signature, audience, and expiration
        decoded = id_token.verify_token(
            token,
            request,
            audience=audience,
            certs_url=IAP_CERTS_URL
        )

        # IAP tokens must have the correct Google Cloud issuer
        if decoded.get("iss") != IAP_ISSUER:
            raise ValueError("Invalid IAP issuer claim.")

        # Ensure the token has some form of user identification
        if not decoded.get("email") and not decoded.get("sub"):
            raise ValueError("IAP token is missing email and subject claims.")

        logger.info("Successfully validated IAP token. User email: %s", decoded.get("email", "unknown"))
        
        # Return the full decoded dictionary so agent.py can extract 'sub' or 'gcip' claims
        return decoded

    except ValueError as e:
        # Catch validation errors (e.g., bad signature, expired token, wrong audience)
        logger.warning("IAP JWT validation failed: %s", e)
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid IAP token.")

