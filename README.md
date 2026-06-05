# sandbox-api

A modern, lightweight API environment designed for sandboxing and quick evaluation. Powered by Python 3.11+ and FastAPI.

## Prerequisites

- **Python**: `>=3.11`
- **Package Manager**: `pip` (or `uv` for fast installations)

## Getting Started

### 1. Set Up Environment

Clone the repository and set up a virtual environment:

```bash
# Clone the repository
cd sandbox-api

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

Install the package along with its FastAPI standard dependencies:

```bash
pip install -e .
```

### 3. Run the Server

Launch the development server using the FastAPI CLI:

```bash
fastapi dev app.py
```

Once running, navigate to:
- **Interactive Swagger UI**: `http://127.0.0.1:8000/docs` 
- **Alternative ReDoc UI**: `http://127.0.0.1:8000/redoc` 

## Repository Structure

- `app.py`: Core application entrypoint defining paths, middleware, and request/response lifecycles.
- `pyproject.toml`: Project metadata, tool configurations, and dependency lists conforming to PEP 621.
- `.github/workflows/docdr.yml`: CI/CD workflow running DocDr to automatically maintain and update documentation upon pull request merges.
