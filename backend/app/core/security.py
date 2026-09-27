from typing import Optional
from fastapi import Header, HTTPException, status
from app.core.config import settings


async def verify_api_key(x_api_key: Optional[str] = Header(default=None)):
    """
    Guards incident-mutating endpoints (POST/PATCH).

    If INCIDENT_API_KEY is unset, auth is disabled — fine for local dev.
    Set it before exposing the API via ngrok/publicly (see docs/BUILD_NOTES.md).
    """
    if not settings.INCIDENT_API_KEY:
        return
    if x_api_key != settings.INCIDENT_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-API-Key",
        )
