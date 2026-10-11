"""HTTP contract and startup checks for checkpoint 1."""

import importlib
import pkgutil

from fastapi.testclient import TestClient

import app
from app.api.routes import HealthResponse
from app.main import app as application


def test_every_initialized_module_imports():
    modules = list(pkgutil.walk_packages(app.__path__, prefix="app."))
    assert {module.name for module in modules} >= {
        "app.config", "app.main", "app.api", "app.api.routes"
    }
    for module in modules:
        importlib.import_module(module.name)


def test_health_response():
    with TestClient(application) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok", "service": "Kessler", "version": "0.1.0"
    }
    assert HealthResponse.model_validate(response.json()).status == "ok"


def test_health_openapi_schema():
    with TestClient(application) as client:
        schema = client.get("/openapi.json").json()
    assert "/api/health" in schema["paths"]
    assert set(schema["components"]["schemas"]["HealthResponse"]["required"]) == {
        "status", "service", "version"
    }
