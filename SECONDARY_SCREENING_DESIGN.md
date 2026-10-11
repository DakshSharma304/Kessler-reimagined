# Phase 2 integration design

The preserved Phase 1 reference is commit `714bfb5`, tagged
`phase1-before-secondary-screening`. This records the inspected reuse interfaces
and implemented extension. Executed verification and current checkpoint status
are recorded separately in `CHECKPOINTS.md`.

## Existing interfaces to reuse

| Component | Actual interface and behavior | Phase 2 use |
| --- | --- | --- |
| Orbital elements | Frozen `GPElements` in `app/models/orbital.py`; OMM input aliases, string catalog ID, aware UTC epoch, Earth/TEME/SGP4; `initialize_sgp4()` returns `Satrec` | Validate bulk/local catalog records with the same model |
| Source/cache | `CacheRecord`, `FileCache.read/write`, `make_record` in `app/data/cache.py`; atomic files with SHA-256 payload integrity and source/fetch timestamps | Cache bulk snapshots without per-object downloads |
| Individual GP retrieval | `CelestrakClient.get_object(id)` and `get_encounter_objects(encounter)`; two-hour refresh limit; seven-day epoch suitability | Keep existing selected-case retrieval unchanged |
| Propagation | `propagate_object(orbit, timestamp)` returns `StateVector` with SI position/velocity, exact aware timestamp and explicit TEME frame | Nominal single-time evaluation; vectorized library SGP4 for catalog batches |
| Frames | `teme_to_gcrs(state)`, `earth_pole_gcrs(timestamp)`, `rtn_basis(state)` in `app/physics/frames.py`; installed offline IERS data | Consistent GCRS state differences and RTN impulses |
| Numerical trajectories | `NumericalTrajectory(initial, end, pole, start=None, rtol=1e-9)`; callable dense DOP853 output in GCRS, central gravity/J2, SI units | Matched no-burn and post-impulse trajectories over the screening interval |
| Primary closest approach | `analyze_encounter(...)`; `refine_closest_approach(first, second, start, end)` limited to a local interval of at most one hour | Preserve primary calculation; add a separate multi-minimum, longer-window search |
| Shared primary reference | `MatchedDynamics(encounter, first, second, anchor, reference)` initializes both numerical orbits at one common anchor | Retain optimizer anchor when constructing finalist differential trajectories |
| Maneuver simulation | `simulate_maneuver(...)` applies one RTN impulse, retains pre-burn nominal states and compares against matched zero burn | Leave primary simulation behavior unchanged |
| Candidate representation | `ManeuverOption`: burn time, RTN vector/norm, modeled primary clearance, primary improvement, target flag, TCA and matched baseline | Screen actually evaluated finalists; preserve primary metrics |
| Optimizer ranking | `optimize_maneuver(..., constraints, search=None, now=None)`; `objective_key` ranks clearance descending or delta-v ascending | Add an optional retained finalist pool/post-processing hook; do not replace coarse search or refinement |
| API | Shared `Engine` dependency; typed routes in `app/api/routes.py`; `OptimizeRequest` extends `ManeuverConstraints` with `search` | Add optional screening settings and separate catalog/status and screen routes |
| CLI | `app.cli.main`, interactive flow and JSON list/analyze/simulate/optimize subcommands | Add optional screening, preserving unscreened invocation behavior |

## Implemented extension

1. Load verified public GP groups, local OMM JSON/CSV and explicitly selected
   persistent GP caches into a deduplicated snapshot. Report partial coverage,
   rejected data, source checksums, retrieval times and epoch ranges.
2. Use typed screening requests, bounded windows and explicit incomplete and
   unavailable statuses. A proximity threshold is illustrative, never SAFE.
3. In GCRS, form `nominal SGP4 + (maneuvered numerical - zero-burn numerical)`
   for position **and velocity**, with identical numerical force models and
   reference epoch. Zero impulse must recover nominal SGP4. This differential
   approximation does not establish physical prediction accuracy.
4. Screen one object against available catalog objects using batched SGP4,
   segment-relative-motion filtering with a documented curvature margin, and
   continuous-time local refinement. Include the original counterpart but
   distinguish it from additional objects. No mathematical completeness claim.
5. Compare the same snapshot/window for baseline and maneuvered trajectories,
   matching events by time rather than catalog ID alone. Bound runtime/workload
   and expose skipped/stale/failed records and any incomplete search.
6. Optionally screen a small ranked finalist set, then apply REPORT_ONLY,
   REJECT_NEW_ALERTS or REJECT_ALL_ALERTS. Preserve the primary objective and
   constraints; incomplete screening never qualifies as a policy pass.

Every numbered implementation checkpoint is a hard gate. The user's instruction
to stop and report the first failed checkpoint overrides the pasted instruction
to attempt fixes automatically. No frontend, covariance/Pc or cleanup work is
included.
