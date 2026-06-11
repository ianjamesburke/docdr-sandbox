"""Simple FastAPI app for testing DocDr documentation generation."""
from fastapi import Depends, FastAPI, HTTPException, Request
from auth import generate_api_key, require_admin, require_api_key, require_workspace_member
from billing import router as billing_router
from cache import LRUCache
from metrics import MetricsCollector, MetricsMiddleware
from middleware import RequestLoggingMiddleware
from rate_limit import RateLimiter
from webhooks import router as webhook_router

app = FastAPI(title="Sandbox API", version="0.9.0")
item_cache = LRUCache(max_size=256)
rate_limiter = RateLimiter(max_requests=60, window_seconds=60)
metrics_collector = MetricsCollector()
app.add_middleware(MetricsMiddleware, collector=metrics_collector)
app.add_middleware(RequestLoggingMiddleware)
app.include_router(billing_router)
app.include_router(webhook_router)

ITEMS: dict[int, dict] = {}
TAGS: dict[int, set[str]] = {}
WORKSPACES: dict[int, dict] = {}
WORKSPACE_EVENTS: dict[int, list[dict]] = {}
NOTIFICATION_SUBSCRIPTIONS: dict[int, list[dict]] = {}
AUDIT_REPORTS: dict[int, list[dict]] = {}
_next_id = 1
_next_workspace_id = 1
_next_subscription_id = 1
_next_audit_report_id = 1


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/rate-limit")
def rate_limit_status(request: Request):
    """Check current rate limit usage for the calling client."""
    return rate_limiter.get_usage(request)


@app.get("/metrics")
def get_metrics(_key: dict = Depends(require_api_key)):
    """Return per-endpoint request metrics. Requires API key."""
    return metrics_collector.summary()


@app.post("/metrics/reset", status_code=204)
def reset_metrics(_key: dict = Depends(require_api_key)):
    """Clear all collected metrics. Requires API key."""
    metrics_collector.reset()


@app.post("/keys", status_code=201)
def create_api_key(
    owner: str,
    role: str = "member",
    workspace_id: int | None = None,
    _admin: dict = Depends(require_admin),
):
    """Create a workspace-scoped API key. Requires an admin key."""
    if role not in {"admin", "member"}:
        raise HTTPException(status_code=400, detail="Unsupported role")
    if role == "member" and workspace_id not in WORKSPACES:
        raise HTTPException(status_code=404, detail="Workspace not found")
    key = generate_api_key(owner=owner, role=role, workspace_id=workspace_id)
    return {"key": key, "owner": owner, "role": role, "workspace_id": workspace_id}


@app.get("/workspaces")
def list_workspaces(_admin: dict = Depends(require_admin)):
    """List all workspaces. Requires an admin key."""
    return list(WORKSPACES.values())


@app.post("/workspaces", status_code=201)
def create_workspace(name: str, slug: str, _admin: dict = Depends(require_admin)):
    """Create an isolated workspace. Requires an admin key."""
    global _next_workspace_id
    if any(workspace["slug"] == slug for workspace in WORKSPACES.values()):
        raise HTTPException(status_code=409, detail="Workspace slug already exists")
    workspace = {"id": _next_workspace_id, "name": name, "slug": slug, "members": []}
    WORKSPACES[_next_workspace_id] = workspace
    _next_workspace_id += 1
    return workspace


@app.get("/workspaces/{workspace_id}")
def get_workspace(workspace_id: int, _key: dict = Depends(require_workspace_member)):
    """Return workspace metadata for authorized callers."""
    if workspace_id not in WORKSPACES:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WORKSPACES[workspace_id]


@app.post("/workspaces/{workspace_id}/members", status_code=201)
def add_workspace_member(
    workspace_id: int,
    owner: str,
    _admin: dict = Depends(require_admin),
):
    """Add a member owner to a workspace. Requires an admin key."""
    if workspace_id not in WORKSPACES:
        raise HTTPException(status_code=404, detail="Workspace not found")
    members = WORKSPACES[workspace_id]["members"]
    if owner not in members:
        members.append(owner)
        WORKSPACE_EVENTS.setdefault(workspace_id, []).append({
            "type": "member_added",
            "owner": owner,
            "notification_count": len([
                subscription
                for subscription in NOTIFICATION_SUBSCRIPTIONS.get(workspace_id, [])
                if subscription["status"] == "active"
            ]),
        })
    return WORKSPACES[workspace_id]


@app.get("/workspaces/{workspace_id}/events")
def list_workspace_events(workspace_id: int, _key: dict = Depends(require_workspace_member)):
    """Return recent workspace activity events."""
    if workspace_id not in WORKSPACES:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WORKSPACE_EVENTS.get(workspace_id, [])


@app.get("/workspaces/{workspace_id}/notifications")
def list_notification_subscriptions(
    workspace_id: int,
    _key: dict = Depends(require_workspace_member),
):
    """List notification subscriptions for a workspace."""
    if workspace_id not in WORKSPACES:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return NOTIFICATION_SUBSCRIPTIONS.get(workspace_id, [])


@app.post("/workspaces/{workspace_id}/notifications", status_code=201)
def create_notification_subscription(
    workspace_id: int,
    target_url: str,
    event_type: str = "workspace.event",
    _admin: dict = Depends(require_admin),
):
    """Create an outbound notification subscription for workspace events."""
    global _next_subscription_id
    if workspace_id not in WORKSPACES:
        raise HTTPException(status_code=404, detail="Workspace not found")
    subscription = {
        "id": _next_subscription_id,
        "workspace_id": workspace_id,
        "target_url": target_url,
        "event_type": event_type,
        "status": "active",
    }
    NOTIFICATION_SUBSCRIPTIONS.setdefault(workspace_id, []).append(subscription)
    _next_subscription_id += 1
    return subscription


@app.delete("/workspaces/{workspace_id}/notifications/{subscription_id}", status_code=204)
def delete_notification_subscription(
    workspace_id: int,
    subscription_id: int,
    _admin: dict = Depends(require_admin),
):
    """Disable a workspace notification subscription."""
    subscriptions = NOTIFICATION_SUBSCRIPTIONS.get(workspace_id, [])
    for subscription in subscriptions:
        if subscription["id"] == subscription_id:
            subscription["status"] = "disabled"
            return
    raise HTTPException(status_code=404, detail="Notification subscription not found")


@app.get("/items")
def list_items(workspace_id: int | None = None, tag: str | None = None):
    items = list(ITEMS.values())
    if workspace_id is not None:
        items = [item for item in items if item.get("workspace_id") == workspace_id]
    if tag:
        return [item for item in items if tag in TAGS.get(item["id"], set())]
    return items


@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    return {**ITEMS[item_id], "tags": list(TAGS.get(item_id, set()))}


@app.post("/items", status_code=201)
def create_item(
    request: Request,
    name: str,
    workspace_id: int,
    description: str = "",
    tags: str = "",
    _key: dict = Depends(require_workspace_member),
):
    global _next_id
    rate_limiter.check(request)
    if workspace_id not in WORKSPACES:
        raise HTTPException(status_code=404, detail="Workspace not found")
    item = {
        "id": _next_id,
        "workspace_id": workspace_id,
        "name": name,
        "description": description,
    }
    ITEMS[_next_id] = item
    TAGS[_next_id] = set(t.strip() for t in tags.split(",") if t.strip())
    WORKSPACE_EVENTS.setdefault(workspace_id, []).append({
        "type": "item_created",
        "item_id": _next_id,
        "name": name,
        "notification_count": len([
            subscription
            for subscription in NOTIFICATION_SUBSCRIPTIONS.get(workspace_id, [])
            if subscription["status"] == "active"
        ]),
    })
    _next_id += 1
    return {**item, "tags": list(TAGS[item["id"]])}


@app.get("/workspaces/{workspace_id}/items")
def list_workspace_items(
    workspace_id: int,
    tag: str | None = None,
    _key: dict = Depends(require_workspace_member),
):
    """List items in a workspace. Requires workspace membership."""
    if workspace_id not in WORKSPACES:
        raise HTTPException(status_code=404, detail="Workspace not found")
    items = [item for item in ITEMS.values() if item.get("workspace_id") == workspace_id]
    if tag:
        items = [item for item in items if tag in TAGS.get(item["id"], set())]
    return items


@app.get("/workspaces/{workspace_id}/summary")
def workspace_summary(workspace_id: int, _key: dict = Depends(require_workspace_member)):
    """Return item and tag totals for one workspace."""
    if workspace_id not in WORKSPACES:
        raise HTTPException(status_code=404, detail="Workspace not found")
    workspace_items = [
        item for item in ITEMS.values()
        if item.get("workspace_id") == workspace_id
    ]
    tag_names = {
        tag
        for item in workspace_items
        for tag in TAGS.get(item["id"], set())
    }
    return {
        "workspace_id": workspace_id,
        "item_count": len(workspace_items),
        "unique_tag_count": len(tag_names),
        "member_count": len(WORKSPACES[workspace_id]["members"]),
    }


@app.post("/workspaces/{workspace_id}/audit-reports", status_code=202)
def create_workspace_audit_report(
    workspace_id: int,
    include_items: bool = True,
    include_notifications: bool = True,
    _admin: dict = Depends(require_admin),
):
    """Queue a compliance audit report for a workspace. Requires an admin key."""
    global _next_audit_report_id
    if workspace_id not in WORKSPACES:
        raise HTTPException(status_code=404, detail="Workspace not found")
    workspace_items = [
        item for item in ITEMS.values()
        if item.get("workspace_id") == workspace_id
    ]
    active_notifications = [
        subscription
        for subscription in NOTIFICATION_SUBSCRIPTIONS.get(workspace_id, [])
        if subscription["status"] == "active"
    ]
    report = {
        "id": _next_audit_report_id,
        "workspace_id": workspace_id,
        "status": "queued",
        "sections": {
            "items": include_items,
            "notifications": include_notifications,
        },
        "summary": {
            "item_count": len(workspace_items),
            "active_notification_count": len(active_notifications),
            "event_count": len(WORKSPACE_EVENTS.get(workspace_id, [])),
        },
    }
    AUDIT_REPORTS.setdefault(workspace_id, []).append(report)
    WORKSPACE_EVENTS.setdefault(workspace_id, []).append({
        "type": "audit_report_queued",
        "report_id": _next_audit_report_id,
    })
    _next_audit_report_id += 1
    return report


@app.get("/workspaces/{workspace_id}/audit-reports")
def list_workspace_audit_reports(
    workspace_id: int,
    _key: dict = Depends(require_workspace_member),
):
    """List queued and completed audit reports for a workspace."""
    if workspace_id not in WORKSPACES:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return AUDIT_REPORTS.get(workspace_id, [])


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, _key: dict = Depends(require_api_key)):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    del ITEMS[item_id]
    TAGS.pop(item_id, None)


@app.put("/items/{item_id}")
def update_item(item_id: int, name: str, description: str | None = None):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    ITEMS[item_id]["name"] = name
    if description is not None:
        ITEMS[item_id]["description"] = description
    return {**ITEMS[item_id], "tags": list(TAGS.get(item_id, set()))}


@app.post("/items/{item_id}/tags", status_code=200)
def add_tag(item_id: int, tag: str, _key: dict = Depends(require_api_key)):
    """Add a tag to an item."""
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    TAGS.setdefault(item_id, set()).add(tag)
    return {"id": item_id, "tags": list(TAGS[item_id])}


@app.delete("/items/{item_id}/tags/{tag}", status_code=200)
def remove_tag(item_id: int, tag: str, _key: dict = Depends(require_api_key)):
    """Remove a tag from an item."""
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    TAGS.get(item_id, set()).discard(tag)
    return {"id": item_id, "tags": list(TAGS.get(item_id, set()))}


@app.post("/items/batch-delete", status_code=200)
def batch_delete(item_ids: list[int], _key: dict = Depends(require_api_key)):
    """Delete multiple items in a single request. Returns counts of deleted and not-found IDs."""
    deleted = []
    not_found = []
    for item_id in item_ids:
        if item_id in ITEMS:
            del ITEMS[item_id]
            TAGS.pop(item_id, None)
            deleted.append(item_id)
        else:
            not_found.append(item_id)
    return {"deleted": deleted, "not_found": not_found}


@app.post("/items/batch-tag", status_code=200)
def batch_tag(item_ids: list[int], tag: str, _key: dict = Depends(require_api_key)):
    """Apply a tag to multiple items at once."""
    applied = []
    not_found = []
    for item_id in item_ids:
        if item_id in ITEMS:
            TAGS.setdefault(item_id, set()).add(tag)
            applied.append(item_id)
        else:
            not_found.append(item_id)
    return {"tag": tag, "applied_to": applied, "not_found": not_found}


@app.get("/items/search")
def search_items(q: str):
    """Search items by name substring (case-insensitive)."""
    results = [
        item for item in ITEMS.values()
        if q.lower() in item["name"].lower()
    ]
    return results


@app.post("/items/{item_id}/duplicate", status_code=201)
def duplicate_item(item_id: int):
    """Create a copy of an existing item with a new ID."""
    global _next_id
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    original = ITEMS[item_id]
    copy = {"id": _next_id, "name": f"{original['name']} (copy)", "description": original["description"]}
    ITEMS[_next_id] = copy
    TAGS[_next_id] = set(TAGS.get(item_id, set()))
    _next_id += 1
    return {**copy, "tags": list(TAGS[_next_id - 1])}


@app.get("/items/page/{page}")
def list_items_paginated(page: int, size: int = 10, tag: str | None = None):
    """Return a page of items with total count, optionally filtered by tag."""
    all_items = list(ITEMS.values())
    if tag:
        all_items = [item for item in all_items if tag in TAGS.get(item["id"], set())]
    start = (page - 1) * size
    return {"items": all_items[start:start + size], "total": len(all_items), "page": page}


@app.get("/items/count")
def count_items(tag: str | None = None):
    """Return total item count, optionally filtered by tag."""
    if tag:
        return {"count": sum(1 for item in ITEMS.values() if tag in TAGS.get(item["id"], set())), "tag": tag}
    return {"count": len(ITEMS)}


@app.get("/items/export")
def export_items(fmt: str = "json", tag: str | None = None):
    """Export all items as JSON or CSV. Accepts optional ?tag= filter."""
    items = list(ITEMS.values())
    if tag:
        items = [item for item in items if tag in TAGS.get(item["id"], set())]
    if fmt == "csv":
        import io, csv as csv_mod
        buf = io.StringIO()
        writer = csv_mod.DictWriter(buf, fieldnames=["id", "name", "description"])
        writer.writeheader()
        writer.writerows(items)
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(buf.getvalue(), media_type="text/csv")
    return items


@app.get("/items/stats")
def item_stats():
    """Return aggregate stats: total items, total tags, unique tag names."""
    all_tags = [t for tags in TAGS.values() for t in tags]
    return {
        "total_items": len(ITEMS),
        "total_tags": len(all_tags),
        "unique_tags": list(set(all_tags)),
    }
