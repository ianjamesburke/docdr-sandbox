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
                | Metrics/Logging    |
                |    Middleware      |
                +---------+----------+
                          | Pass-through
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
   All core configurations, FastAPI instantiation, validation schemas, and global exception handlers reside here to reduce architectural fragmentation. Routes are managed via specialized APIRouters.

2. **Billing & Subscription Models (`billing.py`)**:
   Handles workspace billing tier management, plan configurations (`free`, `team`, `enterprise`), active subscriptions, and sandbox invoice generation.

3. **Telemetry & Metrics (`metrics.py`)**:
   Custom middleware and log collector that tracks request volumetric rates, averages request latency, and measures status-code failure counts.

4. **Configuration (`pyproject.toml`)**:
   Utilizes modern Python build conventions, storing all runtime dependency configuration (`fastapi[standard]`) in a centralized, declarative manner.

5. **Quality Assurance (`.github/workflows/docdr.yml`)**:
   Ensures that standard workspace rules, API formats, and file updates undergo automatic verification during integration lifecycles.
