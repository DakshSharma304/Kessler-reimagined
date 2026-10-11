"""Modal ASGI deployment for the existing Kessler FastAPI application.

Run from the repository root: modal deploy modal_app.py
The named Modal secret must supply KESSLER_ALLOWED_ORIGINS as a JSON array of
exact Vercel origins. Scientific code remains in backend/app, unchanged.
"""

from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent
app = modal.App("kessler-backend")
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements(str(ROOT / "backend" / "requirements.txt"))
    .add_local_dir(
        ROOT / "backend" / "app",
        remote_path="/root/app",
        ignore=["**/__pycache__/**", "**/*.pyc"],
    )
)
cache = modal.Volume.from_name("kessler-data-cache", create_if_missing=True)
frontend_origins = modal.Secret.from_name(
    "kessler-config", required_keys=["KESSLER_ALLOWED_ORIGINS"]
)


def create_api():
    """Local validator and Modal worker share the exact FastAPI factory."""
    from app.main import app as fastapi_app

    return fastapi_app


@app.function(
    image=image,
    secrets=[frontend_origins],
    volumes={"/cache": cache},
    env={"KESSLER_ENV": "production", "KESSLER_CACHE_DIR": "/cache/kessler"},
    cpu=4,
    memory=8192,
    max_containers=1,
    scaledown_window=300,
    timeout=600,
)
@modal.concurrent(max_inputs=8)
@modal.asgi_app()
def web():
    """Cold starts load the API; live data is fetched only by explicit requests."""
    return create_api()
