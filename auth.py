"""API key authentication middleware for Sandbox API."""
import secrets
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEYS: dict[str, dict] = {}
api_key_header = APIKeyHeader(name="X-API-Key")


def generate_api_key(owner: str, role: str = "member", workspace_id: int | None = None) -> str:
    """Generate a new API key for the given owner."""
    key = f"sk_{secrets.token_hex(24)}"
    API_KEYS[key] = {
        "owner": owner,
        "role": role,
        "workspace_id": workspace_id,
        "created": True,
    }
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


def require_workspace_member(workspace_id: int, key_data: dict = Depends(require_api_key)) -> dict:
    """Require an API key scoped to the requested workspace or an admin key."""
    if key_data.get("role") == "admin":
        return key_data
    if key_data.get("workspace_id") != workspace_id:
        raise HTTPException(status_code=403, detail="Workspace access required")
    return key_data
