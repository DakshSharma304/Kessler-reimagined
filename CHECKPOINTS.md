# Implementation checkpoints

The user's explicit instruction takes precedence over the pasted task's
fix-and-continue wording: execute each checkpoint, record actual results,
and stop on the first failure with evidence and a likely cause.

Current status: **all 13 checkpoints PASSED**. Final verification produced
**108 passed, 2 warnings in 109.85 seconds**, followed by a successful live
interactive CLI demonstration and standalone benchmark. Failure entries below
are historical: work stopped at each failure, then resumed after user approval;
the source-access and object-response blockers are resolved.

## Checkpoint 1 — Initialize a runnable backend

Status: PASSED on Python 3.12.14.

- Installation: `python3.12 -m venv .venv` and
  `.venv/bin/python -m pip install -r backend/requirements.txt` completed
  successfully from the repository root.
- Check: `cd backend && ../.venv/bin/python -m pytest -v`.
- Actual result: **4 passed in 0.56 seconds**, one upstream Starlette/AnyIO
  deprecation warning.
- Imported every initialized application module.
- Launched a real uvicorn subprocess; `/api/health` returned HTTP 200 and
  exactly `{"status":"ok","service":"Kessler","version":"0.1.0"}`.
- Validated the Pydantic response and generated OpenAPI health schema.
- `../.venv/bin/python -m pip check`: no broken requirements found.
- The test server was terminated after validation.

## Checkpoint 2 — SOCRATES ingestion source prerequisite

Status: FAILED / BLOCKED. Implementation stopped as the user requested.

- Required documentation:
  `https://celestrak.org/SOCRATES/socrates-format.php`.
- Required actual CSV:
  `https://celestrak.org/SOCRATES/sort-minRange.csv`.
- Both requests failed with curl exit 56:
  `CONNECT tunnel failed, response 403`.
- Retrying outside the filesystem sandbox produced the same failure.
- Actual checkpoint command from `backend/`:
  `../.venv/bin/python -m pytest tests/test_socrates_live.py -v -s`.
- Actual result: **2 failed in 0.03 seconds**. Both tests fail at the download
  assertion, before parsing or examining any source contents.
- Network configuration inspection confirms restricted egress with no custom
  or preset `celestrak.org` allowance. The likely cause is rejection by the
  environment's network proxy before a connection to CelesTrak is established.
- Actual encounters retrieved: **0**. No previously downloaded orbital fixtures
  are present. No external encounter data has been invented.
- CSV parsing, typed encounters, unit conversion, timestamp conversion,
  duplicate handling, and caching checks remain **unrun**. Stage 2 is incomplete.
- Required next action: allow `celestrak.org` in the cloud environment's network
  settings, then retry the source tests before continuing implementation.

### Authorized network correction and retry

- The user requested fixing the 403 and retrying.
- A diagnostic HEAD request returned `HTTP/1.1 403 Forbidden` from `server:
  envoy` while opening the HTTPS CONNECT tunnel. This supports a network-proxy
  rejection before any request reaches the SOCRATES application.
- Read the existing network configuration and preserved its package-manager
  presets. Added only `celestrak.org` to the custom allowed domains.
- The configuration tool confirmed `status: saved` and `requires_publish: true`.
  Saving the draft does not update the running network policy or publish it.
- Reran `../.venv/bin/python -m pytest tests/test_socrates_live.py -v -s`:
  **2 failed in 0.03 seconds**, still at the HTTPS CONNECT tunnel with HTTP 403.
- The available tools can save the draft, but cannot apply or publish it.
  Required action: review and save the prepared network change in environment
  settings, then publish the environment. Retry the source checkpoint after
  the updated policy is applied. Stage 2 remains blocked and incomplete.

### Retry after the user reported a settings change

- Reran the actual two live source tests: **2 failed in 0.03 seconds**.
- A separate HEAD request outside the sandbox still returned `HTTP/1.1 403
  Forbidden` from `server: envoy` during HTTPS CONNECT, with curl exit 56.
- Read configuration again: the `celestrak.org` allowance is present in draft
  revision 1; the returned draft ID and base configuration version are unchanged.
  Draft metadata does not establish which policy the running proxy has applied.
- Likely cause: the saved allowance has not reached the active environment,
  or the active proxy is not honoring it. This remains a network-policy blocker,
  not an HTTP response from CelesTrak or a CSV parsing failure.
- Stopped without progressing to later stages. The prepared allowance needs to
  be applied through environment settings/publication before another retry.

## Checkpoint 2 — Successful restart and full ingestion validation

Status: PASSED after the environment finished restarting.

- Live source prerequisite retry: **2 passed in 7.45 seconds**;
  **195,282** actual CSV rows downloaded.
- Verified the actual SOCRATES format documentation and published methodology.
  CelesTrak runs SOCRATES three times daily; refresh interval is eight hours.
- Implemented validated encounters, SI unit normalization, UTC parsing, stable
  pair-plus-TCA IDs, source timestamp/checksum provenance, malformed-row isolation,
  duplicate detection, persistent atomic caching, and last-valid-cache fallback.
- Saved five unmodified actually downloaded rows as an offline fixture with
  source provenance. Offline fixtures are labeled historical predictions.
- Command from `backend/`: `../.venv/bin/python -m pytest -v -s`.
- Actual result: **23 passed in 19.78 seconds**, one upstream deprecation warning.
- Full real ingestion: **195,282 valid encounters**, **0 invalid rows**,
  **0 duplicate rows**. Repeated access reuses the in-memory dataset.
- Numerical units, UTC, string and six-digit IDs, invalid rows/datasets,
  repeat encounters, persistent cache reuse, failed-update preservation,
  retry throttling, and explicit unavailable responses were exercised.

## Checkpoint 3 — Rank and select encounters

Status: PASSED.

- Implemented upcoming-only filtering, MAX_PROB/minimum-separation/time sorts,
  case-insensitive name and either-object catalog-ID filters, stable ID lookup,
  clear missing-ID and unavailable-source exceptions, and quality warnings.
- Default screening order: valid source first, no seven-day source-age caution
  first, then descending MAX_PROB, separation and TCA. This is a transparent
  lexicographic ordering, not a calibrated combined danger score. The age
  threshold is a screening caution, not a universal orbit validity guarantee.
- Command: `../.venv/bin/python -m pytest tests/test_discovery.py tests/test_api.py
  tests/test_startup.py -v -s` from `backend/`.
- Actual result: **16 passed in 7.13 seconds**, one upstream warning.
- Selected actual upcoming encounter **53495 / 34452** from the full real cache.
- Measured repeated indexed lookup: **0.000218 seconds**.
- Both participating IDs remain present; GP availability is explicitly
  unverified until orbital retrieval in the next stage.

## Checkpoint 4 — Retrieve orbital elements

Status: PASSED.

- Implemented GP JSON parsing with documented EARTH/TEME/UTC/SGP4 defaults,
  element validation, matching requested IDs, six-digit support, SGP4
  initialization, two-hour persistent caching and explicit unavailable errors.
- Both real objects in the selected encounter were obtained: **53495 / 34452**.
  Their actual GP epochs are **2026-10-10 13:23:52.331712 UTC** and
  **2026-10-10 08:01:31.241568 UTC**. Catalog **100033** was also downloaded
  and successfully initialized via OMM-compatible JSON.
- Conservative seven-day epoch-distance limit is explicit; no orbit is
  substituted when requested data are missing, invalid, mismatched or unsuitable.
- Current GP elements may differ from SOCRATES source elements; the distinction
  is retained in suitability warnings.
- Corrected SOCRATES refresh interval to **11 hours** after reading the newer
  usage policy at `https://celestrak.org/usage-policy.php`. It supersedes the
  older general page's three-runs-per-day description. Source errors now halt
  queries in that client until operator action; live CSV tests reuse the cache.
- Command from `backend/`: `../.venv/bin/python -m pytest tests/test_celestrak.py
  tests/test_socrates.py tests/test_socrates_live.py tests/test_discovery.py
  tests/test_api.py tests/test_startup.py -v -s`.
- Actual result: **51 passed in 23.67 seconds**, one upstream warning.
- Actual cached GP lookup: **0.000026 seconds**. No new full SOCRATES CSV download
  was needed for these checks.

## Checkpoint 5 — SGP4 positions and trajectories

Status: PASSED.

- Implemented deterministic SGP4 single-state and trajectory propagation using
  the installed library, TEME labels, UTC times, SI units and explicit errors.
- Actual GP states are finite and have plausible orbital position/velocity;
  different timestamps change the position; invalid inputs are rejected.
- Verified case 00005 against Vallado/CSSI output in the trusted library's
  `sgp4/tcppver.out`, using **1 mm** position and **1 micrometre/s** velocity
  tolerances against the rounded reference values.
- Command: `../.venv/bin/python -m pytest tests/test_propagation.py
  tests/test_api.py tests/test_startup.py -v -s` from `backend/`.
- Actual result: **11 passed in 2.04 seconds**, one upstream warning.
- Actual GP benchmark: **100 states in 0.002650 seconds**,
  **1,000 states in 0.023205 seconds**.

## Checkpoint 6 — Recalculate selected encounter

Status: PASSED.

- Implemented squared-separation sampling in a local ±300-second window,
  bounded refinement of bracketed minima, relative state calculations,
  search-boundary reporting, epoch checks and explicit frame/time compatibility.
- Preserved original SOCRATES and independently computed SGP4 predictions.
- Command: `../.venv/bin/python -m pytest tests/test_encounters.py
  tests/test_propagation.py tests/test_api.py -v -s` from `backend/`.
- Actual result: **17 passed in 9.10 seconds**, one upstream warning.
- Actual selected encounter **53495 / 34452**: published separation **7.000 m**;
  current-GP SGP4 recalculation **9,330.205 m**, refined TCA
  **2026-10-13 05:09:03.463408 UTC**, runtime **0.005716 seconds**.
- Source/model disagreement is explicitly flagged. This is not scientific
  agreement with the published SOCRATES prediction; newer element sets differ.
- Synthetic identical/crossing geometry, relative position/velocity, refinement
  quality, interval bounds, real predictions and disagreement handling passed.

## Checkpoint 7 — One actual impulsive maneuver

Status: PASSED.

- Implemented TEME→GCRS position/velocity transformation with Astropy, RTN
  velocity impulses, DOP853 central-gravity/J2 integration, matched zero-burn
  trajectories for both objects, and dynamic closest-approach refinement.
- Pre-burn samples use the unmodified trajectory even when the burn occurs
  inside the local search window. Position is continuous; only velocity jumps.
- Requires an explicit hypothetical capability assumption, participating object,
  future burn time before both published/recalculated TCA and ≤48-hour lead.
- The original SGP4/SOCRATES predictions remain separately labeled references.
  Dynamics assumptions and absent secondary-conjunction assessment are reported.
- Command: `../.venv/bin/python -m pytest tests/test_maneuvers.py
  tests/test_encounters.py tests/test_api.py -v -s` from `backend/`.
- Actual result: **17 passed in 18.11 seconds**, two warnings (upstream
  deprecation and Astropy cache-directory access; installed offline IERS data
  were used and the calculations completed).
- Actual 53495/34452 maneuver: +0.1 m/s transverse impulse one hour before
  published TCA; matched zero-burn clearance **9,553.506 m**, post-burn
  clearance **10,105.911 m**, change **+552.405 m**.
- Measured simulation runtime **0.135274 seconds** (after initial frame setup).
- Zero-burn equality, positive/negative/different-direction impulses, earlier
  burns, invalid timing, repeated inputs and tighter integration tolerances
  passed. Tight-tolerance separation difference rounds to **0.000000 m**.

## Checkpoint 8 — Hypothetical maneuver constraints

Status: PASSED.

- Added strict Pydantic constraints, two documented objectives, explicit assumed
  maneuver capability, participating-object/encounter validation, future burn
  windows, direct delta-v budgets and optional ideal rocket-equation conversion.
- Fuel conversion requires initial mass, available propellant mass and Isp;
  otherwise no fuel estimate is fabricated. Effective budget is the smaller
  of the direct budget and supplied-propulsion ideal delta-v capability.
- Command: `../.venv/bin/python -m pytest tests/test_constraints.py
  tests/test_api.py -v` from `backend/`.
- Actual result: **15 passed in 1.33 seconds**, one upstream warning.
- Negative/nonfinite budgets, invalid windows/targets/objectives, omitted or
  inconsistent propulsion inputs, wrong objects and past burns were rejected.
- Analytical rocket-equation and JSON serialization checks passed.

## Checkpoint 9 — Bounded dynamic optimizer

Status: PASSED.

- Implemented actual RTN candidate simulations, common numerical reference for
  all burn times, hard budget/window validation, objective-specific selection,
  deterministic coarse search and local time/magnitude/direction refinement.
- MINIMUM_DELTA_V selects the lowest evaluated effort meeting the target.
  MAXIMUM_CLEARANCE selects greatest evaluated clearance within the hard budget
  and window, reporting honestly when the requested target is not met.
- Includes actually computed distinct effort/clearance alternatives when found,
  candidate counts, numerical failures, timing, model limits and partial status.
- Command: `../.venv/bin/python -m pytest tests/test_optimizer.py
  tests/test_maneuvers.py -v -s` from `backend/`.
- Actual result: **14 passed in 16.08 seconds**, one Astropy cache warning.
- Default benchmark: **123 candidates evaluated**, **123 feasible**,
  **0 numerical failures**, runtime **2.586 seconds**, status COMPLETE.
- Best evaluated clearance **10,796.958 m** at **0.200000 m/s** for the actual
  historical fixture encounter. This is not a global-optimum claim.
- Changed budgets/windows, target handling, numerical errors, reproducibility,
  no-feasible target and honest timeout/partial outcomes were tested.

## Checkpoint 10 — REST API

Status: FAILED. Stopped at this checkpoint as explicitly requested.

- Implemented health/status, encounter list/detail, analyze/simulate/optimize,
  and object endpoints with Pydantic schemas, shared cached sources, actual
  calculation functions, and clear 404/422/503 error handling.
- Command: `../.venv/bin/python -m pytest tests/test_api_engine.py
  tests/test_api.py tests/test_startup.py -v` from `backend/`.
- Actual result: **1 failed, 6 passed in 5.20 seconds**, two warnings.
- Failed test: `test_every_endpoint_runs_real_engine`, at its object-response
  assertion: `response.json()["elements"]["object_id"]` raises `KeyError`.
- Read-only diagnosis confirmed **HTTP 200** for `/api/objects/53495` with
  the correct actual catalog ID under **`elements.NORAD_CAT_ID`**.
- Confirmed the route has `response_model_by_alias=True`. GPElements uses OMM
  ingestion aliases such as `NORAD_CAT_ID`; FastAPI serializes them by default.
  The test expects normalized names such as `object_id`. This is a confirmed
  API response naming/contract mismatch, not a source-access or orbit-calculation
  failure.
- Likely correction: choose the documented normalized output convention for
  the objects endpoint, disable response alias serialization there, and rerun
  the complete checkpoint. No correction was made after the failure because
  the user instructed stopping and reporting first.
- Passing checks included invalid requests, unknown encounter 404, explicit
  scientific errors, changed valid HTTP optimization inputs, module imports,
  health schema, and actual uvicorn startup. The first endpoint-flow test stops
  before its successful analyze/simulate assertions and OpenAPI path-count
  assertion, so those checks remain unverified at this checkpoint.

## Subsequent checkpoint results

### Checkpoint 10 — Authorized correction and successful retest

- The user authorized fixing the response naming mismatch.
- Set `response_model_by_alias=False` on the object endpoint; OMM ingestion
  aliases remain unchanged and the HTTP response now exposes normalized fields.
- Reran the full checkpoint command: **7 passed in 6.92 seconds**, two warnings.
- All eight endpoint checks, actual analyze/simulate/optimize invocation checks,
  changed-input HTTP calculations, error cases, OpenAPI generation, imports,
  health and real uvicorn startup passed. Checkpoint 10 is now **PASSED**.

### Additional user-requested retry

Historical source-access retry, before the updated network policy took effect;
this is not a current blocker.

- Re-executed `../.venv/bin/python -m pytest tests/test_socrates_live.py -v -s`
  from `backend/`: **2 failed in 0.03 seconds**.
- Both URLs still fail with `CONNECT tunnel failed, response 403`, curl exit 56.
- The source prerequisite remains blocked at the network proxy. Stopped as
  requested; no later checkpoint was started.

## Checkpoint 11 — Terminal demonstration

Status: PASSED.

- Implemented `python -m app.cli` interactive selection, baseline display,
  spacecraft choice, explicit assumed capability, constraint prompts,
  optimization and actual result/limitation display.
- Added JSON `list`, `analyze`, `simulate`, and `optimize` commands with direct
  arguments, optional fuel inputs, bounded search settings and clear errors.
- Invalid menu/numeric answers are retried; missing/empty data, invalid
  constraints, unknown IDs and cancelled input are handled without fabrication.
- Command: `../.venv/bin/python -m pytest tests/test_cli.py
  tests/test_api_engine.py tests/test_api.py -v -s` from `backend/`.
- Actual result: **12 passed in 20.76 seconds**, two known warnings.
- Actual noninteractive subprocess loaded **195,282** encounters, selected the
  real upcoming case, ran **13 actual simulations**, and returned best evaluated
  clearance **10,786.510 m** using the smaller two-time/one-magnitude test search.
- The interactive path also executed actual baseline and full optimization
  using historical public-source fixtures and recovered from invalid answers.

## Checkpoint 12 — End-to-end verification

Status: PASSED.

- Command: `../.venv/bin/python -m pytest tests/test_integration.py
  tests/test_optimizer.py tests/test_encounters.py -v -s` from `backend/`.
- Actual result: **20 passed in 23.07 seconds**, one known Astropy warning.
- Three actual upcoming SOCRATES encounters were selected, both real GP records
  were retrieved, SGP4 baselines calculated, and JSON CLI optimization run twice
  per encounter with explicit hypothetical capability and changed budgets.
- Each request evaluated **13 actual candidates** using the bounded test search.
- All source/model discrepancies were reported, and both participating IDs
  remained correct. No orbit substitution or invented probability occurred.

| Actual object pair | Published separation (m) | Current-GP SGP4 (m) | Common numerical baseline (m) | Best at 0.1 m/s (m) | Best at 0.3 m/s (m) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 53495 / 34452 | 7.000 | 9330.205 | 9321.113 | 10051.843 | 11524.368 |
| 53604 / 100033 | 25.000 | 64069.627 | 64105.624 | 65677.230 | 68822.187 |
| 27056 / 12107 | 27.000 | 1202.567 | 1084.400 | 3079.545 | 7069.582 |

- Individual test searches took **0.313–0.355 seconds**.
- Source/GP failures, missing IDs, stale epochs, source/model discrepancy,
  expired windows, insufficient budget/unattainable target, failed numerical
  integration, optimization timeout and no-feasible results were tested.
- Starlink objects were selected for two cases, but propulsion capability was
  still explicitly assumed. The COSMOS case also requires that assumption;
  operational status does not establish propulsion capability.

## Checkpoint 13 — Performance and final review

Status: PASSED.

- Final review also aligned GP response serialization and the generated OpenAPI
  schema with normalized fields such as `object_id`. Uppercase OMM ingestion
  and the uppercase mapping supplied to SGP4 remain supported. A regression
  assertion checks the documented schema as well as the actual response.
- Full command from `backend/`:
  `../.venv/bin/python -m pytest -v -s --maxfail=1`.
- Actual result: **108 passed, 2 warnings in 109.85 seconds (0:01:49)**.
  No tests failed, skipped or were deselected.
- Includes all unit/integration tests, live API analyze/simulate/optimize smoke
  tests, actual uvicorn startup, CLI subprocesses, three real encounter pairs
  under changed budgets, trusted SGP4 vectors, maneuver consistency, optimizer
  constraints, numerical failures and time-budget handling.
- Loaded **195,282 valid SOCRATES encounters**, with **0 invalid rows** and
  **0 duplicates**. Live tests reused the real downloaded cache in accordance
  with source refresh limits; they did not substitute fabricated source data.
- Warnings: upstream Starlette/AnyIO deprecation and Astropy's read-only user
  cache directory. Frame transforms used installed offline IERS data.
- `../.venv/bin/python -m pip check`: **No broken requirements found**.

### Full live interactive CLI demonstration

From `backend/` (shell `pipefail` enabled):

```sh
printf '1\n1\nyes\n0.2\n2\n15\n10\n2\n' | ../.venv/bin/python -m app.cli
```

- Exit status **0**. Loaded the real source, displayed actual encounters,
  selected 53495/34452 and explicitly confirmed hypothetical maneuver capability.
- Constraints: maximum delta-v **0.2 m/s**, lead time **15 minutes to 2 hours**,
  target **10 km**, objective **MAXIMUM_CLEARANCE**.
- **COMPLETE**, **123 evaluated**, **123 feasible**, runtime **2.736 seconds**.
- Common matched zero-burn baseline: **9,321.113 m**.
- Best evaluated burn: **2026-10-13T03:09:03.882Z**, RTN impulse
  **(0.01990074380419979, 0.19900743804199786, 0) m/s**.
- Modeled clearance: **10,796.958199909179 m**; improvement:
  **1,475.845216447502 m**. The illustrative target was met numerically.
- A distinct computed zero-burn alternative and scientific limits were printed.
  Neither target attainment nor COMPLETE status certifies operational safety.

### Standalone actual-machine benchmark

Command from `backend/`: `../.venv/bin/python -m app.benchmark`; exit status **0**.
Machine: Python **3.12.14**, Linux **6.18.44**, glibc **2.41**.

| Actual operation | Seconds |
| --- | ---: |
| Initial cached-source parsing and indexing, 195,282 rows | 8.952407140 |
| Indexed encounter lookup | 0.000070595 |
| Cached orbital GP pair retrieval | 0.000009980 |
| SGP4 baseline encounter refinement | 0.005099470 |
| Single maneuver, including initial frame setup | 0.581133425 |
| 100 SGP4 states | 0.001613975 |
| 1,000 SGP4 states | 0.045160813 |
| Full default bounded optimization | 2.878021055 |

- Optimizer: **COMPLETE**, **123 evaluated**, **123 feasible**, **0 numerical
  failures**; independently reproduced the interactive example's best clearance.
- All specified indexed/cached calculation performance targets were met on this
  machine. Initial dataset loading is separate and is not claimed to be under
  one second. Measurements are not runtime guarantees.

### Final handoff and limits

Installation, API startup, CLI, test and benchmark commands, repository layout,
actual dataset count and calculated examples are documented in `README.md`.
The complete SOCRATES → selection → GP retrieval → propagation → closest
approach → maneuver simulation → bounded optimization → result path passed.

These are hypothetical nominal calculations, not flight commands or calibrated
collision probabilities. Source/current-GP disagreement is explicitly reported;
matched zero-burn drift is not attributed to the impulse. Propulsion capability
is assumed only with explicit input. Numerical convergence does not establish
physical certainty; secondary conjunctions are **not assessed**. No frontend or
out-of-scope product features were added.
