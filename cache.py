"""In-memory LRU cache for API responses."""
from collections import OrderedDict
from typing import Any


class LRUCache:
    """Thread-unsafe LRU cache with a fixed max size.

    When the cache is full, the least recently accessed entry is evicted.
    """

    def __init__(self, max_size: int = 128):
        self._max_size = max_size
        self._store: OrderedDict[str, Any] = OrderedDict()

    def get(self, key: str) -> Any | None:
        if key in self._store:
            self._store.move_to_end(key)
            return self._store[key]
        return None

    def set(self, key: str, value: Any) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        if len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def invalidate(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    def clear(self) -> None:
        self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)
