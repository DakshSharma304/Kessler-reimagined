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

## Install

From the repository root:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
```

## Start the API

```sh
cd backend
../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The health endpoint is `GET /api/health`; interactive API documentation is at
`/docs`. The server does not fetch orbital data at startup.

| Method | Endpoint | Action |
| --- | --- | --- |
| GET | `/api/health` | Service health |
| GET | `/api/status` | Loaded-source/cache status; no live readiness claim |
| GET | `/api/encounters` | Upcoming encounters; `sort`, `limit`, `object_id`, `name` |
| GET | `/api/encounters/{id}` | Selected source encounter and quality warnings |
| POST | `/api/encounters/{id}/analyze` | Local SGP4 baseline refinement |
| POST | `/api/encounters/{id}/simulate` | Actual hypothetical impulsive simulation |
| POST | `/api/encounters/{id}/optimize` | Bounded candidate search and evaluated results |
| GET | `/api/objects/{id}` | Selected GP record, epoch and provenance |

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

```sh
cd backend
../.venv/bin/python -m pytest -v
```

The startup test launches uvicorn, makes an actual HTTP request, and terminates
only its own process.

Final verification: **108 passed, 2 warnings in 109.85 seconds**, with no failed,
skipped or deselected tests. The warnings concern an upstream Starlette/AnyIO
deprecation and a read-only Astropy cache; installed offline IERS data were used.
Full commands and measured results are recorded in `CHECKPOINTS.md`.

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
cache. Only individually selected objects are downloaded; missing or mismatched
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
supplied as a hypothetical assumption. Secondary conjunctions have not been
assessed. Published SOCRATES predictions, current-GP SGP4 predictions and matched
numerical zero-burn predictions are separately labeled; force-model drift is not
attributed to a maneuver.

SGP4 uses WGS72 and returns TEME states. Astropy transforms positions and
velocities to GCRS for DOP853 numerical integration with central Earth gravity
and J2 using WGS84 constants. The Earth pole is fixed at the reference epoch
over the modeled interval. RTN transverse is perpendicular to radial in the
orbital plane; it is not always exactly the eccentric-orbit velocity direction.
All optimizer candidates share a common numerical reference epoch and baseline.

The force model excludes drag, higher harmonics, third-body forces and future
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

No frontend, cleanup optimization, atmospheric decay, secondary screening,
authentication or operational spacecraft commands are implemented.
