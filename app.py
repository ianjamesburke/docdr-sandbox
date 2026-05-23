"""Simple FastAPI app for testing DocDr documentation generation."""
from fastapi import Depends, FastAPI, HTTPException
from auth import require_api_key
from webhooks import router as webhook_router

app = FastAPI(title="Sandbox API", version="0.3.0")
app.include_router(webhook_router)

ITEMS: dict[int, dict] = {}
_next_id = 1


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/items")
def list_items():
    return list(ITEMS.values())


@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    return ITEMS[item_id]


@app.post("/items", status_code=201)
def create_item(name: str, description: str = "", _key: dict = Depends(require_api_key)):
    global _next_id
    item = {"id": _next_id, "name": name, "description": description}
    ITEMS[_next_id] = item
    _next_id += 1
    return item


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, _key: dict = Depends(require_api_key)):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    del ITEMS[item_id]
# Trigger bootstrap


@app.put('/items/{item_id}')
def update_item(item_id: int, name: str):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail='Item not found')
    ITEMS[item_id]['name'] = name
    return ITEMS[item_id]


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
    _next_id += 1
    return copy


@app.get("/items/page/{page}")
def list_items_paginated(page: int, size: int = 10):
    """Return a page of items with total count."""
    all_items = list(ITEMS.values())
    start = (page - 1) * size
    return {"items": all_items[start:start + size], "total": len(all_items), "page": page}


@app.get("/items/count")
def count_items():
    """Return the total number of items."""
    return {"count": len(ITEMS)}
