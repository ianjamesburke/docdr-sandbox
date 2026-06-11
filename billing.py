"""Billing and invoice endpoints for sandbox workspace accounts."""
from fastapi import APIRouter, Depends, HTTPException

from auth import require_admin, require_workspace_member

router = APIRouter(prefix="/workspaces/{workspace_id}/billing", tags=["billing"])

PLANS: dict[str, dict] = {
    "free": {"id": "free", "monthly_cents": 0, "included_items": 100},
    "team": {"id": "team", "monthly_cents": 2900, "included_items": 5_000},
    "enterprise": {"id": "enterprise", "monthly_cents": 19900, "included_items": 100_000},
}
SUBSCRIPTIONS: dict[int, dict] = {}
INVOICES: dict[int, list[dict]] = {}
_next_invoice_id = 1


@router.get("/plans")
def list_billing_plans(_key: dict = Depends(require_workspace_member)):
    """Return available billing plans for a workspace."""
    return list(PLANS.values())


@router.get("/subscription")
def get_subscription(workspace_id: int, _key: dict = Depends(require_workspace_member)):
    """Return the active subscription for a workspace."""
    return SUBSCRIPTIONS.get(
        workspace_id,
        {
            "workspace_id": workspace_id,
            "plan_id": "free",
            "status": "active",
            "seat_count": 1,
        },
    )


@router.put("/subscription")
def update_subscription(
    workspace_id: int,
    plan_id: str,
    seat_count: int = 1,
    _admin: dict = Depends(require_admin),
):
    """Update the workspace subscription. Requires an admin key."""
    if plan_id not in PLANS:
        raise HTTPException(status_code=400, detail="Unsupported billing plan")
    if seat_count < 1:
        raise HTTPException(status_code=400, detail="seat_count must be at least 1")
    subscription = {
        "workspace_id": workspace_id,
        "plan_id": plan_id,
        "status": "active",
        "seat_count": seat_count,
    }
    SUBSCRIPTIONS[workspace_id] = subscription
    return subscription


@router.post("/invoices", status_code=201)
def create_invoice(
    workspace_id: int,
    description: str,
    amount_cents: int,
    _admin: dict = Depends(require_admin),
):
    """Create a draft invoice for a workspace. Requires an admin key."""
    global _next_invoice_id
    if amount_cents <= 0:
        raise HTTPException(status_code=400, detail="amount_cents must be positive")
    invoice = {
        "id": _next_invoice_id,
        "workspace_id": workspace_id,
        "description": description,
        "amount_cents": amount_cents,
        "status": "draft",
    }
    INVOICES.setdefault(workspace_id, []).append(invoice)
    _next_invoice_id += 1
    return invoice


@router.get("/invoices")
def list_invoices(workspace_id: int, _key: dict = Depends(require_workspace_member)):
    """List invoices for a workspace."""
    return INVOICES.get(workspace_id, [])
