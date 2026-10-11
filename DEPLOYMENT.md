# Kessler deployment: Vercel + Modal

This repository contains a Vite/React frontend in `frontend/` and the existing
FastAPI scientific backend in `backend/`. `frontend/vercel.json` serves the SPA;
`modal_app.py` packages that same backend as a Modal ASGI service. The deployment
adapter has been imported and its FastAPI health/CORS configuration tested
locally. A public deployment needs your own Vercel project, Modal account and
exact frontend origin; no public URL or credentials are checked into Git.

## Local development

From the repository root, in two terminals:

```bash
# Terminal 1 — backend, Python 3.12
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cd backend
../.venv/bin/python -m app.server
```

```bash
# Terminal 2 — frontend, Node 22.12+ (24 recommended)
cd frontend
npm ci
VITE_API_BASE_URL=http://127.0.0.1:8000/api npm run dev
```

Open `http://127.0.0.1:5173`. The backend dev configuration accepts that exact
origin. `VITE_API_BASE_URL` must end in `/api`; Vite embeds it at build time. A
production build without it shows a configuration error in the UI. No `.env`
file is loaded by the Python service; use process environment variables.

```bash
# With both services running, from frontend/
npm run typecheck
npm test
npm run smoke
npm run test:e2e
```

The browser suite uses system Chromium when available on Linux. On other
systems run `npx playwright install chromium`; optionally set `CHROMIUM_PATH`
to an installed executable. Headless SwiftShader performance is not representative
of hardware accelerated browsers.

With `requirements-deploy.txt` installed, `./.venv/bin/python verify_deployment.py`
checks the Modal entrypoint, FastAPI health/CORS/OpenAPI and Vercel static config
locally without publishing either service.

For final release verification after this time-limited handoff, also run the
complete backend suite from `backend/` with
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ../.venv/bin/python -m pytest -q`
and the complete frontend suite from `frontend/` with `npm run test:e2e`.
These are not replaced by the focused smoke checks. The current execution
status is recorded in `CHECKPOINTS.md`.

## Production configuration

1. Create a Vercel project from this repository with Root Directory `frontend`.
   Reserve its production origin, for example `https://YOUR-PROJECT.vercel.app`.
   Use Node 22.12+ or 24. The checked-in Vite config builds `dist` and rewrites
   application URLs to `index.html`.
2. In a Python 3.12 environment run `python -m pip install -r
   requirements-deploy.txt`. Authenticate the Modal CLI in your account using
   its official setup flow. Configure its named secret with the **actual** exact
   Vercel production origin:

   ```bash
   modal secret create kessler-config \
     KESSLER_ALLOWED_ORIGINS='["https://YOUR-PROJECT.vercel.app"]'
   ```

   Add each preview/custom-domain origin explicitly if it needs browser access.
   No wildcard CORS origin is accepted by the backend. The Modal function sets
   `KESSLER_ENV=production`, uses a persistent cache volume, four CPUs, 8 GiB,
   one container and bounded request concurrency. The scientific application
   and pinned `backend/requirements.txt` are reused without a model fork.
3. From the repository root run `modal deploy modal_app.py`. Modal reports the
   actual public ASGI URL. Verify `GET <reported-url>/api/health` and browser
   preflight from your exact Vercel origin before publishing the frontend. The
   first real source request may download or parse public data.
4. In Vercel set the **build-time** environment variable
   `VITE_API_BASE_URL=<reported-Modal-url>/api` for Production, then build/deploy
   the frontend. Set it for Preview as well only when its exact origins are in
   the Modal secret. Vercel must rebuild after the value changes.
5. Run the six real browser workflows against those public URLs. Check the
   network console for CORS or source errors and verify source timestamps and
   scientific statuses. Backend CORS grants browser access; it is not user
   authentication. Modal and Vercel usage may incur account charges.

The Modal URL, Vercel origin, accounts and billing settings are deployment
specific and cannot be inferred from the repository. This document does not
claim a public deployment has occurred. The local production preview is verified
separately from cloud publication in `CHECKPOINTS.md`.

## Runtime behavior

The backend's `KESSLER_ALLOWED_ORIGINS` is a JSON array of explicit origins.
If it is absent in production, the backend permits no browser origins; the
Modal adapter requires it in `kessler-config`. `KESSLER_CACHE_DIR` points to
the named persistent Modal volume. Volume/cache content is a performance aid,
not an offline live-data fixture. No credentials are required for the public
scientific source APIs, but network access is needed for live SOCRATES,
CelesTrak and space-weather retrieval. Source failures remain visible in the
UI. NASA CARA fixtures are historical validation cases shipped with the code.

The Python server permits two concurrent expensive calculations per process;
Modal accepts up to eight HTTP inputs in its single container. Requests can
return 429 BUSY or a source/numerical status. The frontend reports those states
and uses a 240-second client timeout; an upstream proxy may impose a shorter
limit. Long or high-cost analyses need an explicit future job workflow rather
than an implied progress percentage. UI decay horizons are bounded to one day,
while the backend supports a larger validated range.
