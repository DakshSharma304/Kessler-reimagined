# Kessler backend

Python 3.12+ backend for the first Kessler orbital avoidance pipeline.
Implementation proceeds in tested stages; see `CHECKPOINTS.md` for completed
checks and any blockers. The health endpoint and SOCRATES ingestion are
implemented, along with encounter discovery, GP orbital retrieval, SGP4 baseline
analysis, matched numerical maneuver simulation, and bounded dynamic optimization.
All 13 stages passed their checkpoints, including three actual upcoming encounters
through the CLI with changed constraints, live API checks, the interactive CLI
demonstration and actual-machine benchmarks. The final suite passed all 108 tests.
The object endpoint and its OpenAPI response schema use normalized names such
as `object_id`; CelesTrak OMM names remain supported on ingestion.

Phase 2 adds optional secondary-conjunction screening through the API and CLI.
All **nine checkpoints passed**, including the authorized duplicate-event
correction, three actual encounter pipelines and API/CLI demonstrations.
Final full-suite verification: **197 passed, 2 warnings in 300.03 seconds**,
including all 108 original Phase 1 tests. The broader catalog contains **19,505** unique
records and has explicitly **PARTIAL** coverage. Old/failed records and exhausted
budgets produce `INCOMPLETE`, never a screening-policy pass.
See `CHECKPOINTS.md` and `SECONDARY_SCREENING_DESIGN.md` for details.

Phase 3 adds covariance-based collision probability (Pc): strict historical
NASA CDM ingestion, per-object covariance transformations, deterministic
Gaussian collision-disk integration, honest live availability, and optional
illustrative fixed-covariance maneuver comparisons. The original simulator,
clearance optimizer and default API/CLI responses are preserved. Phase 3 added
no frontend, decay model, cleanup optimization or extra dependencies; the
separate Phase 4 persistence model is documented below.
All **nine Phase 3 checkpoints passed**. Final complete suite: **302 passed,
2 upstream warnings in 297.29 seconds**—all 197 prior tests plus 105 new tests,
with zero failed, skipped or deselected tests.

## Phase 5 — frontend integration

Backend-only Phase 5 integrates the existing scientific engines with a
visualization-ready catalog, optional compact persistence trajectories and a
transparent debris-cleanup priority/portfolio MVP. No frontend is implemented.
**All six Phase5 checkpoints passed: 445 automated tests, no skipped tests;
all six real public API workflows and four NASA reference Pc comparisons pass.**
KESSLER BACKEND: FRONTEND READY.
The exact handoff is [FRONTEND_CONTRACT.md](FRONTEND_CONTRACT.md): all21 paths/
22 operations, request/response schemas, six actual workflow examples, units,
statuses, CORS and workload bounds. [openapi.json](openapi.json) matches the
running app. [frontend_examples.json](frontend_examples.json) is a dated HTTP
transcript, not permanently current orbital data. See `CHECKPOINTS.md` for gates.

From the installed repository, with the backend running separately:

```sh
cd backend
../.venv/bin/python -m app.frontend_smoke --base-url http://127.0.0.1:8000
# Actual six-workflow/nine-operation HTTP benchmark:
../.venv/bin/python scripts/benchmark_frontend.py --base-url http://127.0.0.1:8000
# Regenerate OpenAPI and the contract's schema appendix:
../.venv/bin/python -m app.export_frontend
```

See [PERFORMANCE.md](PERFORMANCE.md) and [performance.json](performance.json)
for measured workloads, times and scientific validation. Run the complete suite
using `../.venv/bin/python -m pytest -q --maxfail=1` from backend.

Environment configuration (not automatically loaded from `.env`):
`KESSLER_HOST`, `KESSLER_PORT`, `KESSLER_CACHE_DIR`, `KESSLER_DATA_DIR`,
`KESSLER_CATALOG_FILES` (JSON array of actual local OMM paths),
`KESSLER_METADATA_FILE` (optional SATCAT CSV), `KESSLER_ALLOWED_ORIGINS`
(JSON array of exact HTTP(S) origins), `KESSLER_ENV=production` and
`KESSLER_MAX_CALCULATIONS` (default2, range1..8). See `backend/.env.example`.
Production defaults to no browser origins; configure the actual frontend
origin. Local defaults permit localhost/127.0.0.1 on ports5173/3000.
No authentication: CORS is not access control. Paths are configurable; no
developer-specific filesystem path is needed. Startup downloads no datasets.

Visualization positions are **ITRS/ECEF kilometers**, aware UTC ISO8601;
Three.js right-handed Y-up uses `(x,z,-y)` with a consistent display scale.
Actual SGP4 TEME and numerical GCRS states are transformed, never relabeled.
Bulk requests accept up to2000 IDs, paths up to1001 samples, single-object
orbit intervals up to24hours. Per-object failures have null positions/status.
Existing scientific SI/TEME/GCRS contracts remain unchanged. Public snapshots
are reused for at most five minutes across browsing and matching default
screening scopes; custom/local scopes retain their requested populations.
Original source timestamps/checksums, old GP epoch checks and warnings remain.

Cleanup is an illustrative additive policy proxy, not a removal mission plan
or expected collisions prevented. Supported debris/rocket-body classifications
only; unknown mass/area/dimensions stay null. Default weights use capped
SOCRATES counts over its limited published screening window. Optional
persistence/RCS evidence is explicit; missing weighted evidence does not
fabricate a score. Fixed-count selection is stable; user-supplied heterogeneous
abstract effort budgets use bounded binary HiGHS selection. Costs are not
dollars and shared events are not independent prevented-collision benefits.
Candidate scope, exclusions and selection reasons accompany each portfolio.

Live SOCRATES lacks measured covariance-based Pc; its maximum screening metric
stays separate. User covariance/aerodynamic/weather assumptions are illustrative;
fixed-covariance maneuver Pc is not operationally calibrated. Catalog coverage
is PARTIAL; bounded secondary screening can be INCOMPLETE, not a safety pass.
Lifetimes are censored when the boundary is not reached. Ordinary browsing
performs no atmospheric propagation. No verified fully offline six-workflow
server mode exists: genuine local/NASA fixtures support component development
and are labeled historical/offline, not live. Expensive calls are bounded,
synchronous: show waiting, handle429 BUSY and configure request/proxy timeouts.

## Install

From the repository root:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
```

## Start the API

```sh
cd backend
../.venv/bin/python -m app.server
```

The health endpoint is `GET /api/health`; interactive API documentation is at
`/docs`. The server does not fetch orbital data at startup.

| Method | Endpoint | Action |
| --- | --- | --- |
| GET | `/api/health` | Service health |
| GET | `/api/status` | Loaded-source/cache status; no live readiness claim |
| GET | `/api/catalog/status` | Last explicitly loaded catalog metadata; no download |
| GET | `/api/encounters` | Upcoming encounters; `sort`, `limit`, `object_id`, `name` |
| GET | `/api/encounters/{id}` | Selected source encounter and quality warnings |
| POST | `/api/encounters/{id}/analyze` | Local SGP4 baseline refinement |
| POST | `/api/encounters/{id}/simulate` | Actual hypothetical impulsive simulation |
| POST | `/api/encounters/{id}/optimize` | Bounded search; optional `secondary_screening` settings |
| POST | `/api/encounters/{id}/screen` | Compare nominal and differential post-burn trajectories |
| GET | `/api/objects/{id}` | Selected GP record, epoch and provenance |
| POST | `/api/probability/calculate` | Supplied common-frame Pc or explicit NASA reference benchmark |
| GET | `/api/space-weather/status` | Weather snapshot/coverage; `load=true` explicitly retrieves |
| POST | `/api/atmosphere/density` | Actual NRLMSIS 2.1 density from explicit/source weather |
| POST | `/api/objects/{id}/decay` | Bounded gravity/J2/drag propagation and boundary status |
| POST | `/api/objects/{id}/persistence` | Same propagation with scenario/persistence metrics |
| GET | `/api/objects` | Paginated/searchable/classified catalog and coverage |
| POST | `/api/positions` | Bounded bulk ITRS/ECEF positions in km |
| GET | `/api/objects/{id}/metadata` | Joined metadata and provenance |
| GET | `/api/objects/{id}/trajectory` | Sampled real orbit in ITRS/km |
| GET | `/api/encounters/{id}/trajectories` | Nominal participant paths in ITRS/km |
| POST | `/api/encounters/{id}/trajectories` | Matched baseline/modified maneuver paths in ITRS/km |
| POST | `/api/cleanup/optimize` | Explained, bounded additive-priority portfolio |

An unknown encounter returns 404. Invalid requests and unsupported scientific
inputs return 422; unavailable source/orbital data return 503 with an explicit
status and explanation. `/api/status` reports what has been loaded, and does
not silently download data or certify live access.

## Run the CLI

Interactive demonstration, from the repository root:

```sh
cd backend
../.venv/bin/python -m app.cli
```

Choose an actual upcoming encounter and maneuvering object, explicitly confirm
the hypothetical capability assumption, then provide the delta-v budget,
lead-time window, target separation and objective. Invalid menu/numeric input
is retried; unsupported scenarios return a clear error. Choose option 1 for
minimum effort or option 2 for maximum modeled clearance.
After optimization, optionally answer “yes” to screen the maneuver, then choose
the policy, illustrative threshold, horizon and public-group/local-file scope.
Declining or ending input leaves primary results explicitly unscreened.

Noninteractive JSON commands, from `backend/`:

```sh
../.venv/bin/python -m app.cli --json list --sort minimum_separation --limit 5
../.venv/bin/python -m app.cli --json analyze --encounter-id ENCOUNTER_ID
../.venv/bin/python -m app.cli --json optimize \
  --encounter-id ENCOUNTER_ID --object-id NORAD_ID \
  --max-delta-v 0.2 --min-lead-minutes 15 --max-lead-hours 2 \
  --target-km 10 --objective MAXIMUM_CLEARANCE --assume-capability
../.venv/bin/python -m app.cli --json simulate \
  --encounter-id ENCOUNTER_ID --object-id NORAD_ID \
  --maneuver-time ISO_UTC_TIMESTAMP --delta-v-rtn 0 0.1 0 --assume-capability
```

Replace `ENCOUNTER_ID` and `NORAD_ID` with values from `list`, and use a future
burn timestamp before TCA. IDs include the actual pair and encounter timestamp
in their digest and are not reusable indefinitely. `--json` and `--cache-dir`
are global options and go before the command. Inspect `--help` on each command.
JSON errors use a nonzero exit status; no scientific result is substituted.

Optional fuel conversion accepts all three of `--initial-mass-kg`,
`--propellant-mass-kg` and `--specific-impulse-s`. With partial propulsion inputs
the request is rejected. Without them no fuel consumption/capability is invented.

## Constraint and objective definitions

| Input | Meaning |
| --- | --- |
| `encounter_id` | Selected source encounter, matching the API URL when applicable |
| `maneuvering_object_id` | One of that encounter's two participating catalog IDs |
| `max_delta_v_m_s` | Nonnegative maximum impulse magnitude in m/s |
| `min_lead_time_minutes` | Positive minimum preparation time before published TCA |
| `max_lead_time_hours` | Maximum lead time, greater than the minimum and at most 48 hours |
| `target_miss_distance_km` | Desired modeled separation in km; no operational safety guarantee |
| `objective` | `MINIMUM_DELTA_V` or `MAXIMUM_CLEARANCE` |
| `hypothetical_capability_assumed` | Explicit `true`; maneuverability is never inferred from names/status |

MINIMUM_DELTA_V selects the lowest-effort **evaluated** candidate reaching the
target; no evaluated solution produces `NO_FEASIBLE_SOLUTION`. MAXIMUM_CLEARANCE
selects greatest evaluated clearance within the hard budget and time constraints.
It may return `meets_target=false` with an explicit warning if the target was not
reached. `COMPLETE` means the bounded search completed, not that the maneuver is
operationally safe. Time/evaluation limits return honestly labeled `PARTIAL`
results. A sampled search is not a proof of global optimality.

Default search uses six burn times, three nonzero magnitudes and both signs of
transverse, radial and normal impulses, plus zero burn and local refinement.
The default cap is 150 simulations and 25 seconds. `search` in the optimization
API request can configure the bounded search; corresponding CLI flags include
`--time-samples`, `--magnitude-samples`, `--max-evaluations`, `--timeout-seconds`,
and `--refinement-evaluations`.

## Tests

Phase 3 commands and scientific assumptions are documented below. All
checkpoint evidence, including actual failure diagnoses and reruns, is in
`CHECKPOINTS.md`.

```sh
cd backend
../.venv/bin/python -m pytest -v
```

The startup test launches uvicorn, makes an actual HTTP request, and terminates
only its own process.

Phase 1 verification: **108 passed, 2 warnings in 109.85 seconds**, with no failed,
skipped or deselected tests. The warnings concern an upstream Starlette/AnyIO
deprecation and a read-only Astropy cache; installed offline IERS data were used.
Full commands and measured results are recorded in `CHECKPOINTS.md`.
Phase 2 final verification: **197 passed, 2 warnings in 300.03 seconds**, zero
failed/skipped/deselected tests. This includes **89** new tests, all **108**
original tests, the six controlled numerical orbital scenarios, real-data
integration, API/CLI scientific agreement, uvicorn startup and concurrency checks.

Live tests require access to `celestrak.org`. Earlier proxy HTTP 403 failures
were resolved after restarting with the updated network settings. To run offline
tests without contacting CelesTrak:

```sh
cd backend
../.venv/bin/python -m pytest -m 'not live' -v
```

To run the actual source and ingestion checks:

```sh
cd backend
../.venv/bin/python -m pytest -m live -v -s
```

SOCRATES data are cached under `backend/.cache/kessler/` by default;
`KESSLER_CACHE_DIR` overrides this path. Refreshes are limited to once every
11 hours, following the current SOCRATES Plus usage policy. A failed refresh
retains the valid previous dataset and marks it stale. Further queries by that
client halt until operator action/restart. GP orbital records use a two-hour
cache. Phase 1 downloads individually selected objects; Phase 2 separately
downloads declared bulk public groups. Missing or mismatched
records are never replaced with another orbit.
The CSV range and speed are converted from km and km/s to m and m/s. The
HTTP Last-Modified timestamp, fetch time, original source URL, and SHA-256
checksum accompany each dataset. Parsing rejects malformed rows while retaining
valid ones, and reports invalid and duplicate counts. The SHA-256 cache checksum
detects corruption; it is not a cryptographic signature from the publisher.

## Scientific scope

This phase concerns hypothetical orbital calculations, not flight commands.
SOCRATES reports predicted close approaches; its MAX_PROB screening metric is
not a calibrated collision probability. Nominal clearance is not a guarantee
of collision avoidance or operational safety. Maneuver capability must be
supplied as a hypothetical assumption. Without opt-in screening, secondary
conjunctions remain unassessed. With screening, only the stated available catalog
and interval are checked; incomplete results cannot establish absence of
additional encounters. Published SOCRATES predictions, current-GP SGP4 predictions and matched
numerical zero-burn predictions are separately labeled; force-model drift is not
attributed to a maneuver.

SGP4 uses WGS72 and returns TEME states. Astropy transforms positions and
velocities to GCRS for DOP853 numerical integration with central Earth gravity
and J2 using WGS84 constants. The Earth pole is fixed at the reference epoch
over the modeled interval. RTN transverse is perpendicular to radial in the
orbital plane; it is not always exactly the eccentric-orbit velocity direction.
All optimizer candidates share a common numerical reference epoch and baseline.

The existing collision-avoidance force model excludes drag, higher harmonics, third-body forces and future
real spacecraft maneuvers. Maneuver lead times are capped at 48 hours. Cached
installed IERS data are used without network downloads; predictive Earth
orientation is a limitation. The initial search is local ±300 seconds around
the published TCA, with sampled minima refined using squared separation.
Boundary minima are flagged, and the optimizer rejects those candidate results.
Elements more than seven days from TCA are conservatively unsupported. Reporting
thresholds (>100 m separation discrepancy or >60 s TCA discrepancy) and
integration tolerances are not physical uncertainty bounds.

Observed current-GP disagreement can be large. In the tested 53495/34452 case,
SOCRATES published 7 m while current-GP SGP4 predicted about 9,330 m. That is
reported as a discrepancy, not agreement or evidence of an actual collision.
With a common two-hour numerical reference, its matched baseline was 9,321 m;
the small test searches found about 10,052 m at 0.1 m/s and 11,524 m at 0.3 m/s.
These are actually computed examples for the tested dataset, not preset results.

## Benchmarks

From `backend/`:

```sh
../.venv/bin/python -m app.benchmark
```

This prints actual-machine JSON timings for initial dataset load/indexing,
indexed lookup, cached GP retrieval, baseline calculation, one maneuver,
100/1,000 SGP4 states and a full bounded optimization. Timings are measurements,
not promises; see `CHECKPOINTS.md` for executed results. Initial parsing of the
195,282-row source is measured separately from indexed lookup. The API reuses
its loaded dataset and initialized propagators.

Standalone measured results on Python 3.12.14 (Linux):

| Operation | Seconds |
| --- | ---: |
| Initial cached-source parsing/indexing, 195,282 encounters | 8.952407 |
| Indexed encounter lookup | 0.000071 |
| Cached GP pair retrieval | 0.000010 |
| SGP4 baseline refinement | 0.005099 |
| One maneuver, including initial frame setup | 0.581133 |
| 100 / 1,000 SGP4 states | 0.001614 / 0.045161 |
| Default optimization, 123 evaluated candidates | 2.878021 |

The live interactive example selected objects 53495/34452 with a 0.2 m/s budget,
a 15-minute to two-hour lead window and a 10 km illustrative target. Its best
evaluated hypothetical burn was at `2026-10-13T03:09:03.882Z`, with RTN delta-v
`(0.01990074, 0.19900744, 0)` m/s. The common numerical baseline was 9,321.113 m;
modeled clearance became 10,796.958 m, an increase of 1,475.845 m. The target was
met numerically, not certified safe. These time-dependent results describe the
tested snapshot; later source data or expired windows will change the outcome.

## Repository structure

```text
backend/
  app/
    main.py, config.py, engine.py, cli.py, benchmark.py
    api/          # HTTP routes and validated API schemas
    data/         # SOCRATES, GP, discovery and atomic file caching
    models/       # encounters, GP records and maneuver constraints
    physics/      # SGP4, frame transforms, refinement and J2 maneuvers
    optimization/ # objective ordering and bounded actual-simulation search
  tests/          # unit, API, CLI, live integration and performance checks
    fixtures/     # actually downloaded source rows/GP records and provenance
  requirements.txt, pytest.ini
README.md
CHECKPOINTS.md
```

No frontend, cleanup optimization, atmospheric decay, covariance/Pc,
authentication or operational spacecraft commands are implemented.

## Phase 2: secondary-conjunction screening

The existing primary optimizer, SGP4 propagator, RTN basis, Astropy frame
transforms, dense DOP853/J2 integrator, validated GP models and atomic public-data
cache are reused. The primary search is unchanged. Only a bounded ranked
finalist pool is screened; it is not 123 full catalog screens by default.

New modules:

| Module | Purpose |
| --- | --- |
| `app/data/catalog.py`, `app/models/catalog.py` | Bulk/local OMM ingestion, canonical-ID deduplication, cache and snapshot provenance |
| `app/models/screening.py` | Validated requests, settings, classifications, coverage/completion and policy results |
| `app/physics/screening_trajectories.py` | Matched numerical maneuver differential applied to nominal SGP4 |
| `app/physics/secondary_search.py` | Batched one-vs-catalog segment filter, continuous refinement and bounded thread-safe position cache |
| `app/physics/secondary_comparison.py` | Same-window baseline/modified event matching and calculated classifications |
| `app/secondary.py` | Shared proposed-maneuver service and selected/counterpart provenance |
| `app/optimization/screened_optimizer.py` | Optional policy checks on genuine ranked primary finalists |
| `app/secondary_benchmark.py` | Actual per-stage measurements and optional cumulative-time profiling |

### Catalog selection and coverage

From `backend/`, load the documented default public groups explicitly:

```sh
../.venv/bin/python -m app.cli --json catalog
../.venv/bin/python -m app.cli --json catalog --catalog-group visual
../.venv/bin/python -m app.cli --json catalog --catalog-file /absolute/path/catalog.json
../.venv/bin/python -m app.cli --json catalog --catalog-file /absolute/path/catalog.csv --include-cached-records
```

Local files must contain actual OMM-compatible JSON arrays or CSV rows, not
arbitrary Cartesian states. A local file defaults to **local-only** scope;
repeat `--catalog-group` to additionally select public groups. API selections
use `catalog_selection: {"groups": [...], "local_files": [...],
"include_cached_records": false}`; explicitly use `groups: []` for local-only.
Filenames are paths on the machine running the backend. This is a developer
backend, not an authenticated/untrusted-public filesystem service.

The measured default snapshot, fetched **2026-10-11 04:16:01 UTC**, contained:

| Verified CelesTrak GP group | Usable records |
| --- | ---: |
| `active` | 16,701 |
| `cosmos-2251-debris` | 588 |
| `iridium-33-debris` | 109 |
| `fengyun-1c-debris` | 1,979 |
| `visual` | 156 |
| Unique after deduplication | **19,505** |

There were **28** overlaps, zero ingestion rejects and zero failed downloads.
Snapshot SHA-256:
`d7dacf5368dbd802bef65e37215ab771fe892e04fa384a394220dab49684ee4e`.
Oldest/newest epochs were `2026-09-11T02:37:23.328192Z` /
`2026-10-12T17:36:20.007360Z`. Epoch warnings increased from 207 to 208–209 as
assembly time advanced; suitability is checked again at both screening endpoints,
so more records can be unsupported at the actual future interval.

These groups do **not** cover the full orbiting population. `active` excludes
many debris objects; named debris groups cover only their named populations.
Untracked/restricted objects and missing public elements are absent. No
`GROUP=ALL` or global completeness is invented. Newest usable epoch wins for
each canonical string NORAD ID, including six-digit IDs. Download refreshes obey
the existing two-hour GP limit; an HTTP failure halts that loader's network
queries until operator action/restart. Stale caches retain explicit provenance
and cannot silently yield a complete screen. A missing original counterpart is
added from the actual selected record with a new combined snapshot/checksum;
an empty catalog remains unavailable rather than becoming a one-object screen.
For exact snapshot reproduction, preserve the referenced cache payloads before
a refresh replaces them, or archive the actual OMM data and load it as a declared
local file. Source time windows eventually expire; checksums identify measured
datasets, not a promise that later live downloads reproduce identical numbers.

### Screening API and CLI

`POST /api/encounters/ENCOUNTER_ID/screen` accepts this shape (replace placeholders
with a real selected encounter's object and future burn timestamp):

```json
{
  "maneuvering_object_id": "NORAD_ID",
  "maneuver_time": "ISO_UTC_TIMESTAMP",
  "delta_v_rtn_m_s": [0.0, 0.1, 0.0],
  "hypothetical_capability_assumed": true,
  "alert_distance_km": 5,
  "post_tca_horizon_hours": 6
}
```

`encounter_id` is optional in this body because the URL supplies it; if supplied,
it must match. Inputs are illustrative, not predetermined scientific results.
The interval starts at burn time and ends at original TCA plus the configured
horizon. Default horizon is **6 hours**, maximum post-TCA horizon **24 hours**,
total screening/differential propagation at most **48 hours**, and epoch distance
at each endpoint at most **7 days**. The default **5 km** threshold is illustrative,
not a universal safe distance. The response preserves its actual applied value.

To extend an existing optimize JSON request, add:

```json
{
  "secondary_screening": {
    "policy": "REJECT_NEW_ALERTS",
    "alert_distance_km": 5,
    "post_tca_horizon_hours": 6,
    "max_finalists": 3,
    "timeout_seconds": 30,
    "total_timeout_seconds": 90
  }
}
```

This is an **additional field**, not the full optimize body. Omit it or use null
to retain the Phase 1 workflow. `GET /api/catalog/status` reports only the last
explicitly loaded base catalog; any separately added counterpart is identified
in that screening response's combined metadata.

CLI examples, from `backend/`:

```sh
../.venv/bin/python -m app.cli --json optimize \
  --encounter-id ENCOUNTER_ID --object-id NORAD_ID \
  --max-delta-v 0.2 --min-lead-minutes 15 --max-lead-hours 2 \
  --target-km 10 --objective MAXIMUM_CLEARANCE --assume-capability \
  --secondary-screening REPORT_ONLY --screen-max-finalists 3

../.venv/bin/python -m app.cli --json screen \
  --encounter-id ENCOUNTER_ID --object-id NORAD_ID \
  --maneuver-time ISO_UTC_TIMESTAMP --delta-v-rtn 0 0.1 0 --assume-capability \
  --alert-distance-km 5 --post-tca-horizon-hours 6
```

For a quick small-scope reproducible fixture run, supply
`--catalog-file tests/fixtures/gp_actual.json --post-tca-horizon-hours 0.01` and
select the actual fixture encounter 53495/34452 while its window remains future.
That file has just three actual GP records, **not** the broader screening catalog.
For genuinely larger runs, use the default groups or your own declared OMM files.
`--screen-max-objects`, `--screen-max-refinements`, `--screen-timeout-seconds`
and optimizer `--screen-total-timeout-seconds` bound workload. These are cooperative
budgets, not hard real-time guarantees; validation, catalog loading and the
unchanged primary optimization are measured separately from finalist screening.

### Status, classifications and selection policy

`SCREENED_WITHIN_COVERAGE` and `ALERTS_FOUND` mean computation completed within
the declared **partial** snapshot and interval. `INCOMPLETE` indicates skipped,
stale, rejected or failed records/refinements, or exhausted workload. An empty
catalog is `UNAVAILABLE`. An empty detection list from either unfinished status
does not establish that additional conjunctions are absent. `SAFE` is never a
scientific result status. `objects_screened` counts other objects successfully
considered in **both** nominal and modified searches; refined count is the union
of their refined objects within that intersection. Inspect skipped reasons.

Events are matched one-to-one by same object and time (default **120 s**), with
bounded nearby counterfactual minima when only one trajectory alerts. A newly
below-threshold maneuvered approach with baseline at/above threshold is
`NEW_CLOSE_APPROACH`; otherwise miss-distance decreases greater than **1 m**
are `WORSENED_CLOSE_APPROACH`, increases greater than **1 m** are
`IMPROVED_CLOSE_APPROACH`, and remaining changes are `UNCHANGED`. These numerical
rules are not orbital uncertainty estimates. Original-counterpart events are
distinguished from additional objects; closest-additional reporting excludes it.
`worsened`/`improved` count reported additional events, not all far-away catalog
trajectories. A closest-additional result can itself be above the alert threshold.

| Policy | Behavior |
| --- | --- |
| `REPORT_ONLY` | Preserve primary solutions and report actual screening; alternatives may remain unscreened |
| `REJECT_NEW_ALERTS` | Reject new additional below-threshold approaches; try the next genuine primary-ranked finalist |
| `REJECT_ALL_ALERTS` | Reject any additional maneuvered below-threshold approach; original counterpart stays under the primary objective |

No incomplete assessment passes any policy (`policy_passed: null`). REPORT_ONLY
can still display a primary candidate, but its separate secondary status remains
incomplete/unavailable. Strict policies return no solution if no fully assessed
candidate passes; status identifies unavailable/incomplete versus
`NO_ACCEPTABLE_SCREENED_SOLUTION`. Results show each actual assessment and the
selected original primary rank. There are no invented weighted risk scores.

### Differential method and limitations

Both numerical paths use the same GCRS reference, force model and impulse basis.
Position **and velocity** corrections are formed as
`numerical_maneuvered − numerical_zero_burn`, added to nominal SGP4 in GCRS, then
properly transformed back to TEME for batched catalog comparison. Zero impulse
recovers nominal SGP4 rather than treating numerical force-model drift as a burn.
Primary optimization's common numerical reference is retained for its finalists.

The one-vs-catalog broad phase uses NumPy segment closest approach, not just
pointwise sampled distances; allowance is `40 m/s² × dt² / 8` by default.
Potential events undergo bounded continuous-time refinement with multiple
local minima retained and shared-boundary duplicates rejected using actual
relative-velocity stationarity. This allowance and bounded search are heuristics,
not a mathematical completeness proof or physical uncertainty bounds.

Selected GP records may differ from bulk snapshots, including the original
counterpart. Epochs/checksums identify those differences; explicit warnings
prevent equating screening distances with primary-optimizer distances. Numerical
matched-baseline metrics and differential SGP4 screening metrics are also
different models, even when source records match. No covariance, calibrated Pc,
drag, higher harmonics, third-body forces, future real maneuvers, verified
spacecraft capability or safety beyond the stated interval is supplied.
The timing bucket `trajectory_generation` includes differential setup and other
overhead not attributed to propagation, coarse filtering, refinement or comparison.

### Actual Phase 2 measurements

Run the real pipeline and reproduce profiling with:

```sh
../.venv/bin/python -m app.secondary_benchmark --object-id 53495
../.venv/bin/python -m app.secondary_benchmark --object-id 53604
../.venv/bin/python -m app.secondary_benchmark --object-id 27056
../.venv/bin/python -m app.secondary_benchmark --object-id 53495 \
  --profile --screen-timeout-seconds 15 --max-objects 256
```

Benchmark defaults deliberately use a **36-second post-TCA** horizon, a 10–15
minute lead window, 30-second coarse steps and a 30-second screening budget.
They do **not** demonstrate a completed default six-hour screen. All three
real pipelines preserved the 123-evaluation primary search and screened one
finalist under REPORT_ONLY:

| Pair | Catalog load (s) | Catalog propagation (s) | Coarse (s) | Refine (s) | Screen total (s) | Optimize + screen (s) | Other objects considered / refined |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 53495 / 34452 | 1.254 | 0.826 | 0.129 | 16.912 | 18.818 | 20.569 | 19,123 / 11 |
| 53604 / 100033 | 2.469 | 1.088 | 0.144 | 27.791 | 30.081 | 31.991 | 12,440 / 16 |
| 27056 / 12107 | 2.405 | 1.013 | 0.215 | 10.812 | 13.629 | 15.168 | 19,222 / 8 |

All three returned **INCOMPLETE** with `policy_passed: null`: respectively 380,
357 and 282 endpoint-stale records; one SGP4 failure in the first/third; the
second additionally exhausted its runtime/refinement/comparison budget. The
third added its missing actual counterpart, yielding a **19,506-record** combined
screening snapshot. No additional 5 km alerts were detected in the evaluated
portion; these incomplete results do not establish absence of conjunctions.
The first run's calculated nearest additional encounter was 53619 at about
**14,498.456 m** (baseline **14,563.289 m**); the third's was 49101 at about
**210,926.043 m** (baseline **210,938.462 m**), both above threshold.

Primary optimized clearances were **10,903.135 m**, **64,211.586 m** and
**1,374.671 m** for those short-window requests. The third did not meet the
10 km target, correctly reported. Individual GP refresh changed the first
pair's selected counterpart epoch to `2026-10-10T17:30:09.069696Z`, whereas the
bulk group's record remained `2026-10-10T08:01:31.241568Z`; those snapshots and
different models explain different reported primary/screening distances.

Actual broader-catalog API and CLI demonstrations both succeeded with explicit
INCOMPLETE statuses at their 15-second limits (6,624 and 5,518 objects considered).
Exact scientific API/CLI agreement is separately tested using the same small
snapshot/window and sufficient budget; time-limited runs can cover different
amounts of work. Profiling a deliberately capped run identified Astropy frame
transforms as the refinement bottleneck (17.48 s cumulative, including primary
setup), while batched catalog propagation took about 0.03 s. Profiling overhead
changes runtime and workload; it does not justify weakening physical calculations.

The controlled adverse-case test uses actual central-gravity/J2 numerical
trajectories, not fabricated live alerts: original clearance **10.000 m →
1,024.273 m**, but third-object clearance **1,024.375 m → 9.999 m**. Exactly one
`NEW_CLOSE_APPROACH` is detected, including regression cases with true minima
just **0.2 ms** and **1.41 ms** from a shared coarse sample boundary.

## Phase 3: covariance-aware collision probability

Pc is the integral of a two-dimensional Gaussian encounter-plane density
over the disk of the explicitly supplied combined hard-body radius. Kessler
rotates each object's position covariance using **that object's own RTN/RIC
basis**, expresses both in one frame, forms relative covariance, and projects
perpendicular to relative velocity. The deterministic integrator uses a
covariance eigenbasis, a stable analytical normal-CDF inner integral, and
adaptive SciPy QUADPACK outer quadrature. It does not use Monte Carlo or
hardcoded scientific answers.

### Genuine historical NASA validation

Four unmodified CDMs and the original reference workbook are bundled from
NASA CARA commit `ce0f00722c56808755ee0adbe47a4e3d56439484`.
See [fixture provenance](backend/app/probability/reference_data/PROVENANCE.md).
These are **historical reference encounters, never live SOCRATES predictions**.
No current CelesTrak elements are used to reconstruct their states.

| NASA reference case | Precise published Pc2D | Largest observed relative difference |
| --- | --- | --- |
| Terra / Iridium 33 debris, 2021-03-24 | 0.021173811560368256 | 2.94e-13 |
| Terra / SL-16 debris, 2022-09-28 | 0.00010824948102737557 | 8.17e-13 |
| HST / Delta 2 rocket body, 2021-03-15 | 0.0006114793230828587 | 1.25e-10 |
| Swift / Jilin-01 Gaofen 2A, 2022-04-07 | 0.0023236849651128103 | 8.74e-12 |

Assertions use **2e-9 relative tolerance, no blanket absolute tolerance**;
quadrature convergence is also verified at 1e-11. The CDM Pc headers have only
four significant digits, so precise assertions use the workbook's Pc2D column.
NASA's local linear TCA correction is applied; the original inertial
covariances remain fixed over the actual sub-millisecond rounding correction.

NASA's benchmark script explicitly disables density cross-correlation
corrections even though the CDMs retain DCP metadata. Consequently the
reference adapter requires explicit **independent benchmark acknowledgment**
and warns that this is not operational risk for a correlated encounter.
Normal calculations do not discard known correlations.

From `backend/`, using your activated Python environment (or substitute
`../.venv/bin/python` for `python` with the repository-root environment):

```sh
python -m app.cli probability --list-reference-cases
python -m app.cli probability \
  --reference-case 000025994_conj_000037558_20210324_151047_20210323_154356 \
  --independent-benchmark
python -m app.cli --json probability \
  --reference-case 000025994_conj_000026980_20220928_223445_20220924_220647 \
  --independent-benchmark
```

The CLI shows published precise Pc, rounded CDM Pc, independently calculated
Kessler Pc, numerical difference, TCA correction and assumptions.

With the API running, historical reference evaluation is:

```sh
curl -sS http://127.0.0.1:8000/api/probability/calculate \
  -H 'Content-Type: application/json' \
  -d '{"reference_case":"000025994_conj_000037558_20210324_151047_20210323_154356","independent_benchmark":true}'
```

### Direct supplied geometry and covariance

`POST /api/probability/calculate` also accepts `kind` (`SUPPLIED` or `ASSUMED`),
aware `tca`, common inertial `frame`, `relative_position_m`,
`relative_velocity_m_s`, `covariance_primary_m2`, `covariance_secondary_m2`,
and positive `combined_hard_body_radius_m`. All matrices are 3x3 SI m².
Direct requests require covariances already in the stated common Cartesian
frame; RTN/RIC matrices instead require object states, provided by the live
encounter adapter or the NASA reader. EME2000/GCRF labels are never substituted
for GCRS. Existing Astropy TEME/GCRS conversions are used where supported.

Optional `correlation` is `UNSPECIFIED`, `INDEPENDENT` or `CORRELATED`;
`cross_covariance_m2` is Cov(primary,secondary) in the same frame and epoch.
When present, relative covariance is P1+P2−C12−C12ᵀ and the joint covariance
must be PSD. Known correlation without cross-covariance is unsupported.
Unspecified correlations carry a disclosed independence assumption.

The bundled input below is **synthetic illustrative geometry and explicitly
assumed uncertainties**, not observations or a fabricated current conjunction.
Its calculated scenario Pc is approximately 0.000678365289.

```sh
python -m app.cli --json probability --input-file examples/probability-direct.json
curl -sS http://127.0.0.1:8000/api/probability/calculate \
  -H 'Content-Type: application/json' --data-binary @examples/probability-direct.json
```

The result includes Pc, encounter-plane miss vector and covariance, combined
radius, numerical method/status, quadrature error estimate, conditioning,
assumptions and warnings. Invalid or missing critical request fields return
HTTP 422. Scientifically unsupported cases return explicit `UNSUPPORTED_MODEL`
and null Pc. Numerical underflow is explicitly identified, not evidence that
a collision is impossible.

### Live SOCRATES availability and scenarios

SOCRATES does not supply the object covariances needed for covariance-based
Pc. `MAX_PROB` remains separately available and is **not** true/calibrated Pc.
Actual verified live case `socrates-f3f9e438db4c8a81fa4b93e5` reported MAX_PROB
1.0 and Pc `UNAVAILABLE_NO_COVARIANCE`. Encounter IDs/data change over time.

```sh
python -m app.cli --json list --object-id 53495 --sort minimum_separation --limit 1
python -m app.cli probability --encounter-id ENCOUNTER_ID
python -m app.cli --json analyze --encounter-id ENCOUNTER_ID --probability
curl -sS http://127.0.0.1:8000/api/encounters/ENCOUNTER_ID/analyze \
  -H 'Content-Type: application/json' -d '{"probability_analysis":true}'
```

The optional analysis response adds `probability_analysis` with:

- `probability_status`: `CALCULATED_FROM_SUPPLIED_COVARIANCE`,
  `SCENARIO_WITH_ASSUMED_COVARIANCE`, `UNAVAILABLE_NO_COVARIANCE`,
  `UNAVAILABLE_INVALID_COVARIANCE` or `UNSUPPORTED_MODEL`;
- `socrates_max_probability`: actual source metric, separately preserved;
- `calculated_pc`: null when unavailable or unsupported;
- assumptions, warnings, covariance treatment, TCA/frame and numerical details.

Live covariance-file/API input contains `kind`, `primary` and `secondary`
records (`matrix_m2`, explicit `frame`, aware `epoch`), and
`combined_hard_body_radius_m`. Optional object IDs are checked against the
selected pair. Both epochs must equal **the analyzed TCA** returned by the
baseline request; an original/published TCA is not silently substituted.
Covariance propagation is unavailable. Use only your own supplied matrices or
explicit assumptions; Kessler generates none automatically.

```sh
python -m app.cli probability --encounter-id ENCOUNTER_ID --covariance-file uncertainty.json
```

For the API, put the same object under `probability_inputs` in the analyze
request. `kind: "ASSUMED"` produces the exact label:
`ILLUSTRATIVE — USER-SUPPLIED UNCERTAINTY ASSUMPTIONS.`
`SUPPLIED` identifies user-supplied covariance, not verified provenance,
covariance realism or operational calibration.

### Maneuver comparisons: fixed covariance only

Add `fixed_covariance: true` to a copy of the live covariance input file and
use it as `--probability-scenario-file` on the existing `simulate` command,
or as `probability_scenario` in the simulate API body. The original covariance
epoch must match `sgp4_reference.calculated.tca` (the original analyzed TCA).
Existing burn inputs and capability acknowledgment are still required.

```sh
python -m app.cli --json simulate --encounter-id ENCOUNTER_ID --object-id NORAD_ID \
  --maneuver-time FUTURE_UTC_TIMESTAMP --delta-v-rtn 0 0.1 0 --assume-capability \
  --probability-scenario-file fixed-uncertainty.json
```

The original per-object RTN matrices are transformed once, then frozen in
GCRS—not reoriented along a changed orbit as if propagated. The existing
matched numerical baseline and post-burn trajectories provide separate actual
TCA/relative geometry. `probability_comparison` reports original/published,
baseline and modified TCAs, covariance epoch/treatment, offsets, baseline Pc,
modified scenario Pc and delta Pc. **Both probabilities are illustrative**,
even if original covariance was supplied, because its validity at a changed
TCA is not established. No Pc-based search or default objective change exists.

### Exact assumptions, limitations and runtime

The model assumes short rectilinear relative motion, stationary Gaussian
position uncertainties, compatible common-frame/epoch SI states and matrices,
and an explicitly supplied combined spherical collision radius. Independence
is assumed only when unspecified or explicitly selected; established
correlations require cross-covariance. Velocity uncertainty, uncertainty
propagation, execution error, covariance realism, non-Gaussian tails and object
shape/orientation are not modeled. Instantaneous inputs cannot prove physical
rectilinear applicability; known long-duration/curved cases must set
`model_applicable: false` and are unsupported. No 3D/long-term Pc is provided.

Invalid covariance is never repaired by arbitrary eigenvalue clipping.
Zero/near-zero relative velocity, singular projected covariance and projected
condition number above 1e12 are unsupported. PSD symmetry/roundoff tolerance
is documented in the covariance module. Numerical accuracy is **quadrature
accuracy only**, not input/frame roundoff or a physical confidence bound.
No result is a flight command or operational safety guarantee.

Actual-machine benchmark: 30 calculations per NASA case (120 total), median
**1.32–1.66 ms**, 95th percentile **1.90–3.04 ms**, excluding import, parsing,
frame conversion and transport. Results depend on hardware/load. Reproduce:

```sh
python -m pytest tests/test_probability_reference.py -v -s
python -m pytest tests/test_probability_end_to_end.py -v -s
python -m pytest -q --maxfail=1
```

The end-to-end tests cover actual NASA CLI processes and uvicorn HTTP requests,
live SOCRATES/GP geometry, illustrative anisotropic uncertainty and maneuver
comparison, and existing clearance optimization plus secondary screening.
Partial catalog coverage/time limits still produce INCOMPLETE screening,
never a safety pass. Final checkpoint totals are recorded in `CHECKPOINTS.md`.

## Phase 4: atmospheric drag and orbital persistence

Backend-only research calculations using **NRLMSIS 2.1**, explicitly selected
through **pymsis 0.12.0**, real CelesTrak space weather and actual selected GP
initial states. The separate long-horizon propagator shares the existing central
gravity/J2 equations; it does not replace the maneuver simulator or optimizer.
No frontend, debris-cleanup ranking, ground-impact model or Pc-based search.
All **ten Phase 4 checkpoints passed**, including the authorized performance
correction. Final full suite: **397 passed, 2 upstream warnings in 529.01 s**,
all 302 Phase 3 tests plus 95 Phase 4 tests, with zero failures/skips/deselections.
Checkpoint history, authorized corrections and verification are in
`CHECKPOINTS.md`.

### Inputs, source coverage and output meaning

Supply either all three of mass (kg), area (m²), Cd, or an explicit Cd*A/m
(m²/kg). Missing values are never filled in; SGP4 BSTAR is not converted into
physical properties. Parameters must identify `USER_SUPPLIED` or
`HYPOTHETICAL_ASSUMPTION`. CLI example inputs additionally require
`--assume-properties` and are always labeled hypothetical.

The observed source is the actual CelesTrak `SW-All.csv` snapshot. The verified
snapshot contains **25,436 rows**, 1957-10-01–2041-10-01; last observed solar flux
**2026-10-10**, daily solar forecast **2026-10-11–2026-11-24**. Records after
2026-12-01 are monthly solar forecasts, **not complete daily model forcing**.
These dates are snapshot-specific, not a permanent coverage promise. Inspect
the status endpoint for the current source/cache timestamp and checksum.
Weather refresh is bounded to six hours; valid stale data retain explicit
provenance if refresh fails. As-of research requires an archived snapshot;
today's retrospective data are not silently treated as forecasts issued earlier.

MSIS receives previous-day Earth-distance F10.7, the modeled date's centered
81-day average and the seven-component storm-time Ap history. Solar qualifiers
and geomagnetic metadata limitations remain explicit; centered averages can
include predictions. No implicit pymsis downloads or default solar values.

Weather treatments:

- `SOURCE_ONLY` (default): unavailable forcing produces an explicit failure,
  never silent extrapolation or substitution.
- `HYPOTHETICAL_CONSTANT`: explicitly supply nominal F10.7 and Ap; no weather
  download is needed, and the result is a user-assumed scenario, not a forecast.
- `SOURCE_WITH_EXPLICIT_FALLBACK`: use source forcing where usable, otherwise
  the supplied hypothetical F10.7/Ap; each forcing sample discloses its origin.

`COMPARE` runs three actual trajectories: LOW_DRAG with a constant 80-sfu/Ap4
history, NOMINAL using the selected weather treatment, and HIGH_DRAG with
220-sfu/Ap40. These are illustrative environmental histories, not density
multipliers or statistical confidence bounds. Labels do not guarantee ordering
for arbitrary real storm conditions. Optional minimum/maximum Cd*A/m inputs
must bracket the nominal ratio; failed scenarios remain visible.

Results include the actual initial state/GP epoch, assumed properties, sampled
geodetic altitude, density, central and total-J2 specific energy, osculating
elements, event status, scenario envelope, source checksum and numerical settings.
Band occupancy is **piecewise-linear instantaneous WGS84 geodetic sample altitude**,
not perigee/apogee categories. Default bands are 120–250, 250–500 and 500–1000 km;
unclassified time is explicit. Occupancy is a sample-based approximation.

### API examples

Start the API with the existing command above. These are **hypothetical example
properties, not measured ISS properties**:

```sh
curl 'http://127.0.0.1:8000/api/space-weather/status?load=true'
curl -X POST http://127.0.0.1:8000/api/objects/25544/persistence \
  -H 'Content-Type: application/json' \
  -d '{"horizon_days":1,"scenario_mode":"COMPARE","aerodynamic_properties":{"input_category":"HYPOTHETICAL_ASSUMPTION","mass_kg":100,"area_m2":1,"drag_coefficient":2.2}}'
curl -X POST http://127.0.0.1:8000/api/objects/25338/decay \
  -H 'Content-Type: application/json' \
  -d '{"horizon_days":1,"aerodynamic_properties":{"input_category":"HYPOTHETICAL_ASSUMPTION","cd_area_over_mass_m2_kg":0.022}}'
curl -X POST http://127.0.0.1:8000/api/atmosphere/density \
  -H 'Content-Type: application/json' \
  -d '{"timestamp":"2026-10-11T08:40:37Z","latitude_deg":0,"longitude_deg":0,"altitude_m":400000}'
```

Update the density example's aware UTC timestamp for the desired modeled time
within usable source coverage. Optional `space_weather` accepts a complete
`WeatherForcing` model; see `/docs`. Optional `start_time` selects the orbit's
initial epoch, restricted to seven days from the GP epoch. Omit properties to
receive `INSUFFICIENT_OBJECT_PROPERTIES`, not a guessed calculation.

Both object routes return `PersistenceAnalysis`; per-scenario boundary status
is one of `BOUNDARY_REACHED`, `NOT_REACHED_WITHIN_HORIZON`,
`INSUFFICIENT_OBJECT_PROPERTIES`, `INSUFFICIENT_ENVIRONMENT_DATA`,
`INITIAL_STATE_UNSUPPORTED`, `NUMERICAL_FAILURE`, `MODEL_OUT_OF_VALIDITY`.
Comparison status is COMPLETE/PARTIAL/UNAVAILABLE. No-crossing/failed times
are null. Invalid requests return 422; unavailable GP/direct-density sources
return 503. Missing scenario weather is retained as an explicit per-scenario
INSUFFICIENT_ENVIRONMENT_DATA status rather than a fabricated trajectory.

### CLI examples

From `backend/`, using the root virtual environment:

```sh
../.venv/bin/python -m app.cli persistence
../.venv/bin/python -m app.cli --json space-weather --load
../.venv/bin/python -m app.cli --json persistence --object-id 25544 \
  --mass-kg 100 --area-m2 1 --drag-coefficient 2.2 --assume-properties \
  --horizon-days 1 --scenario-mode COMPARE
../.venv/bin/python -m app.cli --json decay --object-id 25338 \
  --cd-area-over-mass .022 --assume-properties --horizon-days 1
../.venv/bin/python -m app.cli --json persistence --object-id 25544 \
  --cd-area-over-mass .022 --assume-properties --horizon-days 1 \
  --weather-mode HYPOTHETICAL_CONSTANT --nominal-f107 150 --nominal-ap 15
```

The first command interactively prompts for ID, displays GP name/epoch, and
requests hypothetical physical inputs, horizon and scenario choice. No-argument
CLI behavior still runs the original collision-avoidance workflow. Global JSON/
cache options precede commands. `--boundary-km` defaults to 120; `--help` lists
ballistic range, explicit fallback and output-sampling options.

### Numerical model, limits and verification

SGP4 WGS72 supplies the initial TEME position/velocity, actually transformed to
GCRS with Astropy. The DOP853 integrator uses shared WGS84 central gravity/J2,
plus −½ρ(Cd*A/m)|v−ω×r|(v−ω×r), with atmospheric co-rotation at
7.292115e-5 rad/s. Actual geographic density coordinates/rotation axes use
time-varying GCRS→ITRS orientation, validated SO(3) interpolation at ≤20-minute
spacing and ERFA WGS84 geodetic conversion. Density is calculated by real MSIS
at every force evaluation, **not interpolated**. The gravity pole remains fixed
at the initial epoch, explicitly preserving the shared existing force convention.

Default tolerances are rtol 1e−9, position atol 1e−4 m, velocity atol 1e−7 m/s,
maximum integration step 120 s, output spacing 600 s and propagation budget 180 s.
Horizon is bounded to 90 days; large/difficult runs may explicitly exhaust the
budget. Initial altitude must be above the configured cutoff and ≤1000 km.
The default event is a terminal descending **120-km WGS84 geodetic boundary**,
configurable 80–500 km. Numerical trial stages can bracket below the cutoff,
but no returned trajectory extends past it; model trial domain is 80–1000 km.
This is **not ground impact, ablation or an operational reentry date**.

Verified boundary root **1310.210038 s** agreed with independent existing
numerical dynamics plus direct Astropy/brentq to <0.002 s. Three-hour controlled
trajectory refinement changed final position by **4.23e−5 m**; one-day actual
GP/weather/MSIS refinement by **0.178 m**. These quantify numerical convergence,
not physical accuracy. Optimized drag matched independent NumPy cross-product
results exactly across 200 states; unchanged actual-MSIS scalar integration also
matched the optimized path. No tolerances, step caps or timeout were relaxed.

Initial GP errors, unknown attitude/aerodynamics, omitted active maneuvers,
winds, higher harmonics/third bodies, fixed gravity pole, offline predictive
Earth orientation and unknown long-term solar activity limit fidelity. The ISS
example is a **passive hypothetical scenario**, not an ISS operational forecast.
J2 makes osculating semimajor axis oscillate; a higher endpoint does not negate
negative total-energy change. Period-window sample means also depend on sampling
phase and overlap on short horizons; they are not precise secular decay rates.
No-crossing means only "not reached within this modeled horizon", not infinite
lifetime. Covariance/physical uncertainty is not propagated or statistically
calibrated; scenario bounds are not confidence intervals.

### Actual-machine benchmarks and modules

Successful focused run (2026-10-11 04:40:37 EDT / 08:40:37 UTC): actual ISS
initial altitude 429.151 km and NOAA 15 796.865 km, both from genuine GP.
Hypothetical Cd*A/m=.022. One-day modeled total-energy changes were
−703.525 J/kg / −3.669 J/kg, respectively; neither crossed the boundary.
ISS 30 days modeled −14,321.601 J/kg, not observed decay.
LOW/source-NOMINAL/HIGH one-day losses were 240.931/703.525/2915.749 J/kg;
doubling Cd*A/m with unchanged source weather produced 1409.022 J/kg loss.

| Measurement | Actual wall time |
| --- | --- |
| Cached real weather load/parse | 0.707s |
| 100 actual MSIS density evaluations | 0.00575s |
| 100 direct / prepared coordinate evaluations | 0.5365s / 0.00127s |
| ISS one-day / seven-day / thirty-day workflow | 4.80s / 25.37s / 110.15s |
| NOAA15 one-day workflow | 5.40s |
| Three one-day scenarios | 12.42s |
| Actual HTTP decay / persistence, .01-day horizon | 1.450s / 0.635s |

These depend on hardware/load and include service overhead where labeled.
An earlier thirty-day run exhausted 180 s; authorized removal of redundant
coordinate/validation work resolved that benchmark without changing model,
solver settings or budget. Details and original failure remain in CHECKPOINTS.

New modules: `data/space_weather.py` (source/cache), `physics/atmosphere.py`
(MSIS/forcing/coordinates), `physics/drag.py` (validated physical force),
`physics/decay.py` (numerical evolution), `physics/boundary.py` (event/status),
`physics/persistence_scenarios.py` (explicit uncertainty scenarios),
`persistence.py` (real-object service/metrics), `api/persistence_schemas.py`,
and `persistence_benchmark.py`. Existing routes/CLI gained additive commands.

Reproduce measurements and verification from `backend/`:

```sh
../.venv/bin/python -m app.persistence_benchmark
../.venv/bin/python -m app.persistence_benchmark --profile
../.venv/bin/python -m pytest tests/test_decay_performance_fix.py tests/test_persistence_end_to_end.py -v -s --maxfail=1
../.venv/bin/python -m pytest -q --maxfail=1
```

Profiling itself adds runtime, so profiled timings are not interchangeable with
the unprofiled benchmark; computation limits remain explicit. Live tests require
source access. Full regression also includes genuine NASA Pc fixtures, live
SOCRATES/GP, optimization and secondary screening; incomplete catalog coverage
still cannot yield a safety guarantee.
