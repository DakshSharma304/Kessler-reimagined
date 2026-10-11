# Implementation checkpoints

The user's explicit instruction takes precedence over the pasted task's
fix-and-continue wording: execute each checkpoint, record actual results,
and stop on the first failure with evidence and a likely cause.

Phase 1 status: **all 13 checkpoints PASSED**. Final verification produced
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

# Phase 2 — Secondary-conjunction screening

The explicit user instruction remains the hard gate: at the first failed
checkpoint, record the actual failure and likely cause, stop dependent work,
and request direction. Do not automatically fix past a failed checkpoint.

## Phase 2 checkpoint 1 — Verify and preserve Phase 1

Status: PASSED.

- Inspected README, the full historical checkpoint record, all API, propagation,
  frame, maneuver, optimizer and CLI interfaces, data/cache modules and existing
  tests. Actual reusable interfaces and extension boundaries are documented in
  `SECONDARY_SCREENING_DESIGN.md`.
- Preserved the clean working state at commit `714bfb5` using the local tag
  `phase1-before-secondary-screening`. No working engine code was changed.
- Full baseline command from `backend/`:
  `../.venv/bin/python -m pytest -v -s --maxfail=1`.
- Actual result: **108 passed, 2 warnings in 92.27 seconds**, exit **0**.
  All tests ran; no failed, skipped or deselected tests.
- Live-marked calculations used genuine cached public-source data, not a new
  external retrieval of every record. The SOCRATES documentation request did
  exercise current network access. Cached-data calculations do not establish
  current external GP integration success.
- Existing real-data API smoke and three-pair CLI integrations passed. Source
  contained **195,282** actual encounters; all numerical outcomes matched the
  preserved Phase 1 sample. Source/current-GP disagreement remained explicit.
- Existing full interactive demonstration command:
  `printf '1\n1\nyes\n0.2\n2\n15\n10\n2\n' | ../.venv/bin/python -m app.cli`
  with shell pipefail enabled; exit **0**, **123** evaluated/feasible candidates,
  **3.720 seconds**, baseline **9,321.113 m**, modified **10,796.958 m**.
- Existing standalone `../.venv/bin/python -m app.benchmark`: exit **0**.
  Catalog encounter load/index **7.077027 s**; indexed lookup **0.000064682 s**;
  cached GP pair **0.000009682 s**; baseline **0.006171 s**;
  single maneuver **0.658392 s**; full optimizer **3.322391 s**, COMPLETE,
  **123** evaluated/feasible, **0** numerical failures.
- Known warnings: upstream Starlette/AnyIO deprecation and read-only Astropy
  cache; installed offline IERS data were used successfully.

## Phase 2 checkpoint 2 — Broader catalog ingestion

Status: FAILED. Stopped at the first failed acceptance test as requested.

- Added catalog selection/snapshot/provenance models in `app/models/catalog.py`
  and a bulk/local/cached loader in `app/data/catalog.py`, reusing FileCache and
  GPElements. Selected public groups were verified against the actual current
  CelesTrak GP listing; no GROUP=ALL endpoint was invented. Coverage is PARTIAL.
- Extended the existing orbital source label to allow `Local OMM`, preserving
  the existing `CelesTrak GP` default and all Phase 1 calculations.
- Full checkpoint command from `backend/`:
  `../.venv/bin/python -m pytest -v -s --maxfail=1`.
- Actual result: **1 failed, 9 passed, 2 warnings in 9.80 seconds**, exit **1**;
  **120 tests collected**, with the remaining tests unrun after the hard stop.
- Failed test: `tests/test_catalog.py::test_csv_uses_same_validation_and_real_sgp4`.
  Expected three usable actual-source records after CSV round-trip; got **0**.
- Read-only diagnosis confirmed CSV yields `EPHEMERIS_TYPE='0'` (string), while
  JSON has `EPHEMERIS_TYPE=0` (integer). The existing GPElements field is typed
  `Literal[0]`, and Pydantic rejects the CSV string with `literal_error`:
  `Input should be 0 [input_value='0', input_type=str]`.
- Confirmed cause: the new catalog CSV ingestion does not normalize this
  integer-valued literal before using the existing strict GP validator. This
  is a CSV input-type mismatch, not an SGP4 mechanics or network failure.
- Likely correction: normalize the documented CSV EPHEMERIS_TYPE value to its
  integer form before validation, preserving strict rejection of unsupported
  ephemeris types. Do not relax the SGP4 model requirement or weaken the test.
- JSON multi-record parsing, canonical deduplication, invalid/missing record
  handling and the initial existing API checks passed before the failure.
- The actual bulk-download acceptance test, cache/local tests and full Phase 1
  checkpoint-2 regression run remain **unverified**. No broader-catalog usable
  record count or external bulk-integration success is claimed.
- No correction was made after the failure. Checkpoints 3–9 have not begun.
  Secondary screening is not implemented or claimed available.

### Checkpoint 2 — Authorized correction and successful retest

- User authorized the CSV integer conversion. The CSV ingestion boundary now
  converts EPHEMERIS_TYPE with `int()` before strict `GPElements` validation.
  JSON ingestion and the supported `Literal[0]` requirement are unchanged.
- Added five rejection regressions for unsupported, fractional, nonfinite,
  empty and malformed CSV ephemeris values; the original assertion was retained.
- Complete checkpoint/regression command:
  `../.venv/bin/python -m pytest -v -s --maxfail=1` from `backend/`.
- Actual result: **125 passed, 2 warnings in 103.65 seconds**, exit **0**.
  All original 108 tests and all 17 new catalog tests passed; none skipped.
- Actual external bulk ingestion used HTTP, not cached fixtures, for all five
  verified public groups: active **16,701**, COSMOS 2251 debris **588**,
  IRIDIUM 33 debris **109**, FENGYUN 1C debris **1,979**, visual **156**.
- Combined snapshot: **19,505 unique usable orbital records**, **28 duplicates**,
  **0 rejected records**, **0 failed source datasets**. Includes real spacecraft,
  debris, rocket bodies and six-digit catalog IDs beyond the selected pair.
- Snapshot SHA-256:
  `d7dacf5368dbd802bef65e37215ab771fe892e04fa384a394220dab49684ee4e`.
- Coverage is **PARTIAL**, never complete. **207** retained records have epochs
  more than seven days from assembly time; overall freshness is therefore STALE
  despite successful fresh downloads. Those records must be explicitly handled
  by screening validity checks, not silently treated as current.
- Second loader reused all five persistent caches without a repeat download
  and reproduced the identical snapshot checksum. Local OMM JSON/CSV parsing,
  individual GP cache loading, failure halting, stale-cache preservation,
  unavailable catalogs, deduplication and provenance tests all passed.
- Checkpoint 2 is now **PASSED**. Checkpoints 3–9 are not yet verified.

## Phase 2 checkpoint 3 — Screening contracts and windows

Status: PASSED.

- Added strict typed requests, settings, window, secondary-event/result schemas
  and screening policies in `app/models/screening.py`.
- Default interval is the maneuver time through published TCA + **6 hours**;
  configurable positive post-TCA horizon is capped at **24 hours**, and the
  entire numerical screening interval is capped at **48 hours**. Future burn,
  participating object, encounter identity, aware timestamps and finite RTN
  vector requirements are validated explicitly.
- Default **5 km** alert threshold is illustrative, not a safety declaration.
  Statuses: SCREENED_WITHIN_COVERAGE, ALERTS_FOUND, INCOMPLETE, UNAVAILABLE;
  no SAFE status. Empty unavailable catalogs and skipped/rejected/failed coverage
  cannot validate as complete screening. Partial population coverage is distinct
  from completion of the declared available-snapshot calculation.
- Planned classification rules: threshold crossing into `< alert_distance`
  is NEW_CLOSE_APPROACH; for matched events, a decrease greater than the default
  **1 m** numerical tolerance is WORSENED, an increase greater than **1 m** is
  IMPROVED, otherwise UNCHANGED. Events are matched one-to-one within the default
  **120 s** TCA tolerance, not solely by object ID. Missing matching measurements
  are nullable, never filled with fabricated zeroes. These are numerical rules,
  not physical uncertainty estimates; calculation tests follow at checkpoint 6.
- Command: `../.venv/bin/python -m pytest tests/test_screening_models.py
  tests/test_catalog.py tests/test_constraints.py tests/test_api.py
  tests/test_maneuvers.py -v -s --maxfail=1` from `backend/`.
- Actual result: **54 passed, 2 warnings in 13.86 seconds**, exit **0**.
  All **15** new schema/window acceptance cases and relevant existing catalog,
  constraints, API-import and maneuver regressions passed. The broader catalog
  test reused its actual downloaded cache; no repeat bulk HTTP success is claimed.

## Phase 2 checkpoint 4 — Model-consistent differential trajectories

Status: PASSED.

- Added `DifferentialTrajectory` and batched SGP4 samples in
  `app/physics/screening_trajectories.py`, reusing NumericalTrajectory, RTN basis,
  Earth-pole orientation and existing frame transforms.
- Both numerical trajectories share reference epoch/force model/pole. Position
  and velocity differences are applied to nominal SGP4 in GCRS; both are then
  transformed through Astropy into TEME to compare against bulk SGP4 records.
  Frames are transformed, never relabeled. Zero impulse exactly recovers nominal
  SGP4 even when the raw J2 trajectory drifts from it.
- Added vectorized Astropy forward/inverse state transforms; sampling and dense
  single-time evaluation preserve the requested aware timestamp and SI units.
- Command: `../.venv/bin/python -m pytest tests/test_screening_trajectories.py
  tests/test_maneuvers.py tests/test_propagation.py tests/test_screening_models.py
  -v -s --maxfail=1` from `backend/`.
- Actual result: **35 passed, 1 warning in 16.30 seconds**, exit **0**.
- All six new differential-trajectory tests and existing maneuver, trusted SGP4
  and contract regressions passed. Includes zero/nonzero/opposite burns,
  impulse position continuity, velocity increment, batch/scalar agreement,
  frame round trips, shared anchors, repeatability and tighter integration.
- Approximate differential modeling is explicit; no physical precision or
  operational safety claim is inferred from these numerical tolerances.

## Phase 2 checkpoint 5 — Continuous-time secondary search

Status: PASSED.

- Added `app/physics/secondary_search.py`: one-vs-catalog search, bounded batched
  library SGP4, bounded nominal-position LRU cache, NumPy segment closest-point
  filtering and continuous-time squared-distance refinement. Retains multiple
  local minima, deduplicates shared-boundary detections and excludes self.
- The prefilter adds `40 m/s² * segment_duration² / 8` by default as a curvature
  allowance. This is a documented heuristic, not a proven completeness or
  physical uncertainty bound. The nearest relevant object is also refined even
  without an alert; distant objects are screened without unnecessary refinement.
- Epoch, propagation and compute/refinement failures are reported explicitly;
  workload caps yield incomplete results rather than fabricated detections.
- Mandatory command: `../.venv/bin/python -m pytest tests/test_secondary_search.py
  tests/test_screening_trajectories.py tests/test_maneuvers.py
  tests/test_screening_models.py -v -s --maxfail=1` from `backend/`.
- Initial run: **36 passed in 17.07 seconds**, one warning. Strengthened the large
  catalog test to verify broad filtering avoids refining every distant object;
  complete retest: **36 passed, 1 warning in 15.78 seconds**, exit **0**.
- All eight new search tests passed. The 10 km/s constructed crossing at **25 s**
  was over 100 km away at every coarse point but was detected between samples
  and refined to **10 m**. Four separate same-object local minima were retained;
  sampled-boundary events were not duplicated. Identical/nearly-identical cases,
  invalid propagation, frame mismatch, budgets and **1,000 objects** were tested.
- Analytic constructed trajectories exercise the real numerical search, not
  a fabricated live alert. Physical constructed orbital scenarios follow next.

## Phase 2 checkpoint 6 — Baseline/modified secondary comparison

Status: FAILED. Stopped at the first failed acceptance test as requested.

- Added `app/physics/secondary_comparison.py` to screen baseline and modified
  trajectories against the same snapshot/window, match same-object events by
  time and compute nearby counterfactual minima when only one path alerts.
- The original encounter counterpart is included but distinguished from
  additional objects. Closest-additional search excludes that counterpart.
  Classification uses actually calculated distances, not hardcoded statuses.
- Added six mandatory physical scenarios plus an interval-consistency test in
  `tests/test_secondary_comparison.py`. Constructed GCRS orbital states are
  propagated by the actual central-gravity/J2 DOP853 solver, including the
  third object's backward/forward physical trajectory, without mechanics mocks.
- Command: `../.venv/bin/python -m pytest tests/test_secondary_comparison.py
  tests/test_secondary_search.py tests/test_screening_models.py
  tests/test_screening_trajectories.py -v -s --maxfail=1` from `backend/`.
- Actual result: **1 failed, 1 passed in 1.58 seconds**, exit **1**;
  **36 collected**, remaining tests unrun after the hard stop.
- Scenario A passed: original close approach improved, no additional alert.
- Scenario B failed: the third-object alert is detected, but the result reports
  **2** NEW_CLOSE_APPROACH events instead of **1** physical event.
- Read-only diagnosis reproduced the raw search and comparison results:
  original counterpart clearance **10.000000 m → 1,024.273412 m**;
  third object reported at offsets **1,000.000000 s** (**10.000000 m**) and
  **1,000.001410 s** (**9.999009 m**) from the constructed start time.
- Confirmed likely cause: adjacent coarse segments retain both their shared
  sampled boundary and the refined minimum **1.41 ms** later. The boundary
  local-minimum check probes **10 ms** away, overshooting the true minimum and
  wrongly accepting the boundary. The deduplication tolerance is **1 ms**, so
  these two representations of one encounter survive as separate events.
- Read-only relative-state evidence: `d(distance²)/dt` at the sampled boundary
  is **−28.158946 m²/s**, i.e. separation is still decreasing; at the refined
  minimum it is approximately **0.047199 m²/s**. The boundary is not a distinct
  physical local minimum. This is an event-selection/deduplication bug, not
  a missing third-object alert or an SGP4/coordinate conversion failure.
- Likely correction: reject non-minimal internal segment endpoints using
  continuous-time/relative-velocity consistency, then deduplicate shared event
  brackets while retaining genuinely distinct local minima. Keep the mandatory
  one-event assertion; do not simply relax it or count the duplicate as real.
- No correction was made after failure. Scenarios C–F and subsequent regression
  tests remain unverified. Checkpoints 7–9 have not begun; no screened optimizer,
  API/CLI flow or complete Phase 2 readiness is claimed.

### Checkpoint 6 — Authorized correction and successful retest

- User authorized the boundary fix after reviewing the numerical diagnosis.
- Internal segment endpoints must now be stationary according to the actual
  relative-state derivative `2 r · v`, in addition to the existing distance
  probes. Numerical slope tolerance is explicitly separate from uncertainty.
  Window endpoints remain valid constrained minima. No widening of the event
  deduplication threshold or weakening of the one-event assertion was used.
- Added four regressions for minima **0.2 ms** and **1.41 ms** on either side
  of a shared sample boundary; retained exact-boundary and distinct-minima tests.
- Full checkpoint/relevant regression command unchanged:
  `../.venv/bin/python -m pytest tests/test_secondary_comparison.py
  tests/test_secondary_search.py tests/test_screening_models.py
  tests/test_screening_trajectories.py -v -s --maxfail=1` from `backend/`.
- Actual result: **40 passed, 1 warning in 5.98 seconds**, exit **0**.
- All six mandatory numerical orbital scenarios passed, including improving
  the original without additional alerts, creating a third-object alert,
  worsening an existing secondary, improving both, unavailable/incomplete
  catalogs and zero-burn equality. Different intervals are rejected.
- Actual constructed adverse case: original clearance **10.000000 m →
  1,024.273412 m** while the third-object clearance changes **1,024.374905 m →
  9.999009 m**, classified as exactly **one NEW_CLOSE_APPROACH**.
- Constructed third-object TCA is **1,000.001410 s** from test start; relative
  speed **100.010895 m/s**. These are actual J2 numerical calculations on
  controlled states, not a fabricated live-world alert.
- Checkpoint 6 is now **PASSED**; optimizer/API/CLI screening remains to be added.

## Phase 2 checkpoint 7 — Optional finalist screening

Status: PASSED.

- Kept the Phase 1 primary search/ranking intact. An opt-in retained pool of
  at most ten genuine evaluated options is hidden from serialized output.
  Only selected finalists undergo additional screening, within candidate and
  total-runtime limits. Default/disabled optimization follows its old path.
- Added `app/secondary.py` shared actual-GP differential service and
  `app/optimization/screened_optimizer.py` optional postprocessor. Results keep
  primary improvement separate from catalog screening, policy decision and rank.
- REPORT_ONLY preserves primary solutions and explicitly marks unscreened
  alternatives. REJECT_NEW_ALERTS and REJECT_ALL_ALERTS try the next ranked
  option after rejection. The latter excludes the original counterpart, which
  remains the primary objective. Incomplete/unavailable results never pass.
- Nine new tests exercise actual calculated candidate burns on controlled
  numerical orbits, including a rejected best option followed by a passing
  alternative, no acceptable candidate, budgets and minimum-effort objectives.
  A separate actual GP integration exercises the production differential path.
- Mandatory run: all original Phase 1 test files, plus
  `test_screened_optimizer.py`, `test_secondary_comparison.py`,
  `test_secondary_search.py`, `test_screening_models.py`,
  `test_screening_trajectories.py`, using `pytest -v -s --maxfail=1`.
- Actual result: **157 passed, 2 warnings in 110.03 seconds**, exit **0**;
  all **108 original tests** ran and passed. No skips or disabled assertions.
- Actual GP finalist: rank 1, 0.2 m/s radial burn, primary matched-model
  clearance **9,506.776620 m**; actual differential screen considered two
  other fixture records, refined two, completed within that declared partial
  scope with no additional alerts in its deliberately short 36-second
  post-TCA horizon. Screen runtime **4.796424 s**; this is a small-scope test,
  not acceptance of a full broader-catalog run.
- OpenAPI route-count regression will be explicitly extended for the two
  new endpoints at checkpoint 8 while verifying all eight old paths remain.

## Phase 2 checkpoint 8 — API and CLI integration

Status: PASSED.

- Added typed `GET /api/catalog/status` (last explicit load only; no download)
  and `POST /api/encounters/{id}/screen`. Body identity may be omitted when
  supplied by the route; explicitly supplied IDs must match. The hypothetical
  maneuver capability assumption remains required.
- Extended optimize requests with optional `secondary_screening` settings;
  absent settings preserve the original endpoint and optimizer execution.
  API/CLI share the same screening service and bounded propagation cache.
- Added noninteractive CLI `screen`, `catalog`, and opt-in optimize policies,
  plus the optional post-optimization interactive screening prompt. Optional
  EOF preserves completed primary results but never labels them screened.
  Output distinguishes primary objective, partial scope, horizon, new/worsened
  events, screening completion, policy decisions and selected candidate rank.
- Local `--catalog-file` defaults to explicitly local-only scope unless public
  `--catalog-group` flags are also supplied. This avoids unexpected downloads.
- Extended the OpenAPI route assertion to verify all eight original routes and
  exactly two additions. No scientific assertion was relaxed.
- Fourteen new transport/integration tests validate actual GP distances and
  event classifications, schemas, eight invalid-input cases, incomplete/empty
  catalogs, CLI prompts, local loading and exact API/CLI scientific agreement.
- Command: `../.venv/bin/python -m pytest -v -s --maxfail=1` from `backend/`.
- Actual result: **188 passed, 2 warnings in 153.29 seconds**, exit **0**;
  no skips. Warnings are upstream AnyIO deprecation and inaccessible optional
  Astropy download-cache directory; installed offline IERS data are used.
- Final real broader-catalog acceptance and benchmark checkpoint is next.

## Phase 2 checkpoint 9 — Real-data verification and measured performance

Status: PASSED. Initial integration checks and the final complete suite passed.

- Added `app/secondary_benchmark.py`; reports catalog load, propagation,
  coarse/refinement/comparison/differential generation, candidate total and
  optimizer+screen totals, considered/refined objects, maneuvers screened,
  selected primary rank, actual events, skipped reasons and provenance.
  Includes selected records and separate base/combined screening snapshots.
- Initial command: `../.venv/bin/python -m pytest
  tests/test_secondary_integration.py -v -s --maxfail=1` from `backend/`.
  Actual result: **6 passed, 2 warnings in 131.40 seconds**, exit **0**.
- Tested failed catalog download with halted further requests and UNAVAILABLE,
  actual stale secondary epoch handling, injected numerical solver failure
  returning explicit HTTP 422 without fabricated scientific output, a fixture
  benchmark, three actual public-source pipelines and broader-catalog API/CLI.
  Existing tests cover unsupported windows, empty catalogs, budget exhaustion,
  partial population coverage and genuine adverse-case policy rejection.
- Three real encounter IDs:
  `socrates-f3f9e438db4c8a81fa4b93e5` (53495/34452),
  `socrates-7f5e8144e4f1e8ded96dbc05` (53604/100033),
  `socrates-599855ce2ca729ae50cb34e9` (27056/12107).
  Source dataset: **195,282** actual SOCRATES rows; SHA-256
  `4e8b1a87555c4ef98cec6327e5c4140ee3893f7ada7818f1faa3f0f3c8745fb7`.
- Each real pipeline evaluated **123** primary candidates and screened **one**
  finalist under REPORT_ONLY, max three finalists, 30-second candidate budget
  and 35-second total screening budget. Lead window **10–15 minutes** before
  published TCA, impulse cap **0.2 m/s**, alert **5 km**, coarse step **30 s**,
  post-TCA horizon **0.01 h = 36 s**. This is deliberately not an assertion
  that the normal six-hour default was completed.

| Pair | Catalog load s | Catalog propagation s | Coarse s | Refine s | Screen s | Optimize + screen s | Objects considered / refined |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 53495 / 34452 | 1.254159 | 0.825845 | 0.128903 | 16.912245 | 18.818313 | 20.569151 | 19,123 / 11 |
| 53604 / 100033 | 2.469127 | 1.088182 | 0.144012 | 27.790914 | 30.080807 | 31.991188 | 12,440 / 16 |
| 27056 / 12107 | 2.405070 | 1.013391 | 0.215228 | 10.812061 | 13.629340 | 15.167777 | 19,222 / 8 |

- Broader base snapshot: **19,505** unique objects, **28** duplicates, no
  ingestion rejects/download failures, all five datasets reused from cache;
  SHA-256 `d7dacf5368dbd802bef65e37215ab771fe892e04fa384a394220dab49684ee4e`.
  Third case adds actual missing original counterpart 12107, yielding **19,506**
  combined records and an explicitly distinct checksum/source set.
- All three screens correctly returned **INCOMPLETE**, `policy_passed: null`.
  Endpoint-invalid epochs: **380 / 357 / 282**. The first/third had one failed
  SGP4 record. The second also exhausted continuous refinement/comparison time,
  with unprocessed objects explicit. No additional 5 km alerts were detected
  in the evaluated portion; this is not evidence of absent conjunctions.
- Actual nearest additional calculated events: first case object **53619**,
  baseline **14,563.289212 m → 14,498.456481 m**, third case object **49101**,
  baseline **210,938.461594 m → 210,926.043417 m**, both above alert threshold.
  Second case's closest comparison was unavailable when its budget expired.
- Primary matched-model best clearances: **10,903.134604 / 64,211.586110 /
  1,374.670908 m**. Third case did not reach the 10 km target and says so.
  Both primary objective metrics and secondary assessments remain separate.
- Selected individual GP refresh changed counterpart 34452 to epoch
  **2026-10-10T17:30:09.069696Z**, selected checksum
  `f6737d9a2ee3845e3ae2abd8f34b5dd4fcc0bc46b120a93543031b3693a03e56`;
  bulk cosmos-2251-debris remains epoch **2026-10-10T08:01:31.241568Z** and
  checksum `778b4e73ee3f55ed485e45e976bf513f71ea8151a3958cc05d59ca3a2efa5d3f`.
  Added explicit counterpart mismatch warnings and a regression using a
  deliberately changed test input. Do not equate primary/screening distances
  across these identified snapshots or across their different force models.
- Actual API/CLI demonstrations used 15-second screening limits and returned
  INCOMPLETE with **6,624 / 5,518** objects considered and elapsed **15.035639 /
  15.095725 s** respectively. API HTTP 200 screening/catalog-status succeeded;
  CLI exit 0 preserved primary REPORT_ONLY options without a screening pass.
  Exact scientific transport agreement is separately validated with sufficient
  budget in the same declared small snapshot/window.
- Profile command: `../.venv/bin/python -m app.secondary_benchmark --object-id
  53495 --profile --screen-timeout-seconds 15 --max-objects 256`, exit **0**.
  Profiler: **27,205,605** calls, **42.453 s** total including source parsing
  and primary optimization. Astropy transforms **17.477 s** cumulative;
  continuous secondary relative-state evaluations **14.596 s**. Batched
  catalog propagation **0.029922 s**, coarse **0.001644 s**, refinement
  **14.601316 s**, screen total **15.209746 s**. Deliberately capped/profiled
  workload returned INCOMPLETE; profiling overhead alters completed work.
  Coordinate transforms dominate refinement, not bulk SGP4. No physical
  transformations were removed or approximated merely to hit a runtime target.
- Final hardening adds applied threshold to each result, rejects failed-refresh
  stale primary sources, and protects the bounded shared position-cache LRU
  against concurrent API access. New regression checks verify these contracts.
- Full regression command: `../.venv/bin/python -m pytest -v -s --maxfail=1`.
  Final result: **197 passed, 2 warnings in 300.03 seconds**, exit **0**;
  **108 original Phase 1 tests + 89 new tests**, with no failures, skips,
  deselections or disabled assertions. All nine Phase 2 checkpoints are passed.
- Final-suite real-data retest retained identical scientific primary options,
  nearest reported events and honest INCOMPLETE statuses. Measured screen totals
  were **20.081032 / 30.053986 / 12.644650 s**, and optimizer+screen totals
  **21.748674 / 31.970903 / 14.173867 s**. Considered/refined counts were
  **19,123/11**, **761/8**, **19,222/8**. The second run again reached its
  time cap; processed-prefix counts are workload/timing dependent, not a
  promised coverage count. All skipped reasons remain explicit, no policy pass.
- Retest combined third-case snapshot SHA-256:
  `42c2b8c70f2482ec3fee25e0c3956db0bd9fe87777ea6190522268216b5cfa5d`.
  Retest broader API/CLI each considered **6,624** objects, with INCOMPLETE
  statuses and elapsed **15.015221 / 15.030059 s**. Sufficient-budget fixture
  API/CLI scientific agreement and all original endpoint contracts passed.
- `git diff --check` passed. No dependencies or frontend/Pc/cleanup components
  added. Changes were initially handed off locally. The user subsequently
  requested commit/push and made publication after completed, tested changes
  the default repository workflow; this preference is recorded in `AGENTS.md`.
  Publication is verified against the remote branch before reporting success.
