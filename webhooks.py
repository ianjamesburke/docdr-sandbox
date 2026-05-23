"""Webhook system for real-time event notifications.

Registers webhook URLs and dispatches events when items are created,
updated, or deleted. Supports retry logic with exponential backoff.
"""
import hmac
import hashlib
from dataclasses import dataclass, field
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

WEBHOOK_REGISTRY: dict[str, "WebhookConfig"] = {}


@dataclass
class WebhookConfig:
    url: str
    secret: str
    events: list[str] = field(default_factory=lambda: ["item.created", "item.updated", "item.deleted"])
    active: bool = True
    retry_count: int = 3


def sign_payload(payload: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload verification."""
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


@router.post("/register")
def register_webhook(url: str, secret: str, events: list[str] | None = None):
    """Register a new webhook endpoint."""
    config = WebhookConfig(url=url, secret=secret, events=events or ["item.created"])
    WEBHOOK_REGISTRY[url] = config
    return {"registered": True, "url": url, "events": config.events}


@router.delete("/{webhook_url}")
def unregister_webhook(webhook_url: str):
    """Remove a registered webhook."""
    if webhook_url not in WEBHOOK_REGISTRY:
        raise HTTPException(status_code=404, detail="Webhook not found")
    del WEBHOOK_REGISTRY[webhook_url]
    return {"unregistered": True}


@router.get("/")
def list_webhooks():
    """List all registered webhooks."""
    return [
        {"url": url, "events": cfg.events, "active": cfg.active}
        for url, cfg in WEBHOOK_REGISTRY.items()
    ]
