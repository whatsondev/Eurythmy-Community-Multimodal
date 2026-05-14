"""
Shared Dependencies

Authentication and other shared dependencies for route handlers.
"""

import firebase_admin
from firebase_admin import auth as firebase_auth
from fastapi import Header, HTTPException

from .database import is_admin


# =============================================================================
# Firebase Admin SDK Initialization
# =============================================================================

# Initialize Firebase Admin SDK (uses default credentials in Cloud Run)
if not firebase_admin._apps:
    firebase_admin.initialize_app()


# =============================================================================
# Admin Authentication
# =============================================================================

async def verify_admin(authorization: str = Header(...)) -> str:
    """
    Verify Firebase ID token and check if user is an admin.

    Admin users must be added to the 'admins' Firestore collection.
    Document ID should be the user's email address.

    Returns:
        The admin's email address

    Raises:
        HTTPException 401: Invalid or missing token
        HTTPException 403: User is not an admin
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    id_token = authorization[7:]  # Remove "Bearer " prefix

    try:
        # Verify the Firebase ID token
        decoded_token = firebase_auth.verify_id_token(id_token)
        email = decoded_token.get("email")

        if not email:
            raise HTTPException(status_code=401, detail="Token does not contain email")

        # Check if user is in the admins collection
        if not await is_admin(email):
            raise HTTPException(
                status_code=403,
                detail=f"User {email} is not an admin"
            )

        return email

    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid ID token")
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="ID token has expired")
    except firebase_auth.RevokedIdTokenError:
        raise HTTPException(status_code=401, detail="ID token has been revoked")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


# =============================================================================
# Google Domain Authentication
# =============================================================================

ALLOWED_DOMAIN = "google.com"


def _extract_email_from_token(token: str) -> str:
    """
    Extract and validate email from a Bearer token.

    Supports two token types:
      1. Firebase ID tokens (from Firebase Auth sign-in)
      2. Google OIDC tokens (from `gcloud auth print-identity-token`)

    Returns:
        The user's email address

    Raises:
        HTTPException: If token is invalid or email is not from google.com
    """
    email = None

    # Try Firebase ID token first
    try:
        decoded = firebase_auth.verify_id_token(token)
        email = decoded.get("email")
    except Exception:
        pass

    # Fall back to Google OIDC token (e.g. from gcloud CLI)
    if not email:
        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests

            decoded = google_id_token.verify_oauth2_token(
                token, google_requests.Request()
            )
            email = decoded.get("email")
        except Exception:
            raise HTTPException(
                status_code=401,
                detail="Invalid token. Provide a Firebase ID token or a Google OIDC token "
                       "(from `gcloud auth print-identity-token`)"
            )

    if not email:
        raise HTTPException(status_code=401, detail="Token does not contain email")

    # Check domain
    if not email.endswith(f"@{ALLOWED_DOMAIN}"):
        raise HTTPException(
            status_code=403,
            detail=f"Access restricted to @{ALLOWED_DOMAIN} users"
        )

    return email


async def verify_google_user(authorization: str = Header(...)) -> str:
    """
    Verify that the caller is a @google.com user.

    Accepts either:
      - Firebase ID token (from web sign-in)
      - Google OIDC token (from `gcloud auth print-identity-token`)

    Does NOT require admin collection membership.

    Returns:
        The user's email address

    Raises:
        HTTPException 401: Invalid or missing token
        HTTPException 403: User is not from google.com domain
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = authorization[7:]  # Remove "Bearer " prefix
    return _extract_email_from_token(token)
