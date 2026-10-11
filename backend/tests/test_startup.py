"""Exercise the real uvicorn process and HTTP transport, not just ASGI mocks."""

from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx


def test_uvicorn_starts_and_serves_health(tmp_path):
    with socket.socket() as address:
        address.bind(("127.0.0.1", 0))
        port = address.getsockname()[1]
    with (tmp_path / "uvicorn.log").open("w+") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
             "--port", str(port)],
            cwd=Path(__file__).resolve().parents[1], stdout=log, stderr=log,
        )
        try:
            deadline = time.monotonic() + 15
            response = None
            with httpx.Client(timeout=1, trust_env=False) as client:
                while time.monotonic() < deadline and process.poll() is None:
                    try:
                        response = client.get(f"http://127.0.0.1:{port}/api/health")
                        break
                    except httpx.TransportError:
                        time.sleep(0.05)
            log.flush()
            log.seek(0)
            assert response is not None, f"Server did not start: {log.read()}"
            assert response.status_code == 200
            assert response.json() == {
                "status": "ok", "service": "Kessler", "version": "0.1.0"
            }
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
