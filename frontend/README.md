# Kessler orbital interface

React 19, TypeScript and Three.js frontend for the existing Kessler Python API.
The UI is designed as a restrained orbital instrument: graphite surfaces,
native system typography, real source data, and color only for known object
classes, trajectories and statuses. It runs as regular repository code and
builds as a static site for Vercel. The backend is the scientific source.

## Start

Start the backend using [`../DEPLOYMENT.md`](../DEPLOYMENT.md). Then:

```bash
cd frontend
npm ci
VITE_API_BASE_URL=http://127.0.0.1:8000/api npm run dev
```

Open `http://127.0.0.1:5173`. The production Vercel build must set
`VITE_API_BASE_URL` to the actual Modal URL **including `/api`** before building.
The checked-in `.env.example` documents the local value; no credentials
belong in a `VITE_` variable. The `.env.local` override is ignored by Git.

## Workspaces

- Explore: bounded partial catalog, category filters, catalog-wide search,
  real batched ITRS positions and selected orbital trajectory.
- Close approaches: published SOCRATES encounters, recalculated separation,
  source disagreement, participant paths and honest Pc availability.
- Avoidance planner: explicit hypothetical capability, adjustable constraints,
  real optimization alternatives, matched trajectory comparison and bounded
  secondary screening.
- Orbital decay: explicit mass/area/Cd/weather/horizon, numerical sample charts
  and low/nominal/high scenario states when selected.
- Cleanup planner: configurable, auditable policy scores, exclusions, abstract
  effort budgets and a selected portfolio highlighted on the globe.
- Data & methods: status, coverage, coordinate/unit contract, limitations,
  actual NASA CARA historical benchmark comparison and asset attribution.

The globe maps backend ITRS kilometers `(x,y,z)` to Three.js `(x,z,-y)`, scaled
by the WGS84 equatorial radius. It never propagates or relabels orbits in
JavaScript. The renderer requests at most 2,000 positions in a batch, shows
failed objects as unavailable, and renders only actual returned path samples.
On narrow screens the inspector acts as a sheet and the nav follows the active
workspace. `/` focuses an available search; Escape closes the inspector;
`R` resets Earth focus; Space toggles playback outside form controls.
Reduced-motion preference disables nonessential movement.

## Checks

With the real backend on port 8000:

```bash
npm run format:check
npm run typecheck
npm run build
npm test
npm run smoke
npm run test:e2e
```

The full browser suite uses real NASA Pc, SOCRATES, CelesTrak, optimizer,
screening, NRLMSIS persistence and cleanup responses. One isolated 503 test
checks error presentation without substituting scientific outputs. Browser
capture artifacts are in `test-results/` (ignored by Git); reviewed demo images
are in `docs/screenshots/`. A production build embeds the provided API URL;
Vercel and Modal deployment details are in [`../DEPLOYMENT.md`](../DEPLOYMENT.md).

SOCRATES MAX_PROB is a screening metric, not covariance-aware collision Pc.
Assumed covariance, aerodynamic properties and weather are always labeled.
Fixed-covariance maneuver comparisons do not propagate uncertainty. Cleanup
scores are a decision proxy, not removal missions, cost or prevented-collision
counts. Reported boundary crossing is a finite model cutoff, not certain
reentry. Initial source fetches and expensive calculations can take time or
fail independently of the frontend; the UI retains those statuses and errors.
