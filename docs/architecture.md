# Architecture Overview

This document contextualizes the architectural framework of `sandbox-api`.

## System Architecture

The application is designed as an ultra-lightweight monolithic service. Due to its minimalist layout, performance overhead is kept low, serving as an optimal sandbox template.

```
                +--------------------+
                |   Public Client    |
                +---------+----------+
                          | HTTP Request
                          v   
                +--------------------+
                |   Middleware.py    |
                |  (Log/Rate Limit)  |
                +---------+----------+
                          | Passed Requests
                          v   
                +--------------------+
                |      FastAPI       |
                |     (app.py)       |
                +---------+----------+
                          | Processes Router / Schema Logic
                          v
                +--------------------+
                |  JSON Response     |
                +--------------------+
```

## Key Components

1. **Application Layer (`app.py`)**:
   All routes, FastAPI instantiation, validation schemas, and exception handlers reside here to reduce architectural fragmentation.

2. **Middleware (`middleware.py`)**:
   Intercepts incoming requests to record response latencies, log request paths, and enforce an in-memory sliding window rate limit of 60 requests per minute per IP address. It emits an HTTP `429 Too Many Requests` response code if the limit is exceeded.

3. **Configuration (`pyproject.toml`)**:
   Utilizes modern Python build conventions, storing all runtime dependency configuration (`fastapi[standard]`) in a centralized, declarative manner.

4. **Quality Assurance (`.github/workflows/docdr.yml`)**:
   Ensures that standard workspace rules, API formats, and file updates undergo automatic verification during integration lifecycles.
