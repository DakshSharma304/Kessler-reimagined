# Implementation checkpoints

## Phase 6 — frontend checkpoint policy and baseline

The latest Phase6 brief authorizes fixing/retesting failures, with a hard stop
after three substantial unsuccessful attempts on the same blocker; every gate
must pass before dependent development. This supersedes the older first-failure
repository policy for this explicitly requested phase. User visual/deployment
instructions take precedence: restrained Apple-inspired UI, regular React code
in this repository, Vercel frontend and Modal Python backend. No ChatGPT Sites.

- Clean verified backend baseline5d758b74f11e8a68fe4fddafca3dcdb80f4922ac,
  protected by local tag `phase5-before-frontend`; scientific engines unchanged.
- Read complete Phase6 brief, FRONTEND_CONTRACT, OpenAPI, README, actual routes,
  source/status/frame/unit and calculation schemas before frontend development.
- Actual backend started on8000; initial smoke reached it before readiness:
  `[Errno 111] Connection refused`. After actual healthHTTP200, full documented
  smoke rerun exited0: all six workflows, real encounter/optimizer/secondary
  screening, NASA Pc, actual MSIS/persistence and cleanup. This was a startup
  timing failure, not a scientific result. Screening INCOMPLETE and no live Pc
  remain disclosed. No failed gate was advanced.
- Existing pinned Python environment reused. Node24.19.0/npm11.9.0 and actual
  system Chromium154 available. Frontend dependencies/test tools are scoped to
  frontend with a lockfile; no Python dependency or scientific source rewrite.

### Checkpoint 1 — PASSED

- React19/TypeScript5/Vite7 initialized under frontend; actual OpenAPI-generated
  types, TanStack query client, Zustand UI state, Motion/reduced-motion shell,
  Lucide controls and graphite styling. API base configurable with explicit
  production validation, readable scientific/validation/network errors.
- npm install exit0 (244 packages/44s), lockfile retained. TypeScript and
  production build exit0 (3.91s),4 API contract unit tests passed (820ms).
- Actual Chromium browser with real backend health: navigation changes view,
  panels close/reopen, responsive390x844 shell renders with no document
  overflow or fatal page errors:1 passed/5.4s, exit0. Screenshot reviewed.
  Globe/analysis content deliberately not claimed implemented at this gate.

## Phase 5 — Checkpoint policy and verified baseline

Phase 5 follows the latest explicit user policy: diagnose/correct failures,
rerun the entire checkpoint and relevant regressions, stop after three
substantial unsuccessful attempts on the same blocker. This overrides the
older first-failure policy for this phase only. Never advance a failed gate.

### Checkpoint 1 — PASSED

- Initially clean baseline `eac189cdc81e1d973b27e77280dab0008279037b`,
  protected by tag `phase4-before-frontend-readiness`.
- Inspected source/model/cache architecture, APIs/schemas, orbital/encounter
  physics, numerical maneuvers/optimizer, secondary catalog screening, Pc,
  MSIS/drag/persistence, CLI and test coverage. All **51 backend modules**
  imported successfully; actual OpenAPI has **15 paths, 62 schemas**.
- Full existing suite from backend:
  `../.venv/bin/python -m pytest -q --maxfail=1`:
  **397 passed, 2 upstream warnings in 419.03 s**, exit **0**, no skips or
  deselections. No Phase 5 implementation preceded this passing gate.
- Actual-source/HTTP focused command covering startup, real API smoke, live
  optimizer/screening/Pc, NASA references and HTTP decay:
  **10 passed, 2 warnings in 27.19 s**, exit **0**. Actual API encounter
  `socrates-599855ce2ca729ae50cb34e9` analyzed/simulated/optimized HTTP200.
  Actual `socrates-f3f9e438db4c8a81fa4b93e5` optimizer COMPLETE, 13 evaluations;
  secondary screening INCOMPLETE with 97 considered/19,505 available, no
  safety pass; live Pc unavailable without covariance, MAX_PROB1 separate.
  Four NASA cases still match independent reference tolerance2e-9, maximum
  relative discrepancy1.242e-10. Real HTTP decay/persistence (.01 day) took
  1.218/.641 s, no boundary reached; owned uvicorn processes stopped.
- `pip check` exit0, no broken requirements. Warnings remain upstream
  AnyIO deprecation and optional read-only Astropy cache; offline IERS used.
- Gaps: no paginated object browser, bulk visualization positions, dedicated
  ITRS trajectories, cleanup model/portfolio endpoint or CORS/server config.
  Existing scientific services are working, not replacements to implement.
  GP CLASSIFICATION_TYPE/U is a security marking, not object type. Real
  object classification must be joined separately. Ordinary browsing must
  not launch atmospheric simulations. Persistence output is presently
  returned but not retained as reusable cleanup evidence.

Current API request/response schemas (actual OpenAPI references; none invented):

| Method/path | Request model | Response model |
| --- | --- | --- |
| GET /api/health | none | HealthResponse |
| GET /api/status | none | StatusResponse |
| GET /api/catalog/status | none | CatalogStatusResponse |
| GET /api/encounters | bounded sort/limit/object_id/name query | EncounterListResponse |
| GET /api/encounters/{encounter_id} | path ID | ScreenedEncounter |
| POST /api/encounters/{encounter_id}/analyze | optional AnalyzeRequest | BaselineAnalysis or ProbabilityBaselineAnalysis |
| POST /api/encounters/{encounter_id}/simulate | SimulateRequest | ManeuverSimulation or ProbabilityManeuverSimulation |
| POST /api/encounters/{encounter_id}/optimize | OptimizeRequest | OptimizationResult |
| POST /api/encounters/{encounter_id}/screen | ScreenRequest | ScreeningResult |
| GET /api/objects/{object_id} | path ID | OrbitalRecord |
| POST /api/probability/calculate | DirectProbabilityRequest or ReferenceProbabilityRequest | ProbabilityAnalysis or ReferenceComparison |
| GET /api/space-weather/status | optional load query | SpaceWeatherStatus |
| POST /api/atmosphere/density | DensityRequest | DensityResult |
| POST /api/objects/{object_id}/decay | PersistenceRequest | PersistenceAnalysis |
| POST /api/objects/{object_id}/persistence | PersistenceRequest | PersistenceAnalysis |

### Checkpoint 2 — PASSED

- Added documented CelesTrak SATCAT metadata joins (PAY/R/B/DEB/UNK and
  operational status); GP security markings are never used as object types.
  Actual download contained 70,980 records. No GCAT/mass/dimensions were
  invented; RCS is explicitly not aerodynamic area. Six preserved genuine
  SATCAT fixture rows are documented with source/date.
- Transparent illustrative policy: capped screening exposure by default;
  optional capped modeled persistence/logarithmic RCS with configurable
  weights. Missing positively weighted evidence makes the score unavailable,
  never reweighted/zero-filled. Available persistence is censored scenario
  evidence, not lifetime extrapolation. No atmospheric work during ranking.
- Fixed-count stable ranking and bounded binary HiGHS effort selection;
  actual resource sums verified. Shared events have unique/shared IDs, never
  independently prevented-collision benefits. Scope/eligibility/exclusions
  and missing-data indicators are explicit.
- Focused command `../.venv/bin/python -m pytest tests/test_cleanup.py -v -s
  --maxfail=1`: **17 passed, 1 warning, 41.83 s**, exit0. First run exposed
  a test incorrectly comparing expected HTTP/ST​ALE_CACHE provenance labels;
  corrected to assert unchanged data/checksum AND the changed retrieval mode,
  reran the entire checkpoint. No scientific assertion weakened.
- Independently enumerated 100 additional seeded small budget problems:
  every proxy optimum matched and no budget/count violation, exit0. Initial
  manual harness omitted tests/ from PYTHONPATH; corrected harness and reran.
- Full current suite: **414 passed, 2 warnings in 572.95 s**, exit0, no skips.
- Actual default 200-object pool selected **10114 SL-3 R/B**, **11672 SL-14
  R/B**, **12139 SL-8 R/B**; published screening counts **46/12/18**. Capped
  exposure scores tie at1, deterministic NORAD-ID tie break. **2,564** eligible
  objects outside this bounded pool are explicitly disclosed, not a claim
  of global ranking. Cold actual-source example took38.160785s including
  catalog/SATCAT/SOCRATES ingestion. Modeled priority ranking, not mission plan.

### Checkpoint 3 — PASSED

- Added five paths (six operations): paginated/searchable/classified objects,
  bounded bulk positions, object metadata, sampled orbit, and GET/POST
  encounter trajectories. All 15 existing paths/contracts retained.
- Real SGP4 arrays -> actual Astropy TEME/ITRS transforms; numerical maneuver
  paths GCRS -> ITRS. Visualization positions km, aware UTC timestamps,
  explicit Three.js mapping (x,z,-y); no raw-TEME relabeling or meter/km mix.
  Max2000 batch IDs, max1001 path samples, max24h single-orbit interval;
  isolated SGP4/unsupported-epoch/missing-object nulls and error statuses.
- Focused tests **19 passed, 2 warnings in21.79s**, exit0. First run found
  vectorized SGP4's requirement for contiguous Julian-date arrays; copied
  NumPy column views to contiguous buffers (unchanged values/model), then
  reran the entire checkpoint. Independent direct-Astropy conversion,
  units, timestamps, actual SGP4 error isolation, search/filter/detail,
  participant IDs, bounds, optimizer anchor and zero-burn consistency pass.
- Actual benchmark **1200/1200 OK**, finite positions, **0.090567s**, JSON
  **304,086 bytes**; source ingestion preloaded and measured separately.
- Full current regression: **428 passed, 2 warnings in591.04s**, exit0,
  no skips/deselections. Exactly20 OpenAPI paths, every schema ref resolves.

### Checkpoint 4 — PASSED

- All six frontend workflows execute through production HTTP routes/services
  using genuine input fixtures: browse/ITRS paths, encounters, same-anchor
  optimizer/simulator/secondary screen, NASA+live/scenario Pc, actual MSIS
  persistence comparison, and persistence-informed cleanup. No fake scientific
  backend or precomputed output. Exactly21 paths/22 API operations.
- Added cleanup endpoint, explicit selection reasons, thread-safe bounded
  persistence evidence retention, optional compact ITRS persistence response
  (actual samples; raw scientific samples explicitly omitted), encounter
  pagination/time filters. Existing default scientific contracts retained.
- Configurable process environment for cache/data/files/origins/host/port;
  explicit local CORS, production defaults to no allowed browser origins,
  wildcard origins rejected. No dotenv dependency/no auth claim. Two bounded
  concurrent expensive calculations by default; immediate429 BUSY, no
  unbounded calculation queue. Health/catalog browsing do not acquire slots.
- New workflow/config/error tests **10 passed in8.68s**, exit0; targeted
  existing regressions **49 passed in54.11s**, exit0. Invalid/no-data cases,
  NASA reference calculations, CORS rejection and capacity release verified.
- Actual process `../.venv/bin/python -m app.server` started with configurable
  ephemeral port; health/OpenAPI/local CORS HTTP200, exactly21 paths. Owned
  server stopped cleanly; no developer-specific path required.
- User requested faster execution while retaining essential checks. Confirmed
  4-core CPU quota/32GiB memory; ran the COMPLETE suite in3 disjoint processes
  with BLAS/OMP threads1 (no changed physical models/assertions/time limits).
  ShardA:15 passed/210.42s; B:31 passed/206.81s; C:392 passed/220.27s,
  each exit0. JUnit union matches **all438 collected test IDs exactly**,
  zero failures/errors/skips/duplicates/omissions. Verification harness first
  compared before completing its loop; corrected indentation and reran,
  exit0. This was a harness error, not a failed scientific result.
- Shards: A=persistence_end_to_end,persistence_scenarios,decay_performance_fix;
  B=secondary_integration,secondary_api_cli,screened_optimizer;
  C=all remaining files. All upstream warnings remain disclosed.

### Checkpoint 5 — PASSED

- Created `FRONTEND_CONTRACT.md`, exact `openapi.json` (21 paths, 22
  operations, 83 schemas), HTTP-only `python -m app.frontend_smoke`, and
  reproducible `python -m app.export_frontend`. Existing scientific error
  responses are now documented alongside FastAPI validation errors; their
  runtime behavior has not changed.
- Actual server started using `KESSLER_PORT=8015 ../.venv/bin/python -m
  app.server`. Public smoke command exited0: all six workflows passed,
  30 genuine request/response exchanges captured in `frontend_examples.json`
  at 2026-10-11T10:07:06.996881+00:00. Every response validated against its
  actual FastAPI response model. Six verbatim curl examples were rerun:
  every request HTTP200. OpenAPI refs resolve and export is repeatable.
- Live encounter `socrates-599855ce2ca729ae50cb34e9`; both maneuver
  alternatives honestly screened INCOMPLETE, not a safety certificate.
  Live Pc UNAVAILABLE_NO_COVARIANCE; historical Terra March2021 reference
  relative discrepancy2.9362918056463266e-13; fixed-covariance scenarios
  explicitly ILLUSTRATIVE. Actual MSIS atmospheric scenarios calculated.
  Modeled cleanup selection29734/29737 from explicit five-object pool.
- Focused handoff tests4 passed/7.81s; after documentation-generator
  precision improvement, all4 rerun passed/8.75s, exit0. Existing/new full
  suite: shardA15 passed/173.16s, B31 passed/187.70s, C396 passed/215.79s,
  each exit0. JUnit union equals all442 collected tests exactly, with zero
  failures/errors/skips/duplicates/omissions. Upstream warnings unchanged.
- All schemas/units/statuses/caps/provenance, allowed CORS, invalid startup
  configuration and both error shapes verified. No hardcoded developer
  paths, fabricated example outputs, new dependencies or fully-offline
  live-backend claim. Root example transcript is an explicitly dated
  integration deliverable, not a download cache or current live guarantee.

### Checkpoint 6 — PASSED — KESSLER BACKEND: FRONTEND READY

- Final actual public API integration at2026-10-11T10:38UTC (06:38EDT): all
  six workflows passed, 30 actual HTTP responses validated against current
  FastAPI models. Repeated standalone `python -m app.frontend_smoke --base-url
  http://127.0.0.1:8015` also exited0. No frontend or new scientific phase.
- Real CelesTrak five-group catalog refreshed over HTTP at10:38:09UTC,
  19,505 records; PARTIAL coverage and207 old epochs retained/disclosed.
  1,200 actual finite SGP4/Astropy ITRS/km positions. Search/select/details,
  orbit/encounter/maneuver trajectories work with bounded payloads.
- Actual SOCRATES encounter `socrates-599855ce2ca729ae50cb34e9` selected,
  analyzed, optimized (13 evaluations), two alternatives screened; both
  INCOMPLETE within max128-object/5s bounds, never claimed safe. Live Pc
  unavailable without covariance; source screening maximum separate.
  Explicit covariance and fixed-covariance maneuver scenarios illustrative.
- All four independent NASA API reference comparisons pass unchanged2e-9
  relative tolerance; maximum actual relative discrepancy1.2418621604014618e-10.
  Pc values/fixture stems/provenance in PERFORMANCE.md/performance.json.
  Actual MSIS three atmospheric scenarios/compact ITRS paths work; actual
  source-weather cache (observed/forecast qualifiers preserved) also loaded
  and actual-source density calculated. No invented aerodynamic properties.
- Explicit five-debris pool cleanup selects29734/29737 under max2targets;
  proxy policy/scope/unknown mass/exclusions/reasons disclosed. Never a
  removal mission plan, dollar return or precise collision-prevention estimate.
- Investigated repeated public-screen catalog parsing: matching default
  scope now reuses existing five-minute snapshot, with original data epochs,
  provenance, staleness checks and warnings. Custom/local scopes unchanged.
  Three new genuine-input tests verify identity/expiry/fingerprint/scope/local
  isolation/status. Entire targeted API/handoff/secondary gate31 passed,
  2 upstream warnings/35.84s, exit0. No physics/assertion/cap changes.
- Reproducible `scripts/benchmark_frontend.py` ran all six real workflows
  then3 warm HTTP trials per operation before concurrent regression load.
  Warm medians seconds: catalog search.010600; positions1200 .064365;
  orbit21samples .006758; encounter.007710; optimize13 .245380;
  bounded screen.090469; NASA Pc.018017; persistence3x.001day .150503;
  cleanup5pool 1.005915. First screen3.701s, second.077s; repeated geometry
  benefits from verified propagation cache too. Legacy skipped-object list
  explains~0.8MB screen output; contract retained and frontend display advice
  documented. These are measured bounded workloads, not latency promises.
- Final COMPLETE suite: shardA15 passed/180.53s; B31 passed/134.84s;
  C399 passed/206.85s; each exit0. Exact JUnit union equals **all445 collected
  test IDs**, zero failures/errors/skips/duplicates/omissions. All397 original
  Phase4 tests plus48 Phase5 tests executed. Pipcheck no broken requirements.
  Remaining warnings are upstream AnyIO and optional read-only Astropy cache;
  offline installed IERS remains active, no download or precision fabrication.
- README updated; FRONTEND_CONTRACT.md complete; actual openapi.json exported
  again (21 paths/22operations/83schemas) and matches running app; all schema
  refs/documented routes/60 captured example responses validated. No hardcoded
  developer paths, outputs, credentials, frontend or dependencies added.
- Cloud setup skill saved verified existing-environment startup/smoke/check
  instructions in start_skill only. Draft status saved/requires_publish=true;
  no claim of publication or validation in a new cloud task. Other environment
  configuration preserved. No install needed in this prepared environment.

- Final post-documentation/export artifact check: all7 handoff/cache tests
  passed, 2 upstream warnings/7.17s, exit0. Final diffcheck clean. Both actual
  server processes owned by this task shut down after verification; no running
  process is assumed to persist into a future environment.

All six Phase5 mandatory checkpoints PASSED. Actual-source coverage, unavailable
covariance/physical metadata, fixed-covariance/drag assumptions, censored lifetime,
incomplete secondary screening, synchronous workload limits and no full offline
live mode remain explicit. Git publication is performed after this verified gate.

## Phase 4 — Checkpoint policy

The latest explicit user instruction and AGENTS.md require stopping at the
first failed mandatory checkpoint: inspect actual errors, diagnose the likely
cause, record evidence, and request authorization before correcting or
continuing. This takes precedence over the pasted Phase 4 retry policy.
No subsequent stage begins before its predecessor passes.

## Phase 4 — Checkpoint 1: verified Phase 3 baseline

Status: PASSED (2026-10-11).

- Initially clean checkout at `23aa4c423155d99284f470853e33030a0241e00a`,
  preserved with Git tag `phase3-before-orbital-decay`.
- Inspected README, historical checkpoint evidence, pinned dependencies,
  orbital models, SGP4, frame utilities, numerical integrator/J2, optimizer,
  secondary screening, probability engine, API and CLI. Existing public
  interfaces and startup/test commands are documented in README.
- Reusable numerical convention: validated `StateVector`, aware UTC times,
  metres/m/s, real SGP4 TEME-to-GCRS position and velocity transforms,
  WGS84 central gravity/J2 and adaptive `solve_ivp` DOP853. Existing short
  maneuver integrations hold the Earth pole at the reference epoch.
  GP BSTAR is orbital metadata, not a supplied physical ballistic coefficient.
  New long-horizon density work must use actual Earth-fixed/geodetic positions.
- Full baseline command, from backend:
  `../.venv/bin/python -m pytest -q --maxfail=1`:
  **302 passed, 2 warnings in 282.11 s**, exit **0**. No skipped or deselected
  tests, weakened assertions, replacement scientific fixtures, or code changes.
- Additional verbose verification:
  `../.venv/bin/python -m pytest tests/test_probability_end_to_end.py::test_actual_live_geometry_scenario_maneuver_optimizer_and_screening tests/test_probability_reference.py tests/test_startup.py -v -s --maxfail=1`:
  **8 passed, 2 warnings in 17.65 s**, exit **0**.
- Real SOCRATES/GP case `socrates-f3f9e438db4c8a81fa4b93e5`: optimizer
  COMPLETE, 13 evaluated simulations. Secondary screening executed against
  19,506 available catalog records, considered 4 under its explicit bounded
  budget, correctly INCOMPLETE with no policy pass. Live covariance-based Pc
  UNAVAILABLE_NO_COVARIANCE; real SOCRATES MAX_PROB remains separately 1.0.
  Explicit assumed covariance scenario baseline Pc `6.304736762114633e-7`,
  modified Pc `5.926506440598308e-7`, not measured risk.
- All four genuine historical NASA benchmarks independently recalculated;
  maximum relative discrepancy `1.242e-10` against tolerance `2e-9`.
  Actual uvicorn subprocess served HTTP health successfully and was stopped.
- `../.venv/bin/python -m pip check`: no broken requirements, exit **0**.
  Warnings remain upstream AnyIO deprecation and read-only optional Astropy
  cache; installed offline IERS data were used. No installation was needed.

## Phase 4 — Checkpoint 2: real space-weather ingestion

Status: PASSED.

- Verified live CelesTrak SpaceData listing and format documentation, both
  curl exit 0. Actual linked `SW-All.csv` downloaded with HTTP 200, exit 0;
  original source timestamp `2026-10-11T06:32:11Z` (HTTP Last-Modified).
- Added `app/data/space_weather.py`, reusing atomic checksum-validated
  FileCache; six-hour refresh bounds, provider failure preserves valid cache,
  stale status and halted retries. No orbital calculation code changed.
- CSV preserves Earth-distance vs 1-AU-adjusted flux, centered vs trailing
  81-day averages, daily vs three-hourly Ap, missing/null values and separate
  solar qualifiers OBS/INT/PRD/PRM. The CSV does not establish per-field
  geomagnetic issue/provenance times, explicitly warned. No monthly-to-daily
  extrapolation. As-of backtests require an appropriately archived snapshot.
- Actual downloaded dataset: **25,436 records**, date range **1957-10-01
  through 2041-10-01**; last observed flux **2026-10-10**; daily solar forecast
  **2026-10-11 through 2026-11-24**; monthly solar forecasts **2026-12-01
  through 2041-10-01** are not complete daily environmental coverage.
  Cache fetch `2026-10-11T06:57:19.081233Z`; checksum
  `41fee3d7fda0943aa78e94e99b4070de9f9e8334a6fc3e5319d73a5bf3bb4e88`.
- `../.venv/bin/python -m pytest tests/test_space_weather.py -v -s --maxfail=1`:
  **11 passed in 3.26 s**, exit 0, including actual external HTTP ingestion,
  historical numerical values, categories, malformed input, missing data,
  coverage, cache and simulated provider failures (network isolation only).
- Full regression `../.venv/bin/python -m pytest -q --maxfail=1`:
  **313 passed, 2 upstream warnings in 322.01 s**, exit 0; all 302 previous
  tests rerun, no skips or deselections. Density implementation did not begin
  until this gate passed.

## Phase 4 — Checkpoint 3: NRLMSIS atmospheric density

Status: PASSED.

- Read official pymsis API documentation and installed version's signature/
  docstring. Installed binary `pymsis==0.12.0` without changing existing pins;
  model version explicitly **NRLMSIS 2.1**, no implicit library weather downloads.
  Pip installation/check both exit 0; no broken requirements.
- `app/physics/atmosphere.py` implements validated explicit weather forcing,
  correct previous-day Earth-distance F10.7, modeled-date centered81 and
  storm-time Ap vector (daily, current/3/6/9 hours, 12–33/36–57-hour averages).
  Qualifiers/checksum/timestamps/limitations accompany source inputs.
- Actual GCRS/TEME state positions transform through Astropy to ITRS and
  WGS84 geodetic latitude/longitude/altitude. Longitude −180..180 degrees,
  altitude metres converted to pymsis kilometres; density returned kg/m³.
  Explicit supported model interval 0–1000 km, no extrapolation.
- Controlled independent direct pymsis call reproduced exactly:
  2026-10-09 12:00 UTC, 40° N, −105°, 400 km, hypothetical previous/center81
  F10.7=150 sfu and Ap=15: **3.0355277753219e-12 kg/m³**. Positive, finite,
  deterministic. Controlled 200/400/800-km altitude ordering and low/high
  solar/Ap response passed. Coordinate round trips include high latitude,
  southern hemisphere, near-dateline and TEME input.
- Density-provider interface includes explicitly named constant verification
  atmosphere, never a real-data default. Real weather timing independently
  reconstructed and supplied to actual MSIS; unavailable/as-of data rejected.
- Focused weather/density run: **29 passed, 1 warning in 5.12 s**, exit 0.
- Full `../.venv/bin/python -m pytest -q --maxfail=1`:
  **331 passed, 2 upstream warnings in 327.76 s**, exit 0, all 313 prior tests.
- Measured 100 actual MSIS density calls **0.014563 s**, 100 direct Astropy
  scalar geodetic conversions **0.923745 s**, after initial frame setup.
  Coordinate conversion is the measured propagation-performance concern;
  any future accelerated transforms must be independently validated.

## Phase 4 — Checkpoint 4: atmosphere-relative drag physics

Status: PASSED.

- Added `app/physics/drag.py`: SI −½ρ(Cd*A/m)|v−ω×r|(v−ω×r), with unit
  GCRS Earth pole and ω=7.292115e-5 rad/s. Co-rotation, not inertial orbital
  speed, defines the drag direction. Atmospheric winds/attitude are not modeled.
- Strict explicit properties require either supplied mass/area/Cd or Cd*A/m,
  plus USER_SUPPLIED/HYPOTHETICAL_ASSUMPTION identity. No missing-property
  defaults or BSTAR substitution. Zero area/density explicitly yields zero drag.
- Extracted the existing central/J2 formulas into shared `gravity_components`
  in the original maneuver module; NumericalTrajectory uses that same helper.
  No new optimizer objective or default drag behavior.
- Focused new drag plus original maneuver/optimizer suite:
  **27 passed, 1 warning in 20.00 s**, exit 0. Includes physical scaling,
  co-rotating zero-relative-velocity case, units/direction, invalid inputs,
  deterministic force and exact (absolute 1e-7 state tolerance) zero-drag
  integration agreement with the existing gravity/J2 numerical trajectory.
- Original optimizer benchmark: **123 evaluations, 123 feasible, 0 numerical
  failures**, COMPLETE, **3.743 s**, unchanged fixture clearance
  **10,796.958 m** at 0.2 m/s.
- Full `../.venv/bin/python -m pytest -q --maxfail=1`:
  **344 passed, 2 upstream warnings in 328.01 s**, exit 0. All 331 prior tests
  rerun; no skips, deselections or assertion weakening. Decay propagation
  began only after this gate passed.

## Phase 4 — Checkpoint 5: decay propagation (blocked)

Status: FAILED / STOPPED at first mandatory test failure, as requested.

- Last verified implementation commit: `4d00e66` (Checkpoint 4, 344 passing
  full-suite tests). Checkpoints 1–4 passed; Checkpoints 6–10 have not started.
- New local work adds `app/physics/decay.py` and prepared MSIS evaluation:
  bounded adaptive DOP853 with shared gravity/J2 and explicit drag, SI state
  samples/osculating elements/total J2 energy, and batched Earth-orientation
  interpolation. These propagation changes are **unverified**, not complete.
- Actual command from backend:
  `../.venv/bin/python -m pytest tests/test_decay.py tests/test_drag.py tests/test_atmosphere.py -v -s --maxfail=1`.
- **41 tests collected; 1 failed, 1 upstream warning in 2.88 s; exit 1**.
  Remaining 40 tests were unrun after the hard stop, not passed or skipped.
  Full Checkpoint 5 regressions have not run.
- Failed test:
  `tests/test_decay.py::test_orientation_and_prepared_density_independently_checked`.
  Actual exception:

  ```text
  ValueError: Weather forcing requires matching UTC date and aware timestamp
  forcing.date = datetime.date(2026, 10, 9)
  timestamp = datetime.datetime(2026, 10, 10, 11, 59, 59, tzinfo=datetime.timezone.utc)
  ```

- Read-only inspection confirms the test imports `test_atmosphere.weather`,
  which intentionally creates a fixed 2026-10-09 forcing for same-day density
  tests. The new decay test uses `lambda at: weather()` and spans 86,399 s
  from October 9 at noon into October 10. At the final timestamp the existing
  correctly strict forcing validator rejects that previous day's record.
  Coordinate assertions execute before this rejection; this failure is a
  new test-input epoch mismatch, not evidence of a failed MSIS installation.
- Likely correction: make the controlled hypothetical weather provider assign
  the queried UTC date while preserving its explicitly assumed constant solar
  history, in both direct and prepared evaluation paths. Keep the midnight
  test, strict date validation, and numerical tolerances. Do not relabel real
  observations or silently carry real forecasts into unsupported dates.
- No correction applied. Awaiting user authorization before rerunning this
  checkpoint or implementing boundary detection, scenarios, persistence,
  new APIs/CLI or final performance workflows.

### Phase 4 checkpoint 5 — Authorized correction and successful retest

Status: PASSED after explicit user authorization.

- Corrected only the new synthetic test's weather provider to stamp the queried
  UTC day while retaining explicitly hypothetical constant solar history.
  The midnight-crossing case, date validator and all numerical tolerances remain.
- Entire focused checkpoint command rerun:
  **41 passed, 1 upstream warning in 11.15 s**, exit 0. This includes zero-drag
  agreement with the original integrator, drag/energy/area-mass/density response,
  actual MSIS low/high-altitude trajectories, units, convergence and invalid data.
- Tightened rtol 1e-9→1e-11, position/velocity absolute tolerances and max-step
  120→60 s independently: final-position difference **4.229284e-5 m** in the
  controlled three-hour propagation (ordinary runtime **0.423904 s**).
  Direct-vs-prepared Astropy/ERFA geographic and actual MSIS comparisons passed
  on both sides of midnight. Density itself is never interpolated.
- Full `../.venv/bin/python -m pytest -q --maxfail=1`:
  **354 passed, 2 upstream warnings in 340.64 s**, exit 0; all 344 prior tests,
  no skips, deselections or weakened assertions. Bound to 90 modeled days and
  explicit computation budget. Osculating J2 oscillations/element altitude
  convention and fixed gravity pole limitations are disclosed in output.
- Boundary detection development began only after this successful gate.

## Phase 4 — Checkpoint 6: terminal atmospheric-boundary events

Status: PASSED.

- Added `app/physics/boundary.py` and descending terminal solve_ivp geodetic
  event to the verified propagator. Default 120 km; supported explicit cutoff
  80–500 km. Samples stop at the root, never through breakup or ground impact.
- Explicit seven prediction statuses distinguish bounded no-crossing, missing
  properties/weather, unsupported initial states, numerical/model failure and
  actual calculated crossing. No crossing time is fabricated when unavailable.
- Controlled synthetic orbit crossed at **1310.210038 s** from the initial
  epoch, **2026-10-09T12:21:50.210038Z**. Independently refined original
  NumericalTrajectory/direct Astropy altitude gave **1310.2100358172484 s**.
  Tightened integration, cutoff altitude agreement and all sample endpoints
  passed; a 130-km cutoff correctly occurred earlier.
- Focused boundary/decay/drag command: **32 passed, 1 warning in 8.72 s**,
  exit 0. Includes no crossing, below-cutoff initial state, missing inputs,
  isolated solver-failure handling, weather failure, budget exhaustion and
  invalid cutoffs. Failure injection tests status handling, not scientific
  answers; the event/time calculations are actual numerical dynamics.
- Full `../.venv/bin/python -m pytest -q --maxfail=1`:
  **363 passed, 2 upstream warnings in 334.61 s**, exit 0, all 354 prior tests.
  No skipped/deselected tests. Scenario work began only after this gate.

## Phase 4 — Checkpoint 7: explicit persistence scenarios

Status: PASSED.

- Added strict PersistenceSettings and separate LOW_DRAG/NOMINAL/HIGH_DRAG
  actual MSIS propagations. LOW/HIGH explicitly selected constant solar
  histories use F10.7=80/220 sfu, Ap=4/40. NOMINAL supports source-only,
  explicitly supplied constant assumptions, or explicitly supplied fallback
  beyond unavailable daily forecast coverage. No density multiplier shortcut.
- Optional ordered ballistic ratio range is explicitly supplied, must bracket
  nominal properties, and changes the scenario propagations. No hidden mass,
  area or Cd substitution. All source/assumed forcing provenance retained.
- Controlled 250-km synthetic orbit, 5,400 s, hypothetical Cd*A/m=0.022 m²/kg:
  calculated energy losses **1281.708607 / 2544.343251 / 4061.765142 J/kg**
  for LOW/NOMINAL/HIGH. Initial density and energy responses ordered correctly
  under these controlled assumptions; labels do not guarantee such ordering
  for every real storm or geometry. Independent fixed-weather ratio test passed.
- No-crossing scenarios retain null crossing times; ranges cover only reached
  scenarios. Failed scenarios remain explicitly present with individual status.
  Envelope states NOT a confidence interval/probability distribution.
- Actual source weather lookup retained SOURCE_FORECAST, and a date beyond
  complete daily coverage returned unavailable unless an explicit hypothetical
  fallback was supplied; the latter remained USER_SUPPLIED_ASSUMPTION.
- Focused scenario/boundary/decay tests: **29 passed, 1 warning in 20.51 s**,
  exit 0. Full suite: **373 passed, 2 warnings in 329.66 s**, exit 0,
  all 363 prior tests; no skips/deselections. Persistence service work began
  only after this gate passed.

## Phase 4 — Checkpoint 8: real-object persistence service

Status: PASSED.

- Added `app/persistence.py`, joining actual selected GP→SGP4→GCRS→explicit
  aerodynamic properties→weather/MSIS→drag→boundary→scenario metrics.
  Engine gains a lazily used SpaceWeatherClient; no startup download.
- Initial GP epoch restricted to seven days from the starting state, with
  explicit increasing long-horizon uncertainty. No indefinite SGP4 propagation,
  fabricated mass/area, BSTAR conversion or cleanup ranking.
- Instantaneous WGS84 geodetic altitude-band occupancy uses piecewise-linear
  returned samples, with explicit sampling limitations and unclassified time.
  It does not mix perigee/apogee orbital-element categories with altitude time.
  Modeled duration is conserved across disjoint bands; missing/failed results
  remain null/explicit rather than invented metrics.
- Actual external GP retrieval and real MSIS propagation succeeded:
  ISS 25544 epoch **2026-10-10T18:56:31.282080Z**, sampled initial altitude
  **420,688.571 m**, density **2.931826e-12 kg/m³**, propagation **0.077614 s**;
  NOAA 15 25338 epoch **2026-10-10T22:27:52.056288Z**, altitude
  **829,147.659 m**, density **5.888327e-15 kg/m³**, **0.051479 s**.
  Both correctly NOT_REACHED_WITHIN_HORIZON for **86.4 modeled seconds**.
  Supplied Cd*A/m=0.022 m²/kg was hypothetical, not actual spacecraft data.
- Focused persistence/scenario tests: **15 passed, 1 warning in 12.05 s**,
  exit 0, including source identity, actual trajectory, scenarios, provenance,
  missing properties and long-lived/no-boundary response.
- Full suite: **378 passed, 2 warnings in 634.71 s**, exit 0, all 373 prior
  tests; no skips/deselections. Runtime was longer than preceding gates;
  passive process inspection showed an active CPU-using test process, not a
  stopped runner. No coverage/timeouts/assertions were weakened. API/CLI work
  began only after the actual successful result.

## Phase 4 — Checkpoint 9: API and CLI integration

Status: PASSED.

- Four additive routes: space-weather status (explicit load), actual MSIS
  density, and per-object decay/persistence; validated Pydantic requests and
  responses preserve all eleven previous endpoints. No startup download.
- Both orbit endpoints reproduce independently invoked service trajectories
  exactly. Invalid horizons, boundaries, physical/weather values and naive
  timestamps return 422; missing physical properties have an explicit status.
  OpenAPI has fifteen paths and every local schema reference resolves.
- Interactive `persistence` prompts for catalog ID, hypothetical properties,
  horizon and scenarios; existing no-argument encounter interaction unchanged.
  Noninteractive physical inputs require explicit `--assume-properties`.
  Actual CLI subprocess retrieved ISS GP and invoked MSIS/propagation.
- Focused command:
  `../.venv/bin/python -m pytest tests/test_persistence_api_cli.py tests/test_api_engine.py tests/test_cli.py tests/test_startup.py -v -s --maxfail=1`:
  **25 passed, 2 upstream warnings in 47.81 s**, exit **0**; includes actual
  old API/CLI live flows and actual uvicorn HTTP startup.
- Full `../.venv/bin/python -m pytest -q --maxfail=1`:
  **392 passed, 2 upstream warnings in 381.78 s**, exit **0**, all 378 prior
  tests; zero failed/skipped/deselected. `git diff --check` exit 0.
  Final end-to-end/performance work begins only after this verified gate.

## Phase 4 — Checkpoint 10: end-to-end/performance (blocked)

Status: FAILED / STOPPED at the first mandatory test failure.

- Last fully verified implementation is commit `3755e03` (Checkpoint 9,
  **392 passing full-suite tests**). Checkpoints 1–9 passed. Phase 4 is NOT
  complete and has NOT been pushed as completed work.
- Added unverified local `app/persistence_benchmark.py` and
  `tests/test_persistence_end_to_end.py`; these remain uncommitted. Actual
  focused command, from backend:
  `../.venv/bin/python -m pytest tests/test_persistence_end_to_end.py tests/test_boundary.py::test_actual_event_matches_independent_existing_trajectory_and_converges tests/test_probability_end_to_end.py::test_actual_live_geometry_scenario_maneuver_optimizer_and_screening tests/test_persistence_api_cli.py::test_actual_cli_process_live_object -v -s --maxfail=1`.
- **5 tests collected; 1 failed, 2 warnings in 257.59 s; exit 1**. The other
  four tests were unrun after the hard stop, not passed or skipped. No final
  full-suite rerun, scenario/API benchmark, or completion claim was made.
- Actual live ISS GP, real cached weather and NRLMSIS 2.1 used hypothetical
  mass=100 kg, area=1 m², Cd=2.2 (NOT actual ISS properties), start
  **2026-10-11T08:23:58.254896Z**. One-day service **9.131337 s**
  (propagator **7.116039 s**, 10,862 derivatives), seven-day **64.298188 s**
  (propagator **63.402943 s**, 75,662 derivatives), both NOT_REACHED.
  Modeled total-energy changes −700.917382 / −3976.663930 J/kg, not observed
  spacecraft decay. Thirty-day **180.924076 s**, NUMERICAL_FAILURE, no
  trajectory/energy/crossing result fabricated.
- Actual error warning: **`Propagation computation budget exhausted; no
  complete lifetime prediction`**. Assertion:
  `assert report["benchmark_status"] == "COMPLETE"`, actual **BLOCKED**.
  No timeouts, tolerances or assertions were increased/weakened.
- Source snapshot remains 25,436 rows; last observed flux 2026-10-10;
  daily solar forecast 2026-10-11–2026-11-24, sufficient for this horizon.
  Same checksum as Checkpoint 2. Weather load **0.950778 s**, 100 actual
  density evaluations **0.005991 s**. The failure is the computation budget,
  not missing forecast coverage or a source HTTP error.
- Read-only diagnostic profile after stopping: warmed 3,600-second actual
  GP/MSIS propagation **0.445247 s**, 512 derivatives, exit 0. Integration
  **0.410 s**; force function **0.387 s**; 1,586 Earth-orientation rotation
  evaluations **0.126 s**, 1,074 geodetic conversions **0.128 s**;
  atmosphere wrapper **0.140 s**, pymsis itself **0.068 s**, drag validation/
  force **0.088 s** (cumulative categories overlap). Approximately three
  repeated rotations and two geodetic conversions per derivative, plus
  scalar model/validation overhead, are the likely scaling bottleneck.
- Proposed next step, **not implemented**: share the evaluated rotation/
  geodetic state across boundary-validity, density and drag calculations;
  retain real MSIS, input validation, integrator tolerance/step limits and
  independent frame/convergence tests. Requires user authorization before
  correcting or rerunning the failed checkpoint. Do not simply raise budget.

## Phase 4 — Checkpoint 10: authorized correction and rerun

Status: PASSED. All ten Phase 4 gates complete.

- User authorized the performance correction with "Ok fix" after the failure
  diagnosis. The failed run above remains part of the checkpoint record.
- Each numerical force evaluation now shares one Earth-orientation matrix,
  one validated geodetic position and its rotation-derived pole. The matrix
  cache is exact-epoch and read-only, not a changed interpolation scheme.
  MSIS still runs at every force evaluation; no density interpolation/cache.
- Aerodynamic parameters are validated once at the integration boundary;
  the constant effective ratio is reused. A private scalar cross-product
  kernel avoids generic broadcasting overhead; public drag validation and
  per-step finite-state/density/acceleration checks remain. UTC forcing is
  cached per explicit date/three-hour slot, with complete original provenance.
- Independent new tests: shared geometry/density exactly identical; 200
  deterministic varied-state drag outputs exactly match NumPy cross product;
  actual MSIS integration agrees with independently constructed legacy scalar
  DOP853 at absolute 1e-5 m / 1e-8 m/s. Existing coordinate/force/convergence/
  boundary/error tests rerun: **53 passed, 1 warning in 6.55 s**, exit **0**.
- All default settings preserved: rtol1e-9, position atol1e-4 m, velocity
  atol1e-7 m/s, max step120 s, timeout180 s. No fixture substitution, assertion
  weakening or scientific reference answers were introduced.
- Exact failed focused command rerun: **5 passed, 2 warnings in 197.23 s**,
  exit **0**. All five ran, no skipped/deselected tests. Includes actual GP/
  MSIS cases A–D, HTTP demonstration, controlled event E, existing live
  SOCRATES→optimizer→secondary screening→Pc case F and actual CLI subprocess.
- Successful benchmark initial time **2026-10-11T08:40:37.600652Z**;
  actual ISS GP epoch **2026-10-10T18:56:31.282080Z**, initial altitude
  **429,151.012 m**; NOAA15 epoch **2026-10-10T22:27:52.056288Z**, altitude
  **796,864.893 m**. Properties mass100 kg/area1 m²/Cd2.2 are explicitly
  hypothetical; this is not modeled actual spacecraft operation.
- ISS one/seven/thirty-day total service times **4.804103 / 25.367500 /
  110.148508 s**, propagator **3.203875 / 24.363831 / 108.928555 s**,
  derivatives **10,862 / 75,662 / 324,062**. All NOT_REACHED_WITHIN_HORIZON;
  thirty-day total-J2 energy change **−14,321.601139 J/kg**. Instantaneous
  osculating a increased3,025 m due to J2/sample phase, while first/last
  period-window sample means changed −2,768.982 m; neither is an observed
  decay rate. The returned warnings explicitly distinguish these quantities.
- One-day ISS/NOAA15 energy changes **−703.525453 / −3.668677 J/kg**, initial
  densities **1.011833e-12 / 1.211141e-14 kg/m³**, both no boundary crossing.
  Higher-altitude case correctly showed insignificant drag-energy change.
- Same real orbit/properties, LOW/source-NOMINAL/HIGH one-day energy losses
  **240.931066 / 703.525453 / 2915.748964 J/kg**, distinct real MSIS densities.
  Same source weather with doubled hypothetical Cd*A/m=.044 produced
  **1409.021878 J/kg** loss. Scenario ordering is case-specific, not confidence.
- One-day refined actual GP/MSIS trajectory differed **0.178230 m** at its
  final position (<1 m convergence criterion; not a physical accuracy claim).
  Three-hour controlled refinement remained **4.229284e-5 m**. Boundary event
  **1310.210038 s**, independent **1310.210035817 s**, tightened solve <.002s.
- Actual timings: weather cache load/parse **0.706516 s**; 100 MSIS density
  evaluations **0.005747 s**; 100 direct/prepared coordinate queries
  **0.536491 / 0.001270 s**; three one-day scenarios **12.415627 s**;
  actual uvicorn HTTP decay/persistence (.01-day horizon) **1.450458 /
  0.635269 s**, both HTTP200 and NRLMSIS provenance. Owned server stopped.
- Existing actual encounter `socrates-f3f9e438db4c8a81fa4b93e5` still optimizer
  COMPLETE, 13 evaluations; bounded screening INCOMPLETE, 4 considered of
  19,505 available records. Live covariance Pc UNAVAILABLE_NO_COVARIANCE,
  MAX_PROB1 remains separate; assumed baseline/postmaneuver Pc unchanged
  **6.304736762114633e-7 / 5.926506440598308e-7**.
- README documents inputs, model/version, source coverage, scenario provenance,
  API/CLI examples, boundary semantics, benchmarks, new modules and limitations.
  `pip check` exit0/no broken requirements.
- Final full command, from backend:
  `../.venv/bin/python -m pytest -q --maxfail=1`:
  **397 passed, 2 upstream warnings in 529.01 s**, exit **0**; zero failed,
  skipped or deselected. All 392 previous tests plus five new final/performance
  tests executed, including the complete real-data benchmarks again. This is
  all 302 Phase 3 regressions plus 95 Phase 4 tests. No assertion weakening.
- Warnings remain upstream Starlette/AnyIO deprecation and read-only optional
  Astropy cache, with installed offline IERS data used. `git diff --check`
  exit0. No frontend, cleanup ranking/optimization, operational reentry/impact
  model or replacement of the collision-avoidance simulator was introduced.
- Completed changes are ready for the standing commit/push workflow only now
  that the actual final full regression has passed. Remote main was verified
  still at the expected Phase 3 commit `23aa4c423155d99284f470853e33030a0241e00a`,
  so publication can be a normal fast-forward, never a force push.

## Phase 3 verified checkpoints

## Phase 3 — Checkpoint 1: preserve the existing backend

Status: PASSED (2026-10-11). Phase 3 uses the current task's explicit
fix-and-retest policy, stopping after three substantial unsuccessful attempts
on the same blocker; earlier phase failure policies below are historical.

- Baseline commit: `28130d7bc1b76bd2af3d3bb16570b2a59e8615b9`, preserved by
  Git tag `phase2-before-collision-probability`; initially clean worktree.
- Inspected state/GP models, frame transforms, encounter search, numerical
  simulation, clearance optimizer, secondary screening, API, CLI and tests.
- Reuse SI `StateVector`, actual TEME/GCRS conversions, each object's RTN
  basis, existing relative-state encounter results and verified simulations.
  NASA inertial frame labels must not be silently relabeled as GCRS.
- Ran `cd backend && ../.venv/bin/python -m pytest -v -s --maxfail=1`:
  **197 passed, 2 upstream warnings in 283.90 s**, exit **0**.
- Actual SOCRATES ingestion: **195,282 encounters**, zero invalid rows;
  three actual GP encounter/optimizer/secondary flows passed. Actual API
  and CLI screening demonstrations passed; uvicorn served actual HTTP health.
- Available bulk catalog: **19,505** objects, declared partial/stale coverage.
  Secondary screening correctly returned INCOMPLETE, not a safety guarantee.
  Broad API/CLI checks each considered 5,518 objects within a 15-second limit.
- Offline Astropy cache/read-only warning and upstream AnyIO deprecation do
  not affect successful scientific or startup assertions. No baseline tests
  skipped or weakened. No Phase 3 implementation preceded this gate.


## Phase 3 — Checkpoint 2: NASA CDM ingestion

Status: PASSED. Four unmodified KVN CDMs, the NASA README and precise
reference workbook downloaded from pinned NASA commit
`ce0f00722c56808755ee0adbe47a4e3d56439484`. Both object states, per-object RTN
position covariances, EME2000 frame, UTC TCA, explicit km/km/s/m² units,
combined header HBR and rounded reference Pc verified against actual metadata.
Unknown metadata (including DCP correlations) is retained. Unsupported frames,
units, missing covariance/state fields, duplicate fields and non-PSD matrices
are rejected. Missing optional radius/Pc remains absent, never fabricated.
Historical source identity is separate from live SOCRATES. Original workbook
SHA-256: `dcb1f5bf51703ee793582d21b1f669dc388d9eb0b9f4b3871f13055cc885eb85`.
NASA scripts specify an independent Pc2D benchmark and local linear TCA
correction; this is not a claim of calibrated risk despite DCP metadata.

- Targeted command: `../.venv/bin/python -m pytest tests/test_probability_cdm.py -v --maxfail=1`:
  **13 passed in 0.42 s**, exit **0**.
- Full command: `../.venv/bin/python -m pytest -q --maxfail=1`:
  **210 passed, 2 warnings in 267.09 s**, exit **0**; all 197 previous tests
  rerun, including actual source, optimizer, screening, API/CLI and startup.

## Phase 3 — Checkpoint 3: covariance mathematics

Status: PASSED. Implemented SI 3x3 validation, orthogonal transformations,
individual object RTN/RIC bases, real TEME/GCRS rotations using existing
Astropy utilities, common-frame relative covariance and 2D projection.
EME2000/GCRF are retained without relabeling; unsupported cross-frame
conversions and epoch mismatches fail clearly. Known correlation requires
cross-covariance, including a PSD joint 6x6 check; relative covariance is
P1+P2−C12−C12ᵀ. Unspecified correlation requires a disclosed independence
assumption. PSD tolerance is 64 machine eps times spectral norm, solely for
roundoff; eigenvalues are never clipped. Zero relative velocity is unsupported.

- Targeted reader/math suite: **32 passed, 1 warning in 2.40 s**, exit **0**.
- Full `../.venv/bin/python -m pytest -q --maxfail=1`:
  **229 passed, 2 warnings in 269.02 s**, exit **0**. Identity, analytical
  rotation, round trip, symmetry, PSD/invalid matrices, correlated examples,
  distinct object RTN orientations, plane basis/projection, actual NASA
  rotations and all 210 previous tests passed.

## Phase 3 — Checkpoint 4: actual probability integration

Status: PASSED after one evidence-based test-oracle correction. Initial actual
targeted run failed (exit 1, 1 failed/3 passed) comparing rare isotropic Pc:
integral `3.047134968841445e-73`, SciPy 1.15.3 `ncx2.cdf`
`3.047134125939165e-73`. An independent positive-term Poisson/incomplete-gamma
analytical expansion gave `3.0471349688414093e-73`; tightening quadrature
from 1e-7 to 1e-12 converged to `3.0471349688414665e-73`. Cause: loss of
accuracy in the extreme-tail reference CDF, not the disk integral. Replaced
that test oracle with the converged analytical series, retained the original
2e-9 relative assertion and added 128/256-term series convergence checks.
Ordinary probabilities still independently cross-check `ncx2.cdf`.

The engine performs actual Gaussian disk integration, analytic inner normal
CDF and adaptive outer quadrature, with log-CDF tail differences. Missing
radius/covariance and invalid matrices are rejected. Zero relative velocity,
singular/condition>1e12 projected covariance, known missing cross-covariance
and explicitly inapplicable rectilinear models return unsupported, not Pc.
Numerical convergence/error and underflow are explicit. Physical covariance
realism and rectilinear applicability are assumptions, not certified from
instantaneous states; numerical error is not physical uncertainty.

- Rerun all current probability tests: **52 passed, 1 warning in 2.92 s**, exit 0.
- Full `../.venv/bin/python -m pytest -q --maxfail=1`:
  **249 passed, 2 warnings in 285.68 s**, exit **0**, all prior tests rerun.

## Phase 3 — Checkpoint 5: scientific NASA validation

Status: PASSED. Precise expected values read from the original NASA workbook
Pc2D column, not rounded CDM headers. Covariances rotated using each object's
original EME2000 state; encounter-plane projection applies the local linear
closest-approach correction. Original inertial covariance is fixed only over
the actual <0.5 ms rounding correction. NASA `PcMultiStep_FromCDM.m` explicitly
sets `apply_covXcorr_corrections=false` (line 190 at the pinned commit).
The adapter requires explicit `independent_benchmark=True` and labels this as
historical independent-model validation, not risk for the correlated encounter.

| Actual fixture pair/date | NASA precise Pc2D | Kessler Pc | Relative difference |
| --- | --- | --- | --- |
| Terra / Iridium 33 debris, 2021-03-24 | 0.021173811560368256 | 0.021173811560374473 | 2.94e-13 |
| Terra / SL-16 debris, 2022-09-28 | 0.00010824948102737557 | 0.00010824948102745792 | 7.61e-13 |
| HST / Delta 2 R/B(1), 2021-03-15 | 0.0006114793230828587 | 0.000611479323158796 | 1.24e-10 |
| Swift / Jilin-01 Gaofen 2A, 2022-04-07 | 0.0023236849651128103 | 0.00232368496509251 | -8.74e-12 |

Relative assertion tolerance **2e-9**, absolute tolerance **0**, justified by
requested quadrature accuracy 1e-9, not the rounded-header precision. Retesting
at 1e-11 quadrature tolerance confirms convergence. Altered reference metadata
leaves calculated Pc unchanged; scientific answers are not hardcoded.

- Actual reference command: `../.venv/bin/python -m pytest tests/test_probability_reference.py -v -s --maxfail=1`:
  **6 passed in 1.29 s**, exit **0**.
- Full `../.venv/bin/python -m pytest -q --maxfail=1`:
  **255 passed, 2 warnings in 259.45 s**, exit **0**, all prior tests rerun.

## Phase 3 — Checkpoint 6: live availability and uncertainty scenarios

Status: PASSED. All five required availability states implemented. Inputs
require explicit covariance kind (SUPPLIED/ASSUMED), per-object matrices,
frames, aware epochs and combined HBR; optional IDs are checked against the
selected pair. Invalid/missing fields cannot produce Pc. Known correlations
without cross-covariance and incompatible epochs/frames are unsupported.
Assumed covariance outputs carry exactly:
`ILLUSTRATIVE — USER-SUPPLIED UNCERTAINTY ASSUMPTIONS.`
No covariance, radius or independence for known correlations is fabricated.

- Actual source case `socrates-f3f9e438db4c8a81fa4b93e5`, retrieved GP and
  refined SGP4 TCA `2026-10-13T05:09:03.226914Z`: preserved real SOCRATES
  `MAX_PROB=1.0`, returned **UNAVAILABLE_NO_COVARIANCE**, calculated Pc null.
  Historical NASA references are explicitly rejected by the live adapter.
- Targeted `tests/test_probability_availability.py`: **12 passed in 7.37 s**,
  exit **0**, including an actual live-source geometry flow.
- Full `../.venv/bin/python -m pytest -q --maxfail=1`:
  **267 passed, 2 warnings in 258.41 s**, exit **0**, all 255 prior tests rerun.

## Phase 3 — Checkpoint 7: maneuver probability comparison

Status: PASSED after correcting one new test's wrong existing field name.
Initial targeted run: **1 failed, 3 passed**, exit **1**;
`AttributeError: 'ManeuverOption' object has no attribute 'predicted_miss_distance_m'`.
Inspection confirmed the existing field is `new_miss_distance_m`; corrected
the assertion without changing the optimizer or weakening its condition.

Comparisons require explicit `fixed_covariance=true`. Both individual object
covariances are rotated at original analyzed SGP4 TCA and frozen in GCRS.
Actual matched zero-burn and modified simulator relative states supply each
calculation; no simulator replacement, covariance propagation or Pc objective
is introduced. Output discloses published/original/baseline/modified TCAs,
covariance epoch, offsets, baseline Pc, modified scenario Pc and delta Pc.
Both values are illustrative even if the original matrices were supplied,
because their validity at shifted TCAs is not established. Wrong epochs are
unsupported. Results are tested not to mutate the simulation.

- Corrected checkpoint plus existing optimizer/maneuver tests:
  **18 passed, 1 warning in 16.64 s**, exit **0**.
- Full `../.venv/bin/python -m pytest -q --maxfail=1`:
  **271 passed, 2 warnings in 262.27 s**, exit **0**, all prior tests rerun.

## Phase 3 — Checkpoint 8: API and CLI

Status: PASSED. Added `POST /api/probability/calculate` for explicit SI
common-frame geometry/covariance requests and explicitly acknowledged
historical NASA reference benchmarks. Optional `probability_analysis` /
`probability_inputs` on analyze and `probability_scenario` on simulate.
Default response JSON is unchanged (verified exact equality). Optimizer,
screening, health, object and discovery endpoints retain their behavior.
The existing exact route-set assertion now includes the one required new
probability route while retaining all ten previous routes.

CLI supports NASA reference selection/listing, independent calculation,
published precise and rounded Pc and numerical differences; live availability;
explicit covariance JSON; direct calculation JSON; and acknowledged fixed
covariance maneuver scenarios. No frontend or network access is required for
NASA fixture evaluation. Missing files and invalid input return nonzero exit.
OpenAPI schemas and all local references validated.

- Focused new plus original API/CLI tests: **30 passed, 2 warnings in 43.95 s**,
  exit **0**.
- Actual NASA CLI process exited **0**; Terra/Iridium Pc
  `0.021173811560374473`, difference `6.217248937900877e-15` from precise NASA.
- Actual live CLI process exited **0**, retrieved/refined real case
  `socrates-f3f9e438db4c8a81fa4b93e5`: MAX_PROB **1.0** separately,
  Pc **UNAVAILABLE_NO_COVARIANCE**, calculated Pc null.
- Full `../.venv/bin/python -m pytest -q --maxfail=1`:
  **291 passed, 2 warnings in 279.38 s**, exit **0**, all 271 prior tests rerun.

## Phase 3 — Checkpoint 9: final end-to-end verification

Status: PASSED. All nine Phase 3 hard gates passed sequentially.

- Actual command: `../.venv/bin/python -m pytest tests/test_probability_end_to_end.py -v -s --maxfail=1`:
  **11 passed, 2 warnings in 27.63 s**, exit **0**. Four NASA CLI subprocesses
  and actual uvicorn HTTP reference evaluations passed, using genuine CDM
  states, individual covariance rotations and independent integration.
- Actual live geometry/scenario/maneuver/optimizer/screening flow:
  `socrates-f3f9e438db4c8a81fa4b93e5`; real MAX_PROB **1.0**, live Pc
  **UNAVAILABLE_NO_COVARIANCE**. Explicit anisotropic user-assumption scenario
  SGP4 Pc **6.299418159696612e-7**; matched numerical baseline scenario Pc
  **6.304736762114633e-7**; modified scenario Pc **5.926506440598308e-7**;
  delta **-3.782303215163255e-8**. These are scenarios, not measured risk.
- Original analyzed TCA **2026-10-13T05:09:03.226914Z**; matched numerical
  baseline **05:09:03.265412Z**; modified **05:09:03.383474Z**. Covariances
  remain frozen at the original TCA, with no validity claim at shifted times.
- Existing optimization returned **COMPLETE**, **13** actual simulations and
  primary solutions; optional REPORT_ONLY screening returned **INCOMPLETE**
  against a partial/stale **19,505-object** catalog (3 considered within its
  declared 5-second/max-256-object cap), with no screening-policy pass.
  Broader original screening pipelines are additionally rerun in the full suite.
- Actual Pc benchmark: 30 samples per case, 120 total; medians / p95 in ms:
  HST **1.645 / 3.035**, Terra/SL-16 **1.656 / 2.664**, Terra/Iridium
  **1.459 / 1.935**, Swift **1.324 / 1.898**. Excludes input parsing, frame
  setup, imports and transport. Largest observed relative NASA difference
  **1.242e-10**. QUADPACK absolute estimates **4.378e-13 / 2.973e-14 /
  2.009e-11 / 2.132e-12** respectively, strictly numerical quadrature only.
- Hardened malformed optional velocity-covariance record rejection, numerical
  covariance scale rejection, and degenerate GCRS RTN-basis handling; tested
  real CLI direct-input files and explicit inapplicable-model API responses.
- README includes actual reference/API/CLI usage, all five availability states,
  matrix units/epochs/frames, explicit assumptions and limitations. Bundled
  direct example is synthetic and explicitly ASSUMED; actual CLI exit **0**,
  scenario Pc **0.0006783652889144094**, never labeled a live encounter.
- Final full command: `cd backend && ../.venv/bin/python -m pytest -q --maxfail=1`:
  **302 passed, 2 warnings in 297.29 s**, exit **0**. All **197** original
  tests plus **105** Phase 3 tests; zero failures, skips, deselections or
  disabled assertions. Actual source, API/CLI, startup, optimizer, secondary
  screening and all scientific reference regressions rerun successfully.
- All stages preserved in separate verified Git commits; pre-Phase-3 baseline
  tagged `phase2-before-collision-probability`. `git diff --check` passed.
  Remote main was verified at baseline `28130d7` before publication, with no
  divergence. Completed changes are published to origin/main under the user's
  standing commit-and-push workflow; remote hash is verified before handoff.
  No dependency, frontend, decay, cleanup or default optimizer changes.

## Historical Phase 1 and Phase 2 records

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
