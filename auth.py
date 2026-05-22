"""API key authentication middleware for Sandbox API."""
import secrets
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEYS: dict[str, dict] = {}
api_key_header = APIKeyHeader(name="X-API-Key")


def generate_api_key(owner: str) -> str:
    """Generate a new API key for the given owner."""
    key = f"sk_{secrets.token_hex(24)}"
    API_KEYS[key] = {"owner": owner, "created": True}
    return key


def require_api_key(key: str = Security(api_key_header)) -> dict:
    """Validate the API key from X-API-Key header. Returns key metadata."""
    if key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return API_KEYS[key]


def require_admin(key_data: dict = Depends(require_api_key)) -> dict:
    """Require admin-level API key."""
    if key_data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return key_data
