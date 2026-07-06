"""Shared FastAPI dependencies."""

from fastapi import Depends

from app.core.security.auth import verify_token

# Re-export for convenience
auth_required = Depends(verify_token)
