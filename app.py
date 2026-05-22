"""Simple FastAPI app for testing DocDr documentation generation."""
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Sandbox API", version="0.1.0")

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
def create_item(name: str, description: str = ""):
    global _next_id
    item = {"id": _next_id, "name": name, "description": description}
    ITEMS[_next_id] = item
    _next_id += 1
    return item


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    del ITEMS[item_id]
# Trigger bootstrap
