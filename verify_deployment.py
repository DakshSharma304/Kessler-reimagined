"""Local, nonpublishing validation of the Modal and Vercel deployment adapters."""

from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("KESSLER_ENV", "production")
os.environ.setdefault("KESSLER_ALLOWED_ORIGINS", '["http://127.0.0.1:5173"]')

from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
import modal
import modal_app


def main():
    origins = json.loads(os.environ["KESSLER_ALLOWED_ORIGINS"])
    if not origins:
        raise RuntimeError("At least one exact frontend origin is required")
    api = modal_app.create_api()
    if modal_app.app.name != "kessler-backend" or not isinstance(modal_app.web, modal.Function):
        raise AssertionError("Modal ASGI entrypoint is not registered")
    cors = next(item for item in api.user_middleware if item.cls is CORSMiddleware)
    if cors.kwargs["allow_origins"] != origins:
        raise AssertionError("Production CORS origins differ from the configured exact origins")
    client = TestClient(api)
    health = client.get("/api/health")
    if health.status_code != 200 or health.json()["status"] != "ok":
        raise AssertionError(f"Modal factory health failed: {health.status_code}")
    preflight = client.options("/api/health", headers={
        "Origin": origins[0], "Access-Control-Request-Method": "GET"})
    if preflight.status_code != 200 or preflight.headers.get("access-control-allow-origin") != origins[0]:
        raise AssertionError("Configured frontend origin did not pass CORS preflight")
    foreign = client.options("/api/health", headers={
        "Origin": "https://not-configured.invalid", "Access-Control-Request-Method": "GET"})
    if foreign.headers.get("access-control-allow-origin"):
        raise AssertionError("Unconfigured origin was accepted")
    paths = api.openapi()["paths"]
    for path in ("/api/positions", "/api/encounters/{encounter_id}/optimize",
                 "/api/probability/calculate", "/api/objects/{object_id}/persistence",
                 "/api/cleanup/optimize"):
        if path not in paths:
            raise AssertionError(f"Required API route missing: {path}")
    vercel = json.loads((ROOT / "frontend" / "vercel.json").read_text())
    if (vercel.get("framework"), vercel.get("outputDirectory")) != ("vite", "dist"):
        raise AssertionError("Vercel is not configured for the frontend Vite build")
    if not any(rule == {"source": "/(.*)", "destination": "/index.html"}
               for rule in vercel.get("rewrites", [])):
        raise AssertionError("Vercel SPA navigation rewrite missing")
    print(f"Deployment adapters passed: Modal {modal.__version__}, FastAPI health/CORS/OpenAPI and Vercel static SPA")


if __name__ == "__main__":
    main()
