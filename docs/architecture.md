# Architecture Overview

This document contextualizes the architectural framework of `sandbox-api`.

## System Architecture

The application is designed as an ultra-lightweight monolithic service with an in-memory cache layer. Due to its minimalist layout, performance overhead is kept low, serving as an optimal sandbox template.

```
                +--------------------+
                |   Public Client    |
                +---------+----------+
                          | HTTP Request
                          v   
                +--------------------+      +--------------------+
                |      FastAPI       |<---->|     LRU Cache      |
                |     (app.py)       |      |    (cache.py)      |
                +---------+----------+      +--------------------+
                          | Processes Router / Schema Logic
                          v
                +--------------------+
                |  JSON Response     |
                +--------------------+
```

## Key Components

1. **Application Layer (`app.py`)**:
   All routes, FastAPI instantiation, validation schemas, and exception handlers reside here to reduce architectural fragmentation.

2. **Caching Layer (`cache.py`)**:
   Implements a thread-unsafe in-memory LRU cache (`LRUCache`) used to temporarily store responses and avoid redundant calculations.

3. **Configuration (`pyproject.toml`)**:
   Utilizes modern Python build conventions, storing all runtime dependency configuration (`fastapi[standard]`) in a centralized, declarative manner.

4. **Quality Assurance (`.github/workflows/docdr.yml`)**:
   Ensures that standard workspace rules, API formats, and file updates undergo automatic verification during integration lifecycles.
