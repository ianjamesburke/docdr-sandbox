"""Simple FastAPI app for testing DocDr documentation generation."""
from fastapi import Depends, FastAPI, HTTPException
from auth import require_api_key
from cache import LRUCache
from middleware import RequestLoggingMiddleware
from webhooks import router as webhook_router

app = FastAPI(title="Sandbox API", version="0.6.0")
item_cache = LRUCache(max_size=256)
app.add_middleware(RequestLoggingMiddleware)
app.include_router(webhook_router)

ITEMS: dict[int, dict] = {}
TAGS: dict[int, set[str]] = {}
_next_id = 1


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/items")
def list_items(tag: str | None = None):
    if tag:
        return [item for item in ITEMS.values() if tag in TAGS.get(item["id"], set())]
    return list(ITEMS.values())


@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    return {**ITEMS[item_id], "tags": list(TAGS.get(item_id, set()))}


@app.post("/items", status_code=201)
def create_item(name: str, description: str = "", tags: str = "", _key: dict = Depends(require_api_key)):
    global _next_id
    item = {"id": _next_id, "name": name, "description": description}
    ITEMS[_next_id] = item
    TAGS[_next_id] = set(t.strip() for t in tags.split(",") if t.strip())
    _next_id += 1
    return {**item, "tags": list(TAGS[item["id"]])}


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
