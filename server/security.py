"""Shared-secret authentication for mutating API endpoints.

Set FABRIC_ATLAS_TOKEN in the environment to require ``Authorization: Bearer <token>``
on every endpoint that changes state (login, scans, user mappings, permission
migrations). Read-only endpoints stay open so the dashboard remains usable as a
viewer. When the variable is unset or empty the API runs in open mode and the app
logs a warning at startup; use that only for local development on 127.0.0.1.
"""

import os
import secrets
from typing import Annotated

from fastapi import Header, HTTPException


TOKEN_ENV_VAR = "FABRIC_ATLAS_TOKEN"


def configured_token() -> str | None:
    """Return the shared secret from the environment, or ``None`` in open mode."""
    token = os.environ.get(TOKEN_ENV_VAR)
    if token is None:
        return None
    return token.strip() or None


async def require_api_token(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Reject mutating requests that do not carry the configured shared secret."""
    expected = configured_token()
    if expected is None:
        return
    provided = ""
    if authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()
    if not provided or not secrets.compare_digest(provided.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid API token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
