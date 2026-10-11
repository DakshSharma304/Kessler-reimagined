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
clearance optimizer and default API/CLI responses are preserved. No frontend,
decay model, cleanup optimization or extra dependencies were added.
All **nine Phase 3 checkpoints passed**. Final complete suite: **302 passed,
2 upstream warnings in 297.29 seconds**—all 197 prior tests plus 105 new tests,
with zero failed, skipped or deselected tests.

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
| GET | `/api/catalog/status` | Last explicitly loaded catalog metadata; no download |
| GET | `/api/encounters` | Upcoming encounters; `sort`, `limit`, `object_id`, `name` |
| GET | `/api/encounters/{id}` | Selected source encounter and quality warnings |
| POST | `/api/encounters/{id}/analyze` | Local SGP4 baseline refinement |
| POST | `/api/encounters/{id}/simulate` | Actual hypothetical impulsive simulation |
| POST | `/api/encounters/{id}/optimize` | Bounded search; optional `secondary_screening` settings |
| POST | `/api/encounters/{id}/screen` | Compare nominal and differential post-burn trajectories |
| GET | `/api/objects/{id}` | Selected GP record, epoch and provenance |
| POST | `/api/probability/calculate` | Supplied common-frame Pc or explicit NASA reference benchmark |

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
