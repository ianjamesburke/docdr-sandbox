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
                |      FastAPI       |
                |  (app.py + router) |
                +----+-----------+---+
                     |           |
                     v           v
         +-----------+------+  +--------------------+
         | Webhook Registry |  |  JSON Response     |
         |  (webhooks.py)   |  +--------------------+
         +------------------+
```

## Key Components

1. **Application Layer (`app.py`)**:
   All routes, FastAPI instantiation, validation schemas, and exception handlers reside here to reduce architectural fragmentation. It integrates the webhook router for event notifications.

2. **Webhooks Subsystem (`webhooks.py`)**:
   Registers and manages callback endpoints, supporting HMAC-SHA256 signature generation to secure outbound notifications.

3. **Configuration (`pyproject.toml`)**:
   Utilizes modern Python build conventions, storing all runtime dependency configuration (`fastapi[standard]`) in a centralized, declarative manner.

4. **Quality Assurance (`.github/workflows/docdr.yml`)**:
   Ensures that standard workspace rules, API formats, and file updates undergo automatic verification during integration lifecycles.
