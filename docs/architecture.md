# Architecture Overview

This document contextualizes the architectural framework of `sandbox-api`.

## System Architecture

The application is designed as an ultra-lightweight monolithic service. Due to its minimalist layout, performance overhead is kept low, serving as an optimal sandbox template.

```
                +--------------------+
                |   Public Client    |
                +---------+----------+
                          | HTTP Request (with optional X-API-Key)
                          v   
                +--------------------+
                |      FastAPI       |
                | (app.py & auth.py) |
                +---------+----------+
                          | Processes Router / Schema / Auth Logic
                          v
                +--------------------+
                |  JSON Response     |
                +--------------------+
```

## Key Components

1. **Application Layer (`app.py`)**:
   All routes, FastAPI instantiation, validation schemas, and exception handlers reside here. It utilizes dependency injection to hook into the authentication layer for protected routes.

2. **Authentication Layer (`auth.py`)**:
   Handles API key generation and validation (`X-API-Key` header), guarding write operations (`create_item`, `delete_item`) and enabling multi-tier controls like admin verification.

3. **Configuration (`pyproject.toml`)**:
   Utilizes modern Python build conventions, storing all runtime dependency configuration (`fastapi[standard]`) in a centralized, declarative manner.

4. **Quality Assurance (`.github/workflows/docdr.yml`)**:
   Ensures that standard workspace rules, API formats, and file updates undergo automatic verification during integration lifecycles.
