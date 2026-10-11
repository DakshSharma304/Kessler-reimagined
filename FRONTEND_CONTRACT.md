# Kessler frontend integration contract

Backend only. No frontend or JavaScript orbital physics is included.
This contract is an integration specification; readiness is claimed only after
the final checkpoint passes. Scientific limitations must remain visible in UI.

## Startup and configuration

From repository root (Python3.12; pinned backend/requirements.txt):

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cd backend
../.venv/bin/python -m app.server
```

When the existing environment is installed, only the final two lines are needed.
On Windows use the virtual environment's `Scripts/python.exe` equivalent.
API base URL: `http://127.0.0.1:8000/api`; OpenAPI: `http://127.0.0.1:8000/openapi.json`.
Local port8000; docs `/docs`. Configure the separately hosted frontend's backend
base URL in its deployment configuration; the backend does not determine a
production public URL or implement a frontend build system.

Environment variables are read from the process (the `.env.example` is not
automatically loaded; no dotenv dependency):

| Variable | Default / meaning |
| --- | --- |
| KESSLER_HOST | 127.0.0.1; use0.0.0.0 only when intentionally exposing server |
| KESSLER_PORT | 8000; integer1..65535 |
| KESSLER_ENV | development; production defaults to no allowed browser origins |
| KESSLER_ALLOWED_ORIGINS | JSON array of exact origins; dev localhost/127.0.0.1 on5173/3000 |
| KESSLER_CACHE_DIR | .cache/kessler relative to backend working directory |
| KESSLER_DATA_DIR | data; base for configured relative dataset filenames |
| KESSLER_CATALOG_FILES | JSON array of actual OMM files; when nonempty browser uses this explicitly local scope instead of downloading public groups |
| KESSLER_METADATA_FILE | Optional documented SATCAT CSV; LOCAL/offline provenance, not live classification |
| KESSLER_MAX_CALCULATIONS | 2 concurrent expensive calculations; configurable1..8 |

Production example (replace the public hostname with your actual frontend origin):

```bash
KESSLER_ENV=production KESSLER_HOST=0.0.0.0 KESSLER_PORT=8000 \
KESSLER_ALLOWED_ORIGINS='["https://your-frontend.example"]' \
../.venv/bin/python -m app.server
```

CORS permits GET/POST/OPTIONS and Content-Type, without credentials. Wildcard,
path-bearing and non-HTTP(S) origins are rejected. No authentication: hackathon
prototype for trusted deployment/network use; CORS is not access control.
Missing configured files and malformed variables fail clearly at startup.
No developer-specific absolute path is required.

## Public API and exact schemas

All21 paths /22 GET+POST operations and every request/response schema are in
the generated appendix below and the checked-in `openapi.json`. `/openapi.json`
from your running backend is authoritative. Existing scientific endpoints are
retained; use new visualization routes rather than interpreting raw states as
Earth-fixed. Unknown fields are generally rejected on calculation inputs.

GET health/status/catalog-status do not download live sources. First catalog or
encounter request may parse/download substantial public datasets; show loading
state. Catalog status reports last loaded catalog, which may be a screening
scope, so use each result's own catalog metadata for its authoritative coverage.

## Units, time and Three.js coordinate contract

- All visualization positions: Earth-centered Earth-fixed **ITRS/ECEF**, **km**,
  UTC ISO8601 timestamps with Z or explicit offset. `frame: ITRS`,
  `position_units: km`. Proper Astropy conversion from SGP4 TEME/numerical GCRS.
- Three.js right-handed Y-up: `(x,y,z)ITRS -> (x,z,-y)`. Use one world unit/km
  or one consistent display scale. WGS84 Earth equatorial radius6378.137km.
  Earth-fixed paths rotate with Earth, not closed inertial orbital ellipses.
- Existing scientific states: `position_m`, `velocity_m_s`, TEME or GCRS;
  covariances m²; combined hard-body radius m; delta-v RTN m/s. Do not send
  ITRS display coordinates to an inertial Pc request. Distances with `_km`
  are km, those with `_m` are m. Inclination deg, mean motion rev/day,
  persistence horizon days, durations/solver steps seconds, density kg/m³.
- IDs are canonical positive numeric NORAD **strings**, including six-digit
  IDs. Encounter IDs are opaque SOCRATES IDs, not object IDs.
- SATCAT classification is PAYLOAD/ROCKET_BODY/DEBRIS/UNKNOWN. GP
  `elements.classification` is a security marking, NOT debris classification.
  Unknown status is not operational confirmation or cleanup eligibility.

## Catalog, pagination, times and payload bounds

`GET /api/objects`: search name/ID substring, optional classification, offset
0..1000000, limit1..500; `total`, `next_offset` and metadata returned. Stable
numeric-ID order. This is a partial public GP population, not every tracked
object. `POST /api/positions`:1..2000 IDs before deduplication, optional aware
epoch (default UTC now), one batch call. Unsupported epochs beyond±7days of
elements return per-object UNSUPPORTED_EPOCH; SGP4_ERROR and NOT_IN_CATALOG
have null positions/error strings. Render only statusOK; never render missing
coordinates as the Earth center. Successful coordinates are finite.

Object orbit: optional start_time/end_time, default now and up to one orbital
period, interval≤24h, samples2..1001. Both endpoints must be within±7days of
GP epoch. Nominal encounter trajectories: sample_count2..1001, TCA-centered
half-window>0..1800seconds. GET encounter list supports limit1..1000, offset,
sort screening/max_probability/minimum_separation/time, object_id/name and
inclusive aware start_time/end_time. Only upcoming predictions are returned;
these are filters, not historical-state reconstruction. Existing list response
has no total/next_offset; request the next offset until items is empty/short.

## Six frontend workflows

### A — Orbital exploration

GET objects → POST positions (one bounded batch) → GET selected object's
metadata → GET object trajectory. Existing GET objects/{id} returns raw GP
and provenance; metadata route additionally joins supported classification.
Do not request individual positions through thousands of HTTP calls.

### B — Close approaches

GET encounters → GET selected encounter → POST analyze → GET trajectories.
Published SOCRATES TCA/separation are distinct from recalculated local minimum;
show source/model disagreement, searched window, status and warnings.

### C — Maneuver planning

POST optimize with URL/body encounter_id equal, participant ID and explicit
hypothetical capability. Existing clearance objectives remain MINIMUM_DELTA_V
or MAXIMUM_CLEARANCE, never default Pc minimization. `solutions` contains best
evaluated alternatives, not a global-optimum guarantee. For each chosen option
POST encounter trajectories with its time/delta-v AND the optimizer's
`numerical_reference_epoch`: response has matched baseline, modified and
counterpart ITRS paths plus simulator geometry. Up to1001 samples over the
bounded48-hour model. Using a different anchor changes the comparison model.
POST screen for each selected alternative, or request existing optimize
secondary_screening mode. SCREENED_WITHIN_COVERAGE is only computation within
partial declared coverage, not flight safety; ALERTS_FOUND/INCOMPLETE/UNAVAILABLE
must be visible. Skipped objects, thresholds and time cap matter.

### D — Collision probability

Analyze `probability_analysis:true` returns probability_status,
socrates_max_probability separately, calculated_pc nullable, assumptions and
warnings. Live SOCRATES has no measured covariance: UNAVAILABLE_NO_COVARIANCE.
Never display MAX_PROB as true Pc. SUPPLIED valid matrices can produce
CALCULATED_FROM_SUPPLIED_COVARIANCE (provenance not independently verified).
ASSUMED inputs yield SCENARIO_WITH_ASSUMED_COVARIANCE and the required label
**ILLUSTRATIVE — USER-SUPPLIED UNCERTAINTY ASSUMPTIONS.** Invalid inputs either
fail422 validation or report UNAVAILABLE_INVALID_COVARIANCE/UNSUPPORTED_MODEL.
Covariances require explicit matrix/frame/epoch; radius is combined radius.
NASA reference cases are HISTORICAL_REFERENCE/reference_only, never live
encounters; the independent benchmark acknowledgement is mandatory because
reference metadata includes known correlation distinctions. Four genuine cases
are enumerated in README/reference fixtures, not current CelesTrak propagations.

POST simulate accepts optional fixed covariance scenario. Always show covariance
treatment, original/modified TCA, baseline/modified Pc and deltaPc; no covariance
propagation or operational calibration. These do not change default optimizer.

### E — Decay/persistence

POST objects/{id}/persistence or existing decay alias with explicit physical
parameters or Cd*A/m, input category, horizon and weather treatment. No inferred
mass/area from BSTAR. NOMINAL/COMPARE supports actual NRLMSIS2.1; compare presets
and selected constant solar history are hypothetical, not weather confidence
intervals. SOURCE_ONLY refuses unavailable coverage rather than extrapolating.
Without object properties, statusINSUFFICIENT_OBJECT_PROPERTIES and no trajectory.
NOT_REACHED_WITHIN_HORIZON is censored, not infinite lifetime. BOUNDARY_REACHED
is a geodetic model cutoff, not ground impact or precise reentry prediction.

Set `visualization:true` for compact response `{object_id,prediction_status,
analysis,trajectories,warnings}`. Analysis contains original PersistenceAnalysis
fields except each successful propagation's `samples` is explicitly null with
`sample_status: OMITTED_FROM_COMPACT_VIEW` and `original_sample_count`. Actual
ITRS samples (max1001/scenario) are in trajectories keyed LOW_DRAG/NOMINAL/
HIGH_DRAG; missing/failed scenario has no path and keeps its analysis status.
Metrics were computed from full original samples; subsampling is for display.
Default false preserves the complete original scientific response. Available
nominal evidence is retained in-memory for cleanup (max256objects, one-day
initial-epoch freshness); ordinary browsing never runs atmospheric physics.

### F — Cleanup prioritization

GET objects filtered DEBRIS/ROCKET_BODY → POST cleanup/optimize with candidate_ids,
constraints and policy. Default policy is an **illustrative decision policy**:
exposure=count capped/10; optional persistence=modeled_days capped/30;
optional RCS=log1p(RCS)/log1p(10) capped. Weights normalized once, not reweighted
for missing metadata. A positively weighted unknown yields null score,
INSUFFICIENT_EVIDENCE and a possible score interval—not fabricated zero.
RCS is radar reflection, NOT mass/dimensions/aerodynamic or collision area.
Quality gates comparability/eligibility, never rewards more available metadata.
Active objects, payloads (even defunct), unknown types, decayed/docked/non-Earth
objects and unsupported GP epochs are excluded. No verified removal feasibility.

max_targets bounds target count; optional effort_costs map and effort_budget are
user-defined **abstract units, not dollars**. Missing costs are excluded. MILP
status must be respected; PARTIAL is feasible but optimality unverified. Selection
reasons, component contributions, total expenditure/budget remaining, exclusions,
unknown fields, unique/shared conjunction IDs and coverage are returned.
Default candidate scope is at most200eligible public objects in NORAD order,
not global prioritization; max_candidates≤1000 or supply explicit bounded IDs.
SOCRATES counts are predicted exposure in a limited dataset/window, not actual
long-term collision frequency. Additive proxy is never collisions prevented.

## Errors, latency and data provenance

-404 scientific NOT_FOUND: unknown encounter ID. Missing public orbital data
  uses existing503UNAVAILABLE; do not silently invent a record.
-422: either `{status:UNSUPPORTED,detail:string}` scientific error or FastAPI
  `{detail:[{loc,msg,type,input?,ctx?}]}` input validation. Both shapes are
  explicitly in OpenAPI. Do not read a Pc/trajectory from failed requests.
-429 BUSY: configured concurrent scientific capacity reached; show waiting and
  retry with backoff. No job ID, async job infrastructure or queued calculation.
-503 UNAVAILABLE: required live source/orbital/weather data unavailable.
  Catalog/cleanup can instead return explicit unavailable/partial status200
  with null fields, warnings and failed_sources; inspect calculation status.
-500 unexpected server defect: show failure, retain request information; do
  not report success. Transport timeouts do not prove the server stopped work.

Requests are synchronous. Source loading can take tens of seconds cold.
Warm positions/search/orbits/Pc are interactive; optimization/screening obey
explicit time/evaluation caps. Secondary defaults30seconds, upper300; optimizer
defaults25seconds, upper120. Persistence per-scenario defaults180seconds,
upper600, COMPARE has three scenarios; horizon≤90days does NOT ensure completion.
Use explicit short horizons for interactive scenarios, show progress/waiting
state and configure HTTP/proxy timeouts accordingly. Do not calculate decay
on catalog page load. Raw scientific persistence can contain up to20000samples/
scenario; prefer visualization compact mode. Final measured workloads are
recorded in CHECKPOINTS.md, not universal latency promises.

GP sources have URLs/checksums/fetched_at/element epochs, catalog snapshot hash,
coverage PARTIAL/freshness FRESH/STALE/UNAVAILABLE, failed sources and limitations.
SOCRATES responses include source URL/hash/dataset timestamp/VALID or STALE_CACHE.
Classification metadata has source/hash/retrieval mode (HTTP/CACHE/STALE_CACHE/
LOCAL). Local file mtime is not a verified publication date. A source failure
halts further source queries in that client until restart/operator action;
valid stale data remain explicitly labeled. Installed offline IERS limits
coordinate precision; no calibrated operational safety claim.

## Verification and actual examples

```bash
# Backend running separately; from backend/:
../.venv/bin/python -m app.frontend_smoke --base-url http://127.0.0.1:8000
# Save the actual full requests/responses and measured timings:
../.venv/bin/python -m app.frontend_smoke --record-examples ../frontend_examples.json
# Regenerate the actual schema and this schema appendix:
../.venv/bin/python -m app.export_frontend
```

The checked-in `frontend_examples.json` is an **actual dated API transcript**,
not permanently current scientific outputs. Its labeled A..F entries contain
copy-pasteable exact request bodies/query parameters and full returned responses.
For example execute a recorded request (requires the corresponding current
encounter; historical IDs can expire):

```bash
../.venv/bin/python - <<'PY'
import json,httpx
records=json.load(open('../frontend_examples.json'))['entries']
entry=next(e for e in records if e['label']=='D.reference')
result=httpx.request(entry['method'],'http://127.0.0.1:8000'+entry['path'],
                    params=entry['params'],json=entry['request'])
print(result.status_code,result.text)
PY
```

The smoke command exits nonzero on broken workflows; it uses real HTTP responses
and independently calculated backend results, not hardcoded scientific answers.
Choose another available --encounter-object-id/--persistence-object-id when source
coverage changes. It deliberately uses labeled assumed physical/solar/covariance
scenarios. There is **no verified fully offline six-workflow server mode**.
Genuine dated fixtures under backend/tests/fixtures support offline component
tests, and NASA historical validation is offline; these are not live data.
Configured local catalog/SATCAT browsing is supported and labeled LOCAL, while
encounter discovery still requires actual SOCRATES source/cache coverage.

## Verbatim verified request/response examples

Actual HTTP run at **2026-10-11T10:07:06.996881+00:00**, not fabricated outputs or permanently current encounters. API origin below uses the default port8000; verification used the configurable port8015. All30 full exchanges are in frontend_examples.json. Re-run smoke for new live encounter IDs/epochs.

### Workflow A — A.positions

```bash
curl --fail-with-body -sS -X POST http://127.0.0.1:8000/api/positions -H 'Content-Type: application/json' --data '{"object_ids":["694","733","877"],"epoch":"2026-10-11T10:07:06.996881+00:00"}'
```

Actual HTTP200 response (4597wire bytes, 0.903112s):

```json
{
  "items": [
    {
      "epoch": "2026-10-11T10:07:06.996881Z",
      "position_km": [
        2247.9223601626995,
        6441.599975718137,
        465.28379190285216
      ],
      "propagation_status": "OK",
      "error": null,
      "id": "694",
      "name": "ATLAS CENTAUR 2",
      "classification": "PAYLOAD",
      "frame": "ITRS",
      "position_units": "km"
    },
    {
      "epoch": "2026-10-11T10:07:06.996881Z",
      "position_km": [
        4647.419689577033,
        -3295.1546546279947,
        4359.404723835747
      ],
      "propagation_status": "OK",
      "error": null,
      "id": "733",
      "name": "THOR AGENA D R/B",
      "classification": "ROCKET_BODY",
      "frame": "ITRS",
      "position_units": "km"
    },
    {
      "epoch": "2026-10-11T10:07:06.996881Z",
      "position_km": [
        2888.405504587525,
        6403.649229396462,
        309.79208522961784
      ],
      "propagation_status": "OK",
      "error": null,
      "id": "877",
      "name": "SL-3 R/B",
      "classification": "ROCKET_BODY",
      "frame": "ITRS",
      "position_units": "km"
    }
  ],
  "epoch": "2026-10-11T10:07:06.996881Z",
  "frame": "ITRS",
  "position_units": "km",
  "catalog": {
    "objects_available": 19505,
    "coverage": "PARTIAL",
    "freshness_status": "STALE",
    "sources": [
      {
        "source_url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=JSON",
        "content_sha256": "c89aff71574eb31d47d648badca6f494f864c8c83ba90523670cc8043110c7b6",
        "retrieved_at": "2026-10-11T08:18:13.482780Z",
        "dataset_timestamp": "2026-10-11T08:18:13.482780Z",
        "timestamp_basis": "FETCH_TIME",
        "retrieval_mode": "CACHE",
        "usable_records": 16701,
        "rejected_records": 0,
        "duplicate_records": 0
      },
      {
        "source_url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=cosmos-2251-debris&FORMAT=JSON",
        "content_sha256": "86dc8a5f346e5195cd7290a6cb8ebcc986a4bbadf6904cc296d613035bd12ac5",
        "retrieved_at": "2026-10-11T08:18:13.482780Z",
        "dataset_timestamp": "2026-10-11T08:18:13.482780Z",
        "timestamp_basis": "FETCH_TIME",
        "retrieval_mode": "CACHE",
        "usable_records": 588,
        "rejected_records": 0,
        "duplicate_records": 0
      },
      {
        "source_url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=iridium-33-debris&FORMAT=JSON",
        "content_sha256": "7f65418e427db3cf7db8d7cb410af64155a0d636cc281e90fa05da6b96f2a22e",
        "retrieved_at": "2026-10-11T08:18:13.482780Z",
        "dataset_timestamp": "2026-10-11T08:18:13.482780Z",
        "timestamp_basis": "FETCH_TIME",
        "retrieval_mode": "CACHE",
        "usable_records": 109,
        "rejected_records": 0,
        "duplicate_records": 0
      },
      {
        "source_url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=fengyun-1c-debris&FORMAT=JSON",
        "content_sha256": "293b2d758ba0ef80b1fbacb4fe1d06c4f2c5e1496a0845881adbb264deaac139",
        "retrieved_at": "2026-10-11T08:18:13.482780Z",
        "dataset_timestamp": "2026-10-11T08:18:13.482780Z",
        "timestamp_basis": "FETCH_TIME",
        "retrieval_mode": "CACHE",
        "usable_records": 1979,
        "rejected_records": 0,
        "duplicate_records": 0
      },
      {
        "source_url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=JSON",
        "content_sha256": "cd42a4ff3c60600d032720170017beed4f85101f7a925f72c70708470ebf7b1f",
        "retrieved_at": "2026-10-11T08:18:13.482780Z",
        "dataset_timestamp": "2026-10-11T08:18:13.482780Z",
        "timestamp_basis": "FETCH_TIME",
        "retrieval_mode": "CACHE",
        "usable_records": 156,
        "rejected_records": 0,
        "duplicate_records": 0
      }
    ],
    "snapshot_sha256": "e13054e93164ac9bf0affe6c95b2729229a29fc94327efc9c978734ea46ba305",
    "assembled_at": "2026-10-11T10:07:07.185023Z",
    "oldest_element_epoch": "2026-09-11T12:27:56.057184Z",
    "newest_element_epoch": "2026-10-12T17:36:20.007360Z",
    "rejected_record_count": 0,
    "duplicate_count": 28,
    "failed_sources": [],
    "coverage_limitations": [
      "PARTIAL catalog: only the selected available public GP groups, local OMM datasets and explicitly selected caches.",
      "GROUP=active does not contain all debris; debris groups cover only their named populations.",
      "Not all tracked objects have public GP data; untracked and restricted objects are absent.",
      "No completeness against the full orbiting population has been established.",
      "Newest element epoch retained per canonical NORAD ID; source datasets may have different retrieval times."
    ],
    "warnings": [
      "215 records have epochs more than seven days from assembly time; retained but must not be silently screened as current."
    ]
  },
  "metadata_source": {
    "source": "CelesTrak SATCAT",
    "source_url": "https://celestrak.org/pub/satcat.csv",
    "fetched_at": "2026-10-11T09:24:23.939547+00:00",
    "dataset_timestamp": "2026-10-10T18:22:58+00:00",
    "content_sha256": "f43644ebcbf57575a9e937f785a3cb8b828c7df8f54cbe2c51cfafcaf37fb294",
    "retrieval_mode": "CACHE",
    "records": 70980,
    "rejected_records": 0,
    "duplicate_records": 0
  },
  "warnings": [
    "ITRS/ECEF Earth-fixed positions in km; not raw TEME/inertial coordinates.",
    "Installed offline IERS data; predictive/degraded Earth orientation may limit precision.",
    "Three.js right-handed Y-up mapping: (x,y,z)ITRS -> (x,z,-y); one world unit per km or a common display scale.",
    "Earth-fixed sampled paths rotate with Earth and are not closed inertial orbital ellipses."
  ]
}
```

### Workflow B — B.analyze

```bash
curl --fail-with-body -sS -X POST http://127.0.0.1:8000/api/encounters/socrates-599855ce2ca729ae50cb34e9/analyze -H 'Content-Type: application/json' --data '{"probability_analysis":true}'
```

Actual HTTP200 response (1780wire bytes, 0.010371s):

```json
{
  "encounter_id": "socrates-599855ce2ca729ae50cb34e9",
  "source": "SOCRATES",
  "published": {
    "tca": "2026-10-12T03:54:38Z",
    "miss_distance_m": 27.0,
    "relative_speed_m_s": 2109.0,
    "max_probability_screening_metric": 0.004208
  },
  "calculated": {
    "tca": "2026-10-12T03:54:37.962335Z",
    "miss_distance_m": 687.2480289143118,
    "relative_speed_m_s": 2109.021101653846,
    "relative_position_m": [
      -410.9328338187188,
      459.60796945542097,
      -303.65206034108996
    ],
    "relative_velocity_m_s": [
      -1405.392764943107,
      -1520.8321319580414,
      -399.88849679720624
    ],
    "frame": "TEME",
    "searched_start": "2026-10-12T03:49:38Z",
    "searched_end": "2026-10-12T03:59:38Z",
    "sampled_minimum_m": 691.8217874565592,
    "status": "COMPLETE"
  },
  "model": "SGP4 / TEME / WGS72",
  "element_epochs": [
    "2026-10-10T22:45:40.775904Z",
    "2026-10-10T22:35:33.379584Z"
  ],
  "orbital_source_checksums": [
    "9bc6f1312c1f1a50507c27adbdf9f4186b3d00655571bbe8273fa5a7fb61c2a7",
    "6799ea556797819e8c0d8980484e5a889c86f28434f202e99e39709517638943"
  ],
  "source_model_disagreement": true,
  "warnings": [
    "Current GP elements may differ from the elements used for the published SOCRATES prediction.",
    "Source/model disagreement: miss distance differs by >100 m or TCA by >60 s; these are reporting thresholds, not uncertainty bounds.",
    "Secondary encounters have not been assessed; no calibrated collision probability or operational safety guarantee is provided."
  ],
  "probability_analysis": {
    "probability_status": "UNAVAILABLE_NO_COVARIANCE",
    "source": "SOCRATES",
    "socrates_max_probability": 0.004208,
    "calculated_pc": null,
    "tca": "2026-10-12T03:54:37.962335Z",
    "frame": "TEME",
    "label": null,
    "covariance_treatment": "NONE",
    "calculation": null,
    "assumptions": [],
    "warnings": [
      "SOCRATES provides MAX_PROB, a screening metric, not measured object covariances or calibrated Pc.",
      "No covariance or hard-body radius has been fabricated."
    ]
  }
}
```

### Workflow C — C.optimize

```bash
curl --fail-with-body -sS -X POST http://127.0.0.1:8000/api/encounters/socrates-599855ce2ca729ae50cb34e9/optimize -H 'Content-Type: application/json' --data '{"encounter_id":"socrates-599855ce2ca729ae50cb34e9","maneuvering_object_id":"27056","max_delta_v_m_s":0.2,"min_lead_time_minutes":5,"max_lead_time_hours":0.25,"target_miss_distance_km":10,"objective":"MAXIMUM_CLEARANCE","hypothetical_capability_assumed":true,"search":{"time_samples":1,"magnitude_samples":2,"max_evaluations":40,"refinement_evaluations":0,"timeout_seconds":25}}'
```

Actual HTTP200 response (5043wire bytes, 0.358168s):

```json
{
  "encounter_id": "socrates-599855ce2ca729ae50cb34e9",
  "maneuvering_object_id": "27056",
  "status": "COMPLETE",
  "result_label": "Best evaluated maneuvers; no global optimality guarantee",
  "objective": "MAXIMUM_CLEARANCE",
  "constraints": {
    "encounter_id": "socrates-599855ce2ca729ae50cb34e9",
    "maneuvering_object_id": "27056",
    "max_delta_v_m_s": 0.2,
    "min_lead_time_minutes": 5.0,
    "max_lead_time_hours": 0.25,
    "target_miss_distance_km": 10.0,
    "objective": "MAXIMUM_CLEARANCE",
    "hypothetical_capability_assumed": true,
    "initial_mass_kg": null,
    "available_propellant_mass_kg": null,
    "specific_impulse_s": null
  },
  "search_settings": {
    "time_samples": 1,
    "magnitude_samples": 2,
    "max_evaluations": 40,
    "timeout_seconds": 25.0,
    "refinement_evaluations": 0
  },
  "baseline": {
    "tca": "2026-10-12T03:54:37.965121Z",
    "miss_distance_m": 700.8727095557257,
    "relative_speed_m_s": 2109.0329046270126,
    "relative_position_m": [
      -415.9212226625532,
      470.7144490343053,
      -310.9019121993333
    ],
    "relative_velocity_m_s": [
      -1415.5281042699312,
      -1512.4045570824228,
      -396.14698602633416
    ],
    "frame": "GCRS",
    "searched_start": "2026-10-12T03:49:38Z",
    "searched_end": "2026-10-12T03:59:38Z",
    "sampled_minimum_m": 704.7224943794077,
    "status": "COMPLETE"
  },
  "sgp4_reference": {
    "encounter_id": "socrates-599855ce2ca729ae50cb34e9",
    "source": "SOCRATES",
    "published": {
      "tca": "2026-10-12T03:54:38Z",
      "miss_distance_m": 27.0,
      "relative_speed_m_s": 2109.0,
      "max_probability_screening_metric": 0.004208
    },
    "calculated": {
      "tca": "2026-10-12T03:54:37.962335Z",
      "miss_distance_m": 687.2480289143118,
      "relative_speed_m_s": 2109.021101653846,
      "relative_position_m": [
        -410.9328338187188,
        459.60796945542097,
        -303.65206034108996
      ],
      "relative_velocity_m_s": [
        -1405.392764943107,
        -1520.8321319580414,
        -399.88849679720624
      ],
      "frame": "TEME",
      "searched_start": "2026-10-12T03:49:38Z",
      "searched_end": "2026-10-12T03:59:38Z",
      "sampled_minimum_m": 691.8217874565592,
      "status": "COMPLETE"
    },
    "model": "SGP4 / TEME / WGS72",
    "element_epochs": [
      "2026-10-10T22:45:40.775904Z",
      "2026-10-10T22:35:33.379584Z"
    ],
    "orbital_source_checksums": [
      "9bc6f1312c1f1a50507c27adbdf9f4186b3d00655571bbe8273fa5a7fb61c2a7",
      "6799ea556797819e8c0d8980484e5a889c86f28434f202e99e39709517638943"
    ],
    "source_model_disagreement": true,
    "warnings": [
      "Current GP elements may differ from the elements used for the published SOCRATES prediction.",
      "Source/model disagreement: miss distance differs by >100 m or TCA by >60 s; these are reporting thresholds, not uncertainty bounds.",
      "Secondary encounters have not been assessed; no calibrated collision probability or operational safety guarantee is provided."
    ]
  },
  "numerical_reference_epoch": "2026-10-12T03:39:38Z",
  "solutions": [
    {
      "maneuver_time": "2026-10-12T03:39:38Z",
      "delta_v_m_s": 0.2,
      "delta_v_rtn_m_s": [
        -0.2,
        -0.0,
        -0.0
      ],
      "new_miss_distance_m": 861.6959222927252,
      "change_in_miss_distance_m": 160.8232127369995,
      "meets_target": false,
      "is_clearance_improvement": true,
      "calculated_tca": "2026-10-12T03:54:37.954078Z",
      "matched_baseline_miss_distance_m": 700.8727095557257
    },
    {
      "maneuver_time": "2026-10-12T03:39:38Z",
      "delta_v_m_s": 0.0,
      "delta_v_rtn_m_s": [
        0.0,
        0.0,
        0.0
      ],
      "new_miss_distance_m": 700.8727095557257,
      "change_in_miss_distance_m": 0.0,
      "meets_target": false,
      "is_clearance_improvement": false,
      "calculated_tca": "2026-10-12T03:54:37.965121Z",
      "matched_baseline_miss_distance_m": 700.8727095557257
    }
  ],
  "candidates_evaluated": 13,
  "feasible_candidates": 13,
  "target_feasible_candidates": 0,
  "numerical_failures": 0,
  "elapsed_seconds": 0.3488109350000741,
  "fuel_budget_delta_v_m_s": null,
  "model_assumptions": [
    "Hypothetical instantaneous RTN velocity impulse; supplied capability is assumed, not verified.",
    "Central Earth gravity plus J2, WGS84 constants, in GCRS coordinates.",
    "Both zero-burn and post-burn trajectories use the same initial epoch and numerical force model.",
    "SGP4 TEME states are transformed into GCRS using Astropy and the installed offline IERS data.",
    "Earth pole is fixed at the burn epoch over this short local propagation; no drag, higher harmonics, third-body forces or ongoing maneuvers.",
    "RTN transverse direction is perpendicular to radial in the orbital plane; it need not equal the eccentric-orbit velocity direction.",
    "Nominal clearance is not a calibrated collision probability or an operational safety guarantee.",
    "Secondary encounters have not been assessed. Results are not spacecraft flight commands.",
    "All candidate burns share one numerical reference epoch and nominal trajectory.",
    "Bounded deterministic samples plus local time/magnitude/direction exploration; no global optimum guarantee.",
    "Clearance improvement flag requires >1 mm modeled change; no uncertainty inference."
  ],
  "warnings": [
    "Current GP elements may differ from the elements used for the published SOCRATES prediction.",
    "Source/model disagreement: miss distance differs by >100 m or TCA by >60 s; these are reporting thresholds, not uncertainty bounds.",
    "Secondary encounters have not been assessed; no calibrated collision probability or operational safety guarantee is provided.",
    "No evaluated candidate reached the requested target; returned clearance is the best evaluated within the hard budget/window constraints."
  ],
  "secondary_screening": null
}
```

### Workflow D — D.reference

```bash
curl --fail-with-body -sS -X POST http://127.0.0.1:8000/api/probability/calculate -H 'Content-Type: application/json' --data '{"reference_case":"000025994_conj_000037558_20210324_151047_20210323_154356","independent_benchmark":true}'
```

Actual HTTP200 response (3601wire bytes, 0.025669s):

```json
{
  "source": "NASA_CARA_HISTORICAL_REFERENCE",
  "reference_only": true,
  "reference_case": "000025994_conj_000037558_20210324_151047_20210323_154356",
  "reference_url": "https://github.com/nasa/CARA_Analysis_Tools/tree/ce0f00722c56808755ee0adbe47a4e3d56439484/DataFiles/PcTestCaseCDMs",
  "source_sha256": "8b97cd36c195ebc869435d87dda19460285433872d4b242db43a448d6c213335",
  "original_tca": "2021-03-24T15:10:47.417000Z",
  "linear_closest_approach_tca": "2021-03-24T15:10:47.417129Z",
  "linear_tca_offset_seconds": 0.0001293094137124919,
  "state_frame": "EME2000",
  "covariance_frame": "INDIVIDUAL_OBJECT_RTN",
  "reference_model": "NASA_INDEPENDENT_2D_BENCHMARK",
  "published_reference_pc": 0.021173811560368256,
  "cdm_rounded_reference_pc": 0.02117,
  "calculated_pc": 0.021173811560374473,
  "numerical_difference": 6.217248937900877e-15,
  "relative_difference": 2.9362918056463266e-13,
  "calculation": {
    "status": "CALCULATED",
    "calculated_pc": 0.021173811560374473,
    "encounter_plane_miss_m": [
      -107.12044218721678,
      -9.493387408496044
    ],
    "projected_covariance_m2": [
      [
        24604.07682064333,
        3894.702813285913
      ],
      [
        3894.702813285913,
        1218.9863853819782
      ]
    ],
    "combined_hard_body_radius_m": 15.0,
    "numerical_method": "2D Gaussian disk: eigenbasis, stable normal-CDF difference, adaptive QUADPACK",
    "numerical_status": "CONVERGED",
    "estimated_absolute_error": 2.0089218483176907e-11,
    "requested_relative_tolerance": 1e-09,
    "projected_condition_number": 42.961948454687956,
    "integrand_evaluations": 399,
    "assumptions": [
      "Short rectilinear relative motion; stationary Gaussian position uncertainties.",
      "Collision disk radius is the explicitly supplied combined hard-body radius.",
      "Covariances and relative states share one inertial frame, epoch and SI units.",
      "Velocity uncertainty, covariance evolution, shape/orientation and non-Gaussian errors are not modeled.",
      "Object position errors assumed independent; cross-covariance unavailable or explicitly zero."
    ],
    "warnings": [
      "Numerical error estimates are not physical uncertainty bounds or an operational safety guarantee.",
      "Estimated absolute error covers quadrature only, not covariance/frame roundoff or input uncertainty.",
      "Instantaneous states cannot establish rectilinear-model applicability or covariance realism."
    ]
  },
  "assumptions": [
    "Short rectilinear relative motion; stationary Gaussian position uncertainties.",
    "Collision disk radius is the explicitly supplied combined hard-body radius.",
    "Covariances and relative states share one inertial frame, epoch and SI units.",
    "Velocity uncertainty, covariance evolution, shape/orientation and non-Gaussian errors are not modeled.",
    "Object position errors assumed independent; cross-covariance unavailable or explicitly zero.",
    "Explicit independent-model benchmark only: NASA PcMultiStep_FromCDM.m sets apply_covXcorr_corrections=false.",
    "Original inertial covariances fixed during sub-millisecond linear TCA rounding correction."
  ],
  "warnings": [
    "Historical validation data, not a current operational conjunction.",
    "DCP common-density correlation metadata present: independence must be explicitly selected only for the NASA independent-model benchmark, not assumed for encounter risk.",
    "Numerical error estimates are not physical uncertainty bounds or an operational safety guarantee.",
    "Estimated absolute error covers quadrature only, not covariance/frame roundoff or input uncertainty.",
    "Instantaneous states cannot establish rectilinear-model applicability or covariance realism.",
    "Known DCP correlation metadata is deliberately omitted ONLY for the explicitly selected NASA independent-model benchmark.",
    "This validation Pc is not an operational risk calculation for the correlated encounter."
  ]
}
```

### Workflow E — E.persistence

```bash
curl --fail-with-body -sS -X POST http://127.0.0.1:8000/api/objects/25544/persistence -H 'Content-Type: application/json' --data '{"start_time":"2026-10-11T10:07:06.996881+00:00","horizon_days":0.001,"scenario_mode":"COMPARE","visualization":true,"weather_mode":"HYPOTHETICAL_CONSTANT","nominal_f107_sfu":150,"nominal_ap":15,"aerodynamic_properties":{"input_category":"HYPOTHETICAL_ASSUMPTION","cd_area_over_mass_m2_kg":0.022}}'
```

Actual HTTP200 response (26495wire bytes, 1.615432s):

```json
{
  "object_id": "25544",
  "prediction_status": "COMPLETE",
  "analysis": {
    "object_id": "25544",
    "object_name": "ISS (ZARYA)",
    "gp_epoch": "2026-10-10T18:56:31.282080Z",
    "initial_state": {
      "timestamp": "2026-10-11T10:07:06.996881Z",
      "position_m": [
        4181170.5251262924,
        1738040.8485607381,
        -5072172.336575541
      ],
      "velocity_m_s": [
        -782.1192499063909,
        7377.845038355794,
        1880.0055541926995
      ],
      "frame": "GCRS",
      "position_units": "m",
      "velocity_units": "m/s",
      "propagation_status": "OK"
    },
    "initial_orbit": {
      "central_specific_energy_j_kg": -29334747.201698396,
      "total_specific_energy_j_kg": -29316253.854859952,
      "semimajor_axis_m": 6793998.241391393,
      "eccentricity": 0.0008410600959496197,
      "perigee_altitude_m": 410147.0805786066,
      "apogee_altitude_m": 421575.40220418014,
      "geodetic_altitude_m": 432993.9828831346
    },
    "assumed_physical_parameters": {
      "input_category": "HYPOTHETICAL_ASSUMPTION",
      "mass_kg": null,
      "area_m2": null,
      "drag_coefficient": null,
      "cd_area_over_mass_m2_kg": 0.022
    },
    "prediction_status": "COMPLETE",
    "prediction_horizon_days": 0.001,
    "scenario_analysis": {
      "settings": {
        "horizon_days": 0.001,
        "boundary_altitude_m": 120000.0,
        "scenario_mode": "COMPARE",
        "weather_mode": "HYPOTHETICAL_CONSTANT",
        "nominal_f107_sfu": 150.0,
        "nominal_ap": 15.0,
        "min_cd_area_over_mass_m2_kg": null,
        "max_cd_area_over_mass_m2_kg": null,
        "solver": {
          "rtol": 1e-09,
          "position_atol_m": 0.0001,
          "velocity_atol_m_s": 1e-07,
          "max_step_seconds": 120.0,
          "sample_step_seconds": 600.0,
          "timeout_seconds": 180.0
        }
      },
      "scenarios": [
        {
          "scenario": "LOW_DRAG",
          "aerodynamic_properties": {
            "input_category": "HYPOTHETICAL_ASSUMPTION",
            "mass_kg": null,
            "area_m2": null,
            "drag_coefficient": null,
            "cd_area_over_mass_m2_kg": 0.022
          },
          "environment_assumptions": {
            "treatment": "HYPOTHETICAL_CONSTANT_SOLAR_HISTORY",
            "f107_sfu": 80,
            "ap": 4,
            "label": "ILLUSTRATIVE \u2014 USER-SELECTED UNCERTAINTY ASSUMPTIONS.",
            "density_treatment": "Actual NRLMSIS response, not a constant density multiplier"
          },
          "boundary": {
            "prediction_status": "NOT_REACHED_WITHIN_HORIZON",
            "boundary_altitude_m": 120000.0,
            "crossing_occurred": false,
            "crossing_time": null,
            "modeled_time_until_crossing_seconds": null,
            "prediction_horizon_days": 0.001,
            "propagation": {
              "status": "PROPAGATED_WITHIN_HORIZON",
              "start_time": "2026-10-11T10:07:06.996881Z",
              "requested_end_time": "2026-10-11T10:08:33.396881Z",
              "integrated_end_time": "2026-10-11T10:08:33.396881Z",
              "horizon_days": 0.001,
              "samples": null,
              "elapsed_seconds": 0.05855739099933999,
              "derivative_evaluations": 77,
              "solver_settings": {
                "rtol": 1e-09,
                "position_atol_m": 0.0001,
                "velocity_atol_m_s": 1e-07,
                "max_step_seconds": 120.0,
                "sample_step_seconds": 600.0,
                "timeout_seconds": 180.0
              },
              "environment": {
                "model": "NRLMSIS 2.1",
                "implementation": "pymsis 0.12.0",
                "weather": "Explicit provider; each output must retain forcing provenance",
                "density_units": "kg/m3",
                "forcing_samples": [
                  {
                    "date": "2026-10-11",
                    "f107_previous_day_sfu": 80.0,
                    "f107_center81_sfu": 80.0,
                    "ap_history": [
                      4.0,
                      4.0,
                      4.0,
                      4.0,
                      4.0,
                      4.0,
                      4.0
                    ],
                    "geomagnetic_mode": -1,
                    "input_category": "USER_SUPPLIED_ASSUMPTION",
                    "provenance": {
                      "source": "USER_SELECTED_HYPOTHETICAL_CONSTANT_SOLAR_HISTORY",
                      "scenario": "LOW_DRAG",
                      "reason": "Explicit COMPARE preset",
                      "f107_convention": "Earth-distance sfu; constant previous/center81 history",
                      "ap_convention": "Constant daily and all storm-time history components"
                    },
                    "warnings": [
                      "ILLUSTRATIVE \u2014 USER-SELECTED UNCERTAINTY ASSUMPTIONS.",
                      "Constant solar history is a scenario, not observed conditions or a forecast beyond source coverage."
                    ]
                  }
                ],
                "coordinate_method": "Validated Astropy SO(3) interpolation + ERFA WGS84; actual MSIS at every force call"
              },
              "aerodynamic_properties": {
                "input_category": "HYPOTHETICAL_ASSUMPTION",
                "mass_kg": null,
                "area_m2": null,
                "drag_coefficient": null,
                "cd_area_over_mass_m2_kg": 0.022
              },
              "boundary_altitude_m": 120000.0,
              "boundary_crossing_time": null,
              "model": "DOP853 / GCRS / WGS84 central gravity + J2 + co-rotating drag",
              "assumptions": [
                "GCRS SI initial state; SGP4 TEME inputs are transformed, never relabeled.",
                "Shared WGS84 central/J2 dynamics; gravity pole fixed at initial epoch as in existing numerical model.",
                "Co-rotation axis and geographic density positions use time-varying GCRS/ITRS orientation.",
                "SO(3) Earth-orientation interpolation at at most 20-minute spacing; density itself is not interpolated.",
                "Constant supplied effective Cd*A/m; no attitude dynamics, winds or active orbit control.",
                "Terminal descending WGS84 geodetic boundary event; no output beyond the cutoff.",
                "Osculating central-gravity elements; perigee/apogee are radii minus equatorial Earth radius, not geodetic heights."
              ],
              "warnings": [
                "Bounded research model, not observationally verified decay or operational reentry prediction.",
                "J2 produces short-period osculating-element oscillations; individual semimajor-axis samples need not monotonically decrease.",
                "Fixed gravity pole, offline predictive Earth orientation, no higher harmonics/third bodies and increasing initial-GP uncertainty limit long-horizon accuracy.",
                "No breakup, ablation, fragmentation or ground-impact calculation."
              ],
              "sample_status": "OMITTED_FROM_COMPACT_VIEW",
              "original_sample_count": 2
            },
            "assumptions": [
              "Finite prediction horizon and explicit aerodynamic/environment inputs.",
              "Boundary is a WGS84 geodetic orbital-model cutoff, not breakup or ground impact."
            ],
            "warnings": [
              "Modeled crossing dates are scenario calculations, not precise operational reentry predictions.",
              "Not reaching the boundary within the horizon does not imply perpetual orbital persistence."
            ]
          },
          "total_specific_energy_change_j_kg": -0.11760688945651054,
          "semimajor_axis_change_m": 776.5648161834106,
          "initial_period_mean_semimajor_axis_m": 6794386.523799485,
          "final_period_mean_semimajor_axis_m": 6794386.523799485,
          "warnings": [
            "Scenario labels are nominal presets, not guaranteed ordering for all geometries or actual storm conditions.",
            "Period-window sample means reduce J2 short-period effects; short horizons/windows overlap and are not a secular lifetime extrapolation."
          ]
        },
        {
          "scenario": "NOMINAL",
          "aerodynamic_properties": {
            "input_category": "HYPOTHETICAL_ASSUMPTION",
            "mass_kg": null,
            "area_m2": null,
            "drag_coefficient": null,
            "cd_area_over_mass_m2_kg": 0.022
          },
          "environment_assumptions": {
            "treatment": "HYPOTHETICAL_CONSTANT",
            "f107_sfu": 150.0,
            "ap": 15.0,
            "source_snapshot": null
          },
          "boundary": {
            "prediction_status": "NOT_REACHED_WITHIN_HORIZON",
            "boundary_altitude_m": 120000.0,
            "crossing_occurred": false,
            "crossing_time": null,
            "modeled_time_until_crossing_seconds": null,
            "prediction_horizon_days": 0.001,
            "propagation": {
              "status": "PROPAGATED_WITHIN_HORIZON",
              "start_time": "2026-10-11T10:07:06.996881Z",
              "requested_end_time": "2026-10-11T10:08:33.396881Z",
              "integrated_end_time": "2026-10-11T10:08:33.396881Z",
              "horizon_days": 0.001,
              "samples": null,
              "elapsed_seconds": 0.08226966100119171,
              "derivative_evaluations": 77,
              "solver_settings": {
                "rtol": 1e-09,
                "position_atol_m": 0.0001,
                "velocity_atol_m_s": 1e-07,
                "max_step_seconds": 120.0,
                "sample_step_seconds": 600.0,
                "timeout_seconds": 180.0
              },
              "environment": {
                "model": "NRLMSIS 2.1",
                "implementation": "pymsis 0.12.0",
                "weather": "Explicit provider; each output must retain forcing provenance",
                "density_units": "kg/m3",
                "forcing_samples": [
                  {
                    "date": "2026-10-11",
                    "f107_previous_day_sfu": 150.0,
                    "f107_center81_sfu": 150.0,
                    "ap_history": [
                      15.0,
                      15.0,
                      15.0,
                      15.0,
                      15.0,
                      15.0,
                      15.0
                    ],
                    "geomagnetic_mode": -1,
                    "input_category": "USER_SUPPLIED_ASSUMPTION",
                    "provenance": {
                      "source": "USER_SELECTED_HYPOTHETICAL_CONSTANT_SOLAR_HISTORY",
                      "scenario": "NOMINAL",
                      "reason": "Explicit constant scenario",
                      "f107_convention": "Earth-distance sfu; constant previous/center81 history",
                      "ap_convention": "Constant daily and all storm-time history components"
                    },
                    "warnings": [
                      "ILLUSTRATIVE \u2014 USER-SELECTED UNCERTAINTY ASSUMPTIONS.",
                      "Constant solar history is a scenario, not observed conditions or a forecast beyond source coverage."
                    ]
                  }
                ],
                "coordinate_method": "Validated Astropy SO(3) interpolation + ERFA WGS84; actual MSIS at every force call"
              },
              "aerodynamic_properties": {
                "input_category": "HYPOTHETICAL_ASSUMPTION",
                "mass_kg": null,
                "area_m2": null,
                "drag_coefficient": null,
                "cd_area_over_mass_m2_kg": 0.022
              },
              "boundary_altitude_m": 120000.0,
              "boundary_crossing_time": null,
              "model": "DOP853 / GCRS / WGS84 central gravity + J2 + co-rotating drag",
              "assumptions": [
                "GCRS SI initial state; SGP4 TEME inputs are transformed, never relabeled.",
                "Shared WGS84 central/J2 dynamics; gravity pole fixed at initial epoch as in existing numerical model.",
                "Co-rotation axis and geographic density positions use time-varying GCRS/ITRS orientation.",
                "SO(3) Earth-orientation interpolation at at most 20-minute spacing; density itself is not interpolated.",
                "Constant supplied effective Cd*A/m; no attitude dynamics, winds or active orbit control.",
                "Terminal descending WGS84 geodetic boundary event; no output beyond the cutoff.",
                "Osculating central-gravity elements; perigee/apogee are radii minus equatorial Earth radius, not geodetic heights."
              ],
              "warnings": [
                "Bounded research model, not observationally verified decay or operational reentry prediction.",
                "J2 produces short-period osculating-element oscillations; individual semimajor-axis samples need not monotonically decrease.",
                "Fixed gravity pole, offline predictive Earth orientation, no higher harmonics/third bodies and increasing initial-GP uncertainty limit long-horizon accuracy.",
                "No breakup, ablation, fragmentation or ground-impact calculation."
              ],
              "sample_status": "OMITTED_FROM_COMPACT_VIEW",
              "original_sample_count": 2
            },
            "assumptions": [
              "Finite prediction horizon and explicit aerodynamic/environment inputs.",
              "Boundary is a WGS84 geodetic orbital-model cutoff, not breakup or ground impact."
            ],
            "warnings": [
              "Modeled crossing dates are scenario calculations, not precise operational reentry predictions.",
              "Not reaching the boundary within the horizon does not imply perpetual orbital persistence."
            ]
          },
          "total_specific_energy_change_j_kg": -0.7379979267716408,
          "semimajor_axis_change_m": 776.421094212681,
          "initial_period_mean_semimajor_axis_m": 6794386.4519385,
          "final_period_mean_semimajor_axis_m": 6794386.4519385,
          "warnings": [
            "Scenario labels are nominal presets, not guaranteed ordering for all geometries or actual storm conditions.",
            "Period-window sample means reduce J2 short-period effects; short horizons/windows overlap and are not a secular lifetime extrapolation."
          ]
        },
        {
          "scenario": "HIGH_DRAG",
          "aerodynamic_properties": {
            "input_category": "HYPOTHETICAL_ASSUMPTION",
            "mass_kg": null,
            "area_m2": null,
            "drag_coefficient": null,
            "cd_area_over_mass_m2_kg": 0.022
          },
          "environment_assumptions": {
            "treatment": "HYPOTHETICAL_CONSTANT_SOLAR_HISTORY",
            "f107_sfu": 220,
            "ap": 40,
            "label": "ILLUSTRATIVE \u2014 USER-SELECTED UNCERTAINTY ASSUMPTIONS.",
            "density_treatment": "Actual NRLMSIS response, not a constant density multiplier"
          },
          "boundary": {
            "prediction_status": "NOT_REACHED_WITHIN_HORIZON",
            "boundary_altitude_m": 120000.0,
            "crossing_occurred": false,
            "crossing_time": null,
            "modeled_time_until_crossing_seconds": null,
            "prediction_horizon_days": 0.001,
            "propagation": {
              "status": "PROPAGATED_WITHIN_HORIZON",
              "start_time": "2026-10-11T10:07:06.996881Z",
              "requested_end_time": "2026-10-11T10:08:33.396881Z",
              "integrated_end_time": "2026-10-11T10:08:33.396881Z",
              "horizon_days": 0.001,
              "samples": null,
              "elapsed_seconds": 0.03886726800192264,
              "derivative_evaluations": 77,
              "solver_settings": {
                "rtol": 1e-09,
                "position_atol_m": 0.0001,
                "velocity_atol_m_s": 1e-07,
                "max_step_seconds": 120.0,
                "sample_step_seconds": 600.0,
                "timeout_seconds": 180.0
              },
              "environment": {
                "model": "NRLMSIS 2.1",
                "implementation": "pymsis 0.12.0",
                "weather": "Explicit provider; each output must retain forcing provenance",
                "density_units": "kg/m3",
                "forcing_samples": [
                  {
                    "date": "2026-10-11",
                    "f107_previous_day_sfu": 220.0,
                    "f107_center81_sfu": 220.0,
                    "ap_history": [
                      40.0,
                      40.0,
                      40.0,
                      40.0,
                      40.0,
                      40.0,
                      40.0
                    ],
                    "geomagnetic_mode": -1,
                    "input_category": "USER_SUPPLIED_ASSUMPTION",
                    "provenance": {
                      "source": "USER_SELECTED_HYPOTHETICAL_CONSTANT_SOLAR_HISTORY",
                      "scenario": "HIGH_DRAG",
                      "reason": "Explicit COMPARE preset",
                      "f107_convention": "Earth-distance sfu; constant previous/center81 history",
                      "ap_convention": "Constant daily and all storm-time history components"
                    },
                    "warnings": [
                      "ILLUSTRATIVE \u2014 USER-SELECTED UNCERTAINTY ASSUMPTIONS.",
                      "Constant solar history is a scenario, not observed conditions or a forecast beyond source coverage."
                    ]
                  }
                ],
                "coordinate_method": "Validated Astropy SO(3) interpolation + ERFA WGS84; actual MSIS at every force call"
              },
              "aerodynamic_properties": {
                "input_category": "HYPOTHETICAL_ASSUMPTION",
                "mass_kg": null,
                "area_m2": null,
                "drag_coefficient": null,
                "cd_area_over_mass_m2_kg": 0.022
              },
              "boundary_altitude_m": 120000.0,
              "boundary_crossing_time": null,
              "model": "DOP853 / GCRS / WGS84 central gravity + J2 + co-rotating drag",
              "assumptions": [
                "GCRS SI initial state; SGP4 TEME inputs are transformed, never relabeled.",
                "Shared WGS84 central/J2 dynamics; gravity pole fixed at initial epoch as in existing numerical model.",
                "Co-rotation axis and geographic density positions use time-varying GCRS/ITRS orientation.",
                "SO(3) Earth-orientation interpolation at at most 20-minute spacing; density itself is not interpolated.",
                "Constant supplied effective Cd*A/m; no attitude dynamics, winds or active orbit control.",
                "Terminal descending WGS84 geodetic boundary event; no output beyond the cutoff.",
                "Osculating central-gravity elements; perigee/apogee are radii minus equatorial Earth radius, not geodetic heights."
              ],
              "warnings": [
                "Bounded research model, not observationally verified decay or operational reentry prediction.",
                "J2 produces short-period osculating-element oscillations; individual semimajor-axis samples need not monotonically decrease.",
                "Fixed gravity pole, offline predictive Earth orientation, no higher harmonics/third bodies and increasing initial-GP uncertainty limit long-horizon accuracy.",
                "No breakup, ablation, fragmentation or ground-impact calculation."
              ],
              "sample_status": "OMITTED_FROM_COMPACT_VIEW",
              "original_sample_count": 2
            },
            "assumptions": [
              "Finite prediction horizon and explicit aerodynamic/environment inputs.",
              "Boundary is a WGS84 geodetic orbital-model cutoff, not breakup or ground impact."
            ],
            "warnings": [
              "Modeled crossing dates are scenario calculations, not precise operational reentry predictions.",
              "Not reaching the boundary within the horizon does not imply perpetual orbital persistence."
            ]
          },
          "total_specific_energy_change_j_kg": -1.8094376139342785,
          "semimajor_axis_change_m": 776.1728807650506,
          "initial_period_mean_semimajor_axis_m": 6794386.327831776,
          "final_period_mean_semimajor_axis_m": 6794386.327831776,
          "warnings": [
            "Scenario labels are nominal presets, not guaranteed ordering for all geometries or actual storm conditions.",
            "Period-window sample means reduce J2 short-period effects; short horizons/windows overlap and are not a secular lifetime extrapolation."
          ]
        }
      ],
      "status": "COMPLETE",
      "scenario_envelope": {
        "interpretation": "Scenario range only; NOT a statistical confidence interval or probability distribution",
        "valid_scenarios": 3,
        "failed_scenarios": [],
        "crossed_scenarios": [],
        "not_reached_within_horizon": [
          "LOW_DRAG",
          "NOMINAL",
          "HIGH_DRAG"
        ],
        "crossing_seconds_min": null,
        "crossing_seconds_max": null,
        "crossing_range_covers_only_reached_scenarios": true,
        "energy_change_range_j_kg": [
          -1.8094376139342785,
          -0.11760688945651054
        ]
      },
      "assumptions": [
        "Actual separate gravity/J2/drag/MSIS propagations; no precomputed lifetime answers.",
        "LOW/HIGH compare explicit constant solar/Ap histories; nominal weather source/treatment is disclosed.",
        "Physical and weather scenario envelope is not a calibrated statistical interval."
      ],
      "warnings": [
        "Unknown physical properties, long-term space weather and initial orbit uncertainty prevent precise operational reentry predictions.",
        "Failed scenarios remain visible and are excluded only from numerical envelope endpoints."
      ]
    },
    "persistence_metrics": [
      {
        "scenario": "LOW_DRAG",
        "status": "NOT_REACHED_WITHIN_HORIZON",
        "definition": "Piecewise-linear instantaneous WGS84 geodetic sample altitude; not perigee/apogee categories",
        "time_in_bands_seconds": {
          "120\u2013250 km": 0.0,
          "250\u2013500 km": 86.4,
          "500\u20131000 km": 0.0
        },
        "modeled_time_in_orbit_seconds": 86.4,
        "unclassified_seconds": 0,
        "sampling_step_seconds": 600.0,
        "limitations": "Sample-based occupancy approximation; no orbital-cycle averaging or statistical confidence implied",
        "final_perigee_altitude_m": 411392.48922944814,
        "final_apogee_altitude_m": 421883.1231857063,
        "boundary_crossing_time": null
      },
      {
        "scenario": "NOMINAL",
        "status": "NOT_REACHED_WITHIN_HORIZON",
        "definition": "Piecewise-linear instantaneous WGS84 geodetic sample altitude; not perigee/apogee categories",
        "time_in_bands_seconds": {
          "120\u2013250 km": 0.0,
          "250\u2013500 km": 86.4,
          "500\u20131000 km": 0.0
        },
        "modeled_time_in_orbit_seconds": 86.4,
        "unclassified_seconds": 0,
        "sampling_step_seconds": 600.0,
        "limitations": "Sample-based occupancy approximation; no orbital-cycle averaging or statistical confidence implied",
        "final_perigee_altitude_m": 411392.2199255787,
        "final_apogee_altitude_m": 421883.10504563246,
        "boundary_crossing_time": null
      },
      {
        "scenario": "HIGH_DRAG",
        "status": "NOT_REACHED_WITHIN_HORIZON",
        "definition": "Piecewise-linear instantaneous WGS84 geodetic sample altitude; not perigee/apogee categories",
        "time_in_bands_seconds": {
          "120\u2013250 km": 0.0,
          "250\u2013500 km": 86.4,
          "500\u20131000 km": 0.0
        },
        "modeled_time_in_orbit_seconds": 86.4,
        "unclassified_seconds": 0,
        "sampling_step_seconds": 600.0,
        "limitations": "Sample-based occupancy approximation; no orbital-cycle averaging or statistical confidence implied",
        "final_perigee_altitude_m": 411391.7548079537,
        "final_apogee_altitude_m": 421883.0737363631,
        "boundary_crossing_time": null
      }
    ],
    "provenance": {
      "gp": {
        "elements": {
          "object_id": "25544",
          "object_name": "ISS (ZARYA)",
          "international_designator": "1998-067A",
          "epoch": "2026-10-10T18:56:31.282080Z",
          "mean_motion_rev_day": 15.48817123,
          "eccentricity": 0.00067205,
          "inclination_deg": 51.6307,
          "raan_deg": 88.0087,
          "argument_of_pericenter_deg": 246.7167,
          "mean_anomaly_deg": 113.3114,
          "bstar": 0.000205821,
          "mean_motion_dot": 0.00010839,
          "mean_motion_ddot": 0.0,
          "ephemeris_type": 0,
          "classification": "U",
          "element_set_number": 999,
          "revolutions_at_epoch": 58967,
          "center": "EARTH",
          "frame": "TEME",
          "time_system": "UTC",
          "mean_element_theory": "SGP4"
        },
        "source": "CelesTrak GP",
        "source_url": "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=JSON",
        "fetched_at": "2026-10-11T10:07:36.525435Z",
        "content_sha256": "9d78055cff2573f4d18b1f367050542595cb8f714a4de57e118bc42bd9f56a73",
        "data_status": "VALID",
        "warnings": []
      },
      "initial_state_method": "SGP4 WGS72 TEME transformed to GCRS with actual Astropy position/velocity conversion",
      "input_identity": "Actual cataloged object; supplied aerodynamic values are not verified object properties"
    },
    "assumptions": [
      "Actual catalog GP supplies a single initial osculating state, not a precise long-horizon orbit determination.",
      "User-supplied constant aerodynamic parameters; BSTAR is not converted into Cd*A/m.",
      "Research persistence within a bounded horizon; no debris cleanup ranking."
    ],
    "warnings": [
      "Current GP elements may differ from the elements used for the published SOCRATES prediction.",
      "Increasing GP uncertainty, omitted forces/active control and unknown attitude/weather limit long-horizon fidelity.",
      "Modeled decay and boundary times are not observationally verified decay or operational reentry predictions."
    ]
  },
  "trajectories": {
    "LOW_DRAG": {
      "id": "25544",
      "name": "ISS (ZARYA)",
      "frame": "ITRS",
      "position_units": "km",
      "samples": [
        {
          "epoch": "2026-10-11T10:07:06.996881Z",
          "position_km": [
            -3889.419802402211,
            -2342.436366050329,
            -5061.157045089519
          ],
          "propagation_status": "OK",
          "error": null
        },
        {
          "epoch": "2026-10-11T10:08:33.396881Z",
          "position_km": [
            -3727.833581975713,
            -2927.2296110455536,
            -4875.193136154279
          ],
          "propagation_status": "OK",
          "error": null
        }
      ],
      "provenance": {
        "gp": {
          "elements": {
            "object_id": "25544",
            "object_name": "ISS (ZARYA)",
            "international_designator": "1998-067A",
            "epoch": "2026-10-10T18:56:31.282080Z",
            "mean_motion_rev_day": 15.48817123,
            "eccentricity": 0.00067205,
            "inclination_deg": 51.6307,
            "raan_deg": 88.0087,
            "argument_of_pericenter_deg": 246.7167,
            "mean_anomaly_deg": 113.3114,
            "bstar": 0.000205821,
            "mean_motion_dot": 0.00010839,
            "mean_motion_ddot": 0.0,
            "ephemeris_type": 0,
            "classification": "U",
            "element_set_number": 999,
            "revolutions_at_epoch": 58967,
            "center": "EARTH",
            "frame": "TEME",
            "time_system": "UTC",
            "mean_element_theory": "SGP4"
          },
          "source": "CelesTrak GP",
          "source_url": "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=JSON",
          "fetched_at": "2026-10-11T10:07:36.525435Z",
          "content_sha256": "9d78055cff2573f4d18b1f367050542595cb8f714a4de57e118bc42bd9f56a73",
          "data_status": "VALID",
          "warnings": []
        },
        "weather": {
          "treatment": "HYPOTHETICAL_CONSTANT_SOLAR_HISTORY",
          "f107_sfu": 80,
          "ap": 4,
          "label": "ILLUSTRATIVE \u2014 USER-SELECTED UNCERTAINTY ASSUMPTIONS.",
          "density_treatment": "Actual NRLMSIS response, not a constant density multiplier"
        },
        "sample_treatment": "Actual computed samples; evenly indexed subsampling if original count exceeds1001"
      },
      "model": "DOP853 / GCRS / WGS84 central gravity + J2 + co-rotating drag -> Astropy ITRS",
      "warnings": [
        "Bounded research model, not observationally verified decay or operational reentry prediction.",
        "J2 produces short-period osculating-element oscillations; individual semimajor-axis samples need not monotonically decrease.",
        "Fixed gravity pole, offline predictive Earth orientation, no higher harmonics/third bodies and increasing initial-GP uncertainty limit long-horizon accuracy.",
        "No breakup, ablation, fragmentation or ground-impact calculation.",
        "ITRS/ECEF Earth-fixed positions in km; not raw TEME/inertial coordinates.",
        "Installed offline IERS data; predictive/degraded Earth orientation may limit precision.",
        "Three.js right-handed Y-up mapping: (x,y,z)ITRS -> (x,z,-y); one world unit per km or a common display scale.",
        "Earth-fixed sampled paths rotate with Earth and are not closed inertial orbital ellipses."
      ]
    },
    "NOMINAL": {
      "id": "25544",
      "name": "ISS (ZARYA)",
      "frame": "ITRS",
      "position_units": "km",
      "samples": [
        {
          "epoch": "2026-10-11T10:07:06.996881Z",
          "position_km": [
            -3889.419802402211,
            -2342.436366050329,
            -5061.157045089519
          ],
          "propagation_status": "OK",
          "error": null
        },
        {
          "epoch": "2026-10-11T10:08:33.396881Z",
          "position_km": [
            -3727.8335828301388,
            -2927.22960778198,
            -4875.193137140086
          ],
          "propagation_status": "OK",
          "error": null
        }
      ],
      "provenance": {
        "gp": {
          "elements": {
            "object_id": "25544",
            "object_name": "ISS (ZARYA)",
            "international_designator": "1998-067A",
            "epoch": "2026-10-10T18:56:31.282080Z",
            "mean_motion_rev_day": 15.48817123,
            "eccentricity": 0.00067205,
            "inclination_deg": 51.6307,
            "raan_deg": 88.0087,
            "argument_of_pericenter_deg": 246.7167,
            "mean_anomaly_deg": 113.3114,
            "bstar": 0.000205821,
            "mean_motion_dot": 0.00010839,
            "mean_motion_ddot": 0.0,
            "ephemeris_type": 0,
            "classification": "U",
            "element_set_number": 999,
            "revolutions_at_epoch": 58967,
            "center": "EARTH",
            "frame": "TEME",
            "time_system": "UTC",
            "mean_element_theory": "SGP4"
          },
          "source": "CelesTrak GP",
          "source_url": "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=JSON",
          "fetched_at": "2026-10-11T10:07:36.525435Z",
          "content_sha256": "9d78055cff2573f4d18b1f367050542595cb8f714a4de57e118bc42bd9f56a73",
          "data_status": "VALID",
          "warnings": []
        },
        "weather": {
          "treatment": "HYPOTHETICAL_CONSTANT",
          "f107_sfu": 150.0,
          "ap": 15.0,
          "source_snapshot": null
        },
        "sample_treatment": "Actual computed samples; evenly indexed subsampling if original count exceeds1001"
      },
      "model": "DOP853 / GCRS / WGS84 central gravity + J2 + co-rotating drag -> Astropy ITRS",
      "warnings": [
        "Bounded research model, not observationally verified decay or operational reentry prediction.",
        "J2 produces short-period osculating-element oscillations; individual semimajor-axis samples need not monotonically decrease.",
        "Fixed gravity pole, offline predictive Earth orientation, no higher harmonics/third bodies and increasing initial-GP uncertainty limit long-horizon accuracy.",
        "No breakup, ablation, fragmentation or ground-impact calculation.",
        "ITRS/ECEF Earth-fixed positions in km; not raw TEME/inertial coordinates.",
        "Installed offline IERS data; predictive/degraded Earth orientation may limit precision.",
        "Three.js right-handed Y-up mapping: (x,y,z)ITRS -> (x,z,-y); one world unit per km or a common display scale.",
        "Earth-fixed sampled paths rotate with Earth and are not closed inertial orbital ellipses."
      ]
    },
    "HIGH_DRAG": {
      "id": "25544",
      "name": "ISS (ZARYA)",
      "frame": "ITRS",
      "position_units": "km",
      "samples": [
        {
          "epoch": "2026-10-11T10:07:06.996881Z",
          "position_km": [
            -3889.419802402211,
            -2342.436366050329,
            -5061.157045089519
          ],
          "propagation_status": "OK",
          "error": null
        },
        {
          "epoch": "2026-10-11T10:08:33.396881Z",
          "position_km": [
            -3727.8335843017708,
            -2927.2296021622788,
            -4875.193138838095
          ],
          "propagation_status": "OK",
          "error": null
        }
      ],
      "provenance": {
        "gp": {
          "elements": {
            "object_id": "25544",
            "object_name": "ISS (ZARYA)",
            "international_designator": "1998-067A",
            "epoch": "2026-10-10T18:56:31.282080Z",
            "mean_motion_rev_day": 15.48817123,
            "eccentricity": 0.00067205,
            "inclination_deg": 51.6307,
            "raan_deg": 88.0087,
            "argument_of_pericenter_deg": 246.7167,
            "mean_anomaly_deg": 113.3114,
            "bstar": 0.000205821,
            "mean_motion_dot": 0.00010839,
            "mean_motion_ddot": 0.0,
            "ephemeris_type": 0,
            "classification": "U",
            "element_set_number": 999,
            "revolutions_at_epoch": 58967,
            "center": "EARTH",
            "frame": "TEME",
            "time_system": "UTC",
            "mean_element_theory": "SGP4"
          },
          "source": "CelesTrak GP",
          "source_url": "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=JSON",
          "fetched_at": "2026-10-11T10:07:36.525435Z",
          "content_sha256": "9d78055cff2573f4d18b1f367050542595cb8f714a4de57e118bc42bd9f56a73",
          "data_status": "VALID",
          "warnings": []
        },
        "weather": {
          "treatment": "HYPOTHETICAL_CONSTANT_SOLAR_HISTORY",
          "f107_sfu": 220,
          "ap": 40,
          "label": "ILLUSTRATIVE \u2014 USER-SELECTED UNCERTAINTY ASSUMPTIONS.",
          "density_treatment": "Actual NRLMSIS response, not a constant density multiplier"
        },
        "sample_treatment": "Actual computed samples; evenly indexed subsampling if original count exceeds1001"
      },
      "model": "DOP853 / GCRS / WGS84 central gravity + J2 + co-rotating drag -> Astropy ITRS",
      "warnings": [
        "Bounded research model, not observationally verified decay or operational reentry prediction.",
        "J2 produces short-period osculating-element oscillations; individual semimajor-axis samples need not monotonically decrease.",
        "Fixed gravity pole, offline predictive Earth orientation, no higher harmonics/third bodies and increasing initial-GP uncertainty limit long-horizon accuracy.",
        "No breakup, ablation, fragmentation or ground-impact calculation.",
        "ITRS/ECEF Earth-fixed positions in km; not raw TEME/inertial coordinates.",
        "Installed offline IERS data; predictive/degraded Earth orientation may limit precision.",
        "Three.js right-handed Y-up mapping: (x,y,z)ITRS -> (x,z,-y); one world unit per km or a common display scale.",
        "Earth-fixed sampled paths rotate with Earth and are not closed inertial orbital ellipses."
      ]
    }
  },
  "warnings": [
    "Opt-in compact visualization response; raw scientific samples omitted, not zero-filled.",
    "Metrics/physical assumptions computed from the original full scientific propagation."
  ]
}
```

### Workflow F — F.cleanup

```bash
curl --fail-with-body -sS -X POST http://127.0.0.1:8000/api/cleanup/optimize -H 'Content-Type: application/json' --data '{"candidate_ids":["29733","29734","29735","29736","29737"],"constraints":{"max_targets":2,"max_candidates":5}}'
```

Actual HTTP200 response (21807wire bytes, 1.260978s):

```json
{
  "status": "OPTIMAL_WITHIN_CANDIDATE_POOL",
  "selected_objects": [
    {
      "id": "29734",
      "name": "FENGYUN 1C DEB",
      "classification": "DEBRIS",
      "eligible": true,
      "eligibility_reason": null,
      "element_epoch": "2026-10-10T22:22:24.277152Z",
      "inclination_deg": 99.1649,
      "orbit_metadata": {
        "source": "GP mean elements; SATCAT altitude metadata is not a propagated state",
        "mean_motion_rev_day": 12.92225879,
        "eccentricity": 0.06144479,
        "satcat_apogee_km": 1764.0,
        "satcat_perigee_km": 821.0,
        "altitude_timestamp": "2026-10-10T18:22:58+00:00"
      },
      "screening_exposure": {
        "count": 3,
        "encounter_ids": [
          "socrates-e50365c21530710acdf2f6db",
          "socrates-fb961722916b26d62c171a21",
          "socrates-37a81ed9ec3355ef66af2072"
        ],
        "minimum_source_miss_distance_m": 1892.0,
        "maximum_socrates_screening_metric": 8.952e-07
      },
      "persistence": null,
      "physical_metadata": {
        "mass_kg": null,
        "dimensions_m": null,
        "aerodynamic_area_m2": null,
        "radar_cross_section_m2": 0.04,
        "radar_cross_section_is_not_aerodynamic_area": true
      },
      "missing_data": [
        "mass_kg",
        "dimensions_m",
        "aerodynamic_area_m2",
        "persistence"
      ],
      "provenance": {
        "gp_url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=fengyun-1c-debris&FORMAT=JSON",
        "gp_sha256": "293b2d758ba0ef80b1fbacb4fe1d06c4f2c5e1496a0845881adbb264deaac139",
        "gp_fetched_at": "2026-10-11T08:18:13.482780+00:00",
        "gp_data_status": "VALID",
        "object_type": {
          "id": "29734",
          "name": "FENGYUN 1C DEB",
          "classification": "DEBRIS",
          "source_object_type": "DEB",
          "operational_status_code": null,
          "decay_date": null,
          "orbit_center": "EA",
          "orbit_type": "ORB",
          "radar_cross_section_m2": 0.04,
          "apogee_km": 1764.0,
          "perigee_km": 821.0,
          "mass_kg": null,
          "dimensions_m": null,
          "aerodynamic_area_m2": null,
          "provenance": {
            "source": "CelesTrak SATCAT",
            "source_url": "https://celestrak.org/pub/satcat.csv",
            "fetched_at": "2026-10-11T09:24:23.939547+00:00",
            "dataset_timestamp": "2026-10-10T18:22:58+00:00",
            "content_sha256": "f43644ebcbf57575a9e937f785a3cb8b828c7df8f54cbe2c51cfafcaf37fb294",
            "retrieval_mode": "CACHE"
          }
        }
      },
      "warnings": [
        "Removal feasibility, physical properties and mission costs are not established."
      ]
    },
    {
      "id": "29737",
      "name": "FENGYUN 1C DEB",
      "classification": "DEBRIS",
      "eligible": true,
      "eligibility_reason": null,
      "element_epoch": "2026-10-10T13:40:34.155264Z",
      "inclination_deg": 99.5751,
      "orbit_metadata": {
        "source": "GP mean elements; SATCAT altitude metadata is not a propagated state",
        "mean_motion_rev_day": 12.66255747,
        "eccentricity": 0.06898143,
        "satcat_apogee_km": 1934.0,
        "satcat_perigee_km": 861.0,
        "altitude_timestamp": "2026-10-10T18:22:58+00:00"
      },
      "screening_exposure": {
        "count": 3,
        "encounter_ids": [
          "socrates-01faf09595b1e1c3c3be651c",
          "socrates-ad2954ed3c27ab3380602f88",
          "socrates-f4d65f82893e42d2b06a9752"
        ],
        "minimum_source_miss_distance_m": 4005.0,
        "maximum_socrates_screening_metric": 5.436e-07
      },
      "persistence": null,
      "physical_metadata": {
        "mass_kg": null,
        "dimensions_m": null,
        "aerodynamic_area_m2": null,
        "radar_cross_section_m2": 0.0312,
        "radar_cross_section_is_not_aerodynamic_area": true
      },
      "missing_data": [
        "mass_kg",
        "dimensions_m",
        "aerodynamic_area_m2",
        "persistence"
      ],
      "provenance": {
        "gp_url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=fengyun-1c-debris&FORMAT=JSON",
        "gp_sha256": "293b2d758ba0ef80b1fbacb4fe1d06c4f2c5e1496a0845881adbb264deaac139",
        "gp_fetched_at": "2026-10-11T08:18:13.482780+00:00",
        "gp_data_status": "VALID",
        "object_type": {
          "id": "29737",
          "name": "FENGYUN 1C DEB",
          "classification": "DEBRIS",
          "source_object_type": "DEB",
          "operational_status_code": null,
          "decay_date": null,
          "orbit_center": "EA",
          "orbit_type": "ORB",
          "radar_cross_section_m2": 0.0312,
          "apogee_km": 1934.0,
          "perigee_km": 861.0,
          "mass_kg": null,
          "dimensions_m": null,
          "aerodynamic_area_m2": null,
          "provenance": {
            "source": "CelesTrak SATCAT",
            "source_url": "https://celestrak.org/pub/satcat.csv",
            "fetched_at": "2026-10-11T09:24:23.939547+00:00",
            "dataset_timestamp": "2026-10-10T18:22:58+00:00",
            "content_sha256": "f43644ebcbf57575a9e937f785a3cb8b828c7df8f54cbe2c51cfafcaf37fb294",
            "retrieval_mode": "CACHE"
          }
        }
      },
      "warnings": [
        "Removal feasibility, physical properties and mission costs are not established."
      ]
    }
  ],
  "priority_ranking": [
    {
      "id": "29734",
      "score": 0.3,
      "score_interval": [
        0.3,
        0.3
      ],
      "status": "RANKABLE",
      "components": {
        "screening_exposure": {
          "value": 0.3,
          "weight": 1.0,
          "contribution": 0.3,
          "status": "AVAILABLE"
        },
        "modeled_persistence": {
          "value": null,
          "weight": 0.0,
          "contribution": 0.0,
          "status": "UNAVAILABLE"
        },
        "radar_cross_section": {
          "value": 0.01635630779967729,
          "weight": 0.0,
          "contribution": 0.0,
          "status": "AVAILABLE"
        }
      },
      "reasons": []
    },
    {
      "id": "29737",
      "score": 0.3,
      "score_interval": [
        0.3,
        0.3
      ],
      "status": "RANKABLE",
      "components": {
        "screening_exposure": {
          "value": 0.3,
          "weight": 1.0,
          "contribution": 0.3,
          "status": "AVAILABLE"
        },
        "modeled_persistence": {
          "value": null,
          "weight": 0.0,
          "contribution": 0.0,
          "status": "UNAVAILABLE"
        },
        "radar_cross_section": {
          "value": 0.012812558159383789,
          "weight": 0.0,
          "contribution": 0.0,
          "status": "AVAILABLE"
        }
      },
      "reasons": []
    },
    {
      "id": "29735",
      "score": 0.2,
      "score_interval": [
        0.2,
        0.2
      ],
      "status": "RANKABLE",
      "components": {
        "screening_exposure": {
          "value": 0.2,
          "weight": 1.0,
          "contribution": 0.2,
          "status": "AVAILABLE"
        },
        "modeled_persistence": {
          "value": null,
          "weight": 0.0,
          "contribution": 0.0,
          "status": "UNAVAILABLE"
        },
        "radar_cross_section": {
          "value": 0.017757425863485075,
          "weight": 0.0,
          "contribution": 0.0,
          "status": "AVAILABLE"
        }
      },
      "reasons": []
    },
    {
      "id": "29736",
      "score": 0.1,
      "score_interval": [
        0.1,
        0.1
      ],
      "status": "RANKABLE",
      "components": {
        "screening_exposure": {
          "value": 0.1,
          "weight": 1.0,
          "contribution": 0.1,
          "status": "AVAILABLE"
        },
        "modeled_persistence": {
          "value": null,
          "weight": 0.0,
          "contribution": 0.0,
          "status": "UNAVAILABLE"
        },
        "radar_cross_section": {
          "value": 0.004686039483648677,
          "weight": 0.0,
          "contribution": 0.0,
          "status": "AVAILABLE"
        }
      },
      "reasons": []
    },
    {
      "id": "29733",
      "score": 0.0,
      "score_interval": [
        0.0,
        0.0
      ],
      "status": "RANKABLE",
      "components": {
        "screening_exposure": {
          "value": 0.0,
          "weight": 1.0,
          "contribution": 0.0,
          "status": "AVAILABLE"
        },
        "modeled_persistence": {
          "value": null,
          "weight": 0.0,
          "contribution": 0.0,
          "status": "UNAVAILABLE"
        },
        "radar_cross_section": {
          "value": 0.015995258138068444,
          "weight": 0.0,
          "contribution": 0.0,
          "status": "AVAILABLE"
        }
      },
      "reasons": []
    }
  ],
  "candidates": [
    {
      "id": "29733",
      "name": "FENGYUN 1C DEB",
      "classification": "DEBRIS",
      "eligible": true,
      "eligibility_reason": null,
      "element_epoch": "2026-10-10T06:41:22.570944Z",
      "inclination_deg": 99.2041,
      "orbit_metadata": {
        "source": "GP mean elements; SATCAT altitude metadata is not a propagated state",
        "mean_motion_rev_day": 12.96942344,
        "eccentricity": 0.05647527,
        "satcat_apogee_km": 1706.0,
        "satcat_perigee_km": 842.0,
        "altitude_timestamp": "2026-10-10T18:22:58+00:00"
      },
      "screening_exposure": {
        "count": 0,
        "encounter_ids": [],
        "minimum_source_miss_distance_m": null,
        "maximum_socrates_screening_metric": null
      },
      "persistence": null,
      "physical_metadata": {
        "mass_kg": null,
        "dimensions_m": null,
        "aerodynamic_area_m2": null,
        "radar_cross_section_m2": 0.0391,
        "radar_cross_section_is_not_aerodynamic_area": true
      },
      "missing_data": [
        "mass_kg",
        "dimensions_m",
        "aerodynamic_area_m2",
        "persistence"
      ],
      "provenance": {
        "gp_url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=fengyun-1c-debris&FORMAT=JSON",
        "gp_sha256": "293b2d758ba0ef80b1fbacb4fe1d06c4f2c5e1496a0845881adbb264deaac139",
        "gp_fetched_at": "2026-10-11T08:18:13.482780+00:00",
        "gp_data_status": "VALID",
        "object_type": {
          "id": "29733",
          "name": "FENGYUN 1C DEB",
          "classification": "DEBRIS",
          "source_object_type": "DEB",
          "operational_status_code": null,
          "decay_date": null,
          "orbit_center": "EA",
          "orbit_type": "ORB",
          "radar_cross_section_m2": 0.0391,
          "apogee_km": 1706.0,
          "perigee_km": 842.0,
          "mass_kg": null,
          "dimensions_m": null,
          "aerodynamic_area_m2": null,
          "provenance": {
            "source": "CelesTrak SATCAT",
            "source_url": "https://celestrak.org/pub/satcat.csv",
            "fetched_at": "2026-10-11T09:24:23.939547+00:00",
            "dataset_timestamp": "2026-10-10T18:22:58+00:00",
            "content_sha256": "f43644ebcbf57575a9e937f785a3cb8b828c7df8f54cbe2c51cfafcaf37fb294",
            "retrieval_mode": "CACHE"
          }
        }
      },
      "warnings": [
        "Removal feasibility, physical properties and mission costs are not established."
      ]
    },
    {
      "id": "29734",
      "name": "FENGYUN 1C DEB",
      "classification": "DEBRIS",
      "eligible": true,
      "eligibility_reason": null,
      "element_epoch": "2026-10-10T22:22:24.277152Z",
      "inclination_deg": 99.1649,
      "orbit_metadata": {
        "source": "GP mean elements; SATCAT altitude metadata is not a propagated state",
        "mean_motion_rev_day": 12.92225879,
        "eccentricity": 0.06144479,
        "satcat_apogee_km": 1764.0,
        "satcat_perigee_km": 821.0,
        "altitude_timestamp": "2026-10-10T18:22:58+00:00"
      },
      "screening_exposure": {
        "count": 3,
        "encounter_ids": [
          "socrates-e50365c21530710acdf2f6db",
          "socrates-fb961722916b26d62c171a21",
          "socrates-37a81ed9ec3355ef66af2072"
        ],
        "minimum_source_miss_distance_m": 1892.0,
        "maximum_socrates_screening_metric": 8.952e-07
      },
      "persistence": null,
      "physical_metadata": {
        "mass_kg": null,
        "dimensions_m": null,
        "aerodynamic_area_m2": null,
        "radar_cross_section_m2": 0.04,
        "radar_cross_section_is_not_aerodynamic_area": true
      },
      "missing_data": [
        "mass_kg",
        "dimensions_m",
        "aerodynamic_area_m2",
        "persistence"
      ],
      "provenance": {
        "gp_url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=fengyun-1c-debris&FORMAT=JSON",
        "gp_sha256": "293b2d758ba0ef80b1fbacb4fe1d06c4f2c5e1496a0845881adbb264deaac139",
        "gp_fetched_at": "2026-10-11T08:18:13.482780+00:00",
        "gp_data_status": "VALID",
        "object_type": {
          "id": "29734",
          "name": "FENGYUN 1C DEB",
          "classification": "DEBRIS",
          "source_object_type": "DEB",
          "operational_status_code": null,
          "decay_date": null,
          "orbit_center": "EA",
          "orbit_type": "ORB",
          "radar_cross_section_m2": 0.04,
          "apogee_km": 1764.0,
          "perigee_km": 821.0,
          "mass_kg": null,
          "dimensions_m": null,
          "aerodynamic_area_m2": null,
          "provenance": {
            "source": "CelesTrak SATCAT",
            "source_url": "https://celestrak.org/pub/satcat.csv",
            "fetched_at": "2026-10-11T09:24:23.939547+00:00",
            "dataset_timestamp": "2026-10-10T18:22:58+00:00",
            "content_sha256": "f43644ebcbf57575a9e937f785a3cb8b828c7df8f54cbe2c51cfafcaf37fb294",
            "retrieval_mode": "CACHE"
          }
        }
      },
      "warnings": [
        "Removal feasibility, physical properties and mission costs are not established."
      ]
    },
    {
      "id": "29735",
      "name": "FENGYUN 1C DEB",
      "classification": "DEBRIS",
      "eligible": true,
      "eligibility_reason": null,
      "element_epoch": "2026-10-10T22:23:41.407296Z",
      "inclination_deg": 99.3789,
      "orbit_metadata": {
        "source": "GP mean elements; SATCAT altitude metadata is not a propagated state",
        "mean_motion_rev_day": 12.75897585,
        "eccentricity": 0.0696306,
        "satcat_apogee_km": 1897.0,
        "satcat_perigee_km": 819.0,
        "altitude_timestamp": "2026-10-10T18:22:58+00:00"
      },
      "screening_exposure": {
        "count": 2,
        "encounter_ids": [
          "socrates-06bd0f9954923c6591d08141",
          "socrates-5c10cef03e88a9ed8b69fe53"
        ],
        "minimum_source_miss_distance_m": 2544.0,
        "maximum_socrates_screening_metric": 7.588e-07
      },
      "persistence": null,
      "physical_metadata": {
        "mass_kg": null,
        "dimensions_m": null,
        "aerodynamic_area_m2": null,
        "radar_cross_section_m2": 0.0435,
        "radar_cross_section_is_not_aerodynamic_area": true
      },
      "missing_data": [
        "mass_kg",
        "dimensions_m",
        "aerodynamic_area_m2",
        "persistence"
      ],
      "provenance": {
        "gp_url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=fengyun-1c-debris&FORMAT=JSON",
        "gp_sha256": "293b2d758ba0ef80b1fbacb4fe1d06c4f2c5e1496a0845881adbb264deaac139",
        "gp_fetched_at": "2026-10-11T08:18:13.482780+00:00",
        "gp_data_status": "VALID",
        "object_type": {
          "id": "29735",
          "name": "FENGYUN 1C DEB",
          "classification": "DEBRIS",
          "source_object_type": "DEB",
          "operational_status_code": null,
          "decay_date": null,
          "orbit_center": "EA",
          "orbit_type": "ORB",
          "radar_cross_section_m2": 0.0435,
          "apogee_km": 1897.0,
          "perigee_km": 819.0,
          "mass_kg": null,
          "dimensions_m": null,
          "aerodynamic_area_m2": null,
          "provenance": {
            "source": "CelesTrak SATCAT",
            "source_url": "https://celestrak.org/pub/satcat.csv",
            "fetched_at": "2026-10-11T09:24:23.939547+00:00",
            "dataset_timestamp": "2026-10-10T18:22:58+00:00",
            "content_sha256": "f43644ebcbf57575a9e937f785a3cb8b828c7df8f54cbe2c51cfafcaf37fb294",
            "retrieval_mode": "CACHE"
          }
        }
      },
      "warnings": [
        "Removal feasibility, physical properties and mission costs are not established."
      ]
    },
    {
      "id": "29736",
      "name": "FENGYUN 1C DEB",
      "classification": "DEBRIS",
      "eligible": true,
      "eligibility_reason": null,
      "element_epoch": "2026-10-09T19:58:04.653120Z",
      "inclination_deg": 99.4391,
      "orbit_metadata": {
        "source": "GP mean elements; SATCAT altitude metadata is not a propagated state",
        "mean_motion_rev_day": 12.57851045,
        "eccentricity": 0.07257395,
        "satcat_apogee_km": 1999.0,
        "satcat_perigee_km": 865.0,
        "altitude_timestamp": "2026-10-10T18:22:58+00:00"
      },
      "screening_exposure": {
        "count": 1,
        "encounter_ids": [
          "socrates-60cf220bfbd5beb48e57db2e"
        ],
        "minimum_source_miss_distance_m": 3911.0,
        "maximum_socrates_screening_metric": 3.183e-07
      },
      "persistence": null,
      "physical_metadata": {
        "mass_kg": null,
        "dimensions_m": null,
        "aerodynamic_area_m2": null,
        "radar_cross_section_m2": 0.0113,
        "radar_cross_section_is_not_aerodynamic_area": true
      },
      "missing_data": [
        "mass_kg",
        "dimensions_m",
        "aerodynamic_area_m2",
        "persistence"
      ],
      "provenance": {
        "gp_url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=fengyun-1c-debris&FORMAT=JSON",
        "gp_sha256": "293b2d758ba0ef80b1fbacb4fe1d06c4f2c5e1496a0845881adbb264deaac139",
        "gp_fetched_at": "2026-10-11T08:18:13.482780+00:00",
        "gp_data_status": "VALID",
        "object_type": {
          "id": "29736",
          "name": "FENGYUN 1C DEB",
          "classification": "DEBRIS",
          "source_object_type": "DEB",
          "operational_status_code": null,
          "decay_date": null,
          "orbit_center": "EA",
          "orbit_type": "ORB",
          "radar_cross_section_m2": 0.0113,
          "apogee_km": 1999.0,
          "perigee_km": 865.0,
          "mass_kg": null,
          "dimensions_m": null,
          "aerodynamic_area_m2": null,
          "provenance": {
            "source": "CelesTrak SATCAT",
            "source_url": "https://celestrak.org/pub/satcat.csv",
            "fetched_at": "2026-10-11T09:24:23.939547+00:00",
            "dataset_timestamp": "2026-10-10T18:22:58+00:00",
            "content_sha256": "f43644ebcbf57575a9e937f785a3cb8b828c7df8f54cbe2c51cfafcaf37fb294",
            "retrieval_mode": "CACHE"
          }
        }
      },
      "warnings": [
        "Removal feasibility, physical properties and mission costs are not established."
      ]
    },
    {
      "id": "29737",
      "name": "FENGYUN 1C DEB",
      "classification": "DEBRIS",
      "eligible": true,
      "eligibility_reason": null,
      "element_epoch": "2026-10-10T13:40:34.155264Z",
      "inclination_deg": 99.5751,
      "orbit_metadata": {
        "source": "GP mean elements; SATCAT altitude metadata is not a propagated state",
        "mean_motion_rev_day": 12.66255747,
        "eccentricity": 0.06898143,
        "satcat_apogee_km": 1934.0,
        "satcat_perigee_km": 861.0,
        "altitude_timestamp": "2026-10-10T18:22:58+00:00"
      },
      "screening_exposure": {
        "count": 3,
        "encounter_ids": [
          "socrates-01faf09595b1e1c3c3be651c",
          "socrates-ad2954ed3c27ab3380602f88",
          "socrates-f4d65f82893e42d2b06a9752"
        ],
        "minimum_source_miss_distance_m": 4005.0,
        "maximum_socrates_screening_metric": 5.436e-07
      },
      "persistence": null,
      "physical_metadata": {
        "mass_kg": null,
        "dimensions_m": null,
        "aerodynamic_area_m2": null,
        "radar_cross_section_m2": 0.0312,
        "radar_cross_section_is_not_aerodynamic_area": true
      },
      "missing_data": [
        "mass_kg",
        "dimensions_m",
        "aerodynamic_area_m2",
        "persistence"
      ],
      "provenance": {
        "gp_url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=fengyun-1c-debris&FORMAT=JSON",
        "gp_sha256": "293b2d758ba0ef80b1fbacb4fe1d06c4f2c5e1496a0845881adbb264deaac139",
        "gp_fetched_at": "2026-10-11T08:18:13.482780+00:00",
        "gp_data_status": "VALID",
        "object_type": {
          "id": "29737",
          "name": "FENGYUN 1C DEB",
          "classification": "DEBRIS",
          "source_object_type": "DEB",
          "operational_status_code": null,
          "decay_date": null,
          "orbit_center": "EA",
          "orbit_type": "ORB",
          "radar_cross_section_m2": 0.0312,
          "apogee_km": 1934.0,
          "perigee_km": 861.0,
          "mass_kg": null,
          "dimensions_m": null,
          "aerodynamic_area_m2": null,
          "provenance": {
            "source": "CelesTrak SATCAT",
            "source_url": "https://celestrak.org/pub/satcat.csv",
            "fetched_at": "2026-10-11T09:24:23.939547+00:00",
            "dataset_timestamp": "2026-10-10T18:22:58+00:00",
            "content_sha256": "f43644ebcbf57575a9e937f785a3cb8b828c7df8f54cbe2c51cfafcaf37fb294",
            "retrieval_mode": "CACHE"
          }
        }
      },
      "warnings": [
        "Removal feasibility, physical properties and mission costs are not established."
      ]
    }
  ],
  "total_priority_proxy": 0.6,
  "resource_model": "TARGET_COUNT",
  "targets_remaining": 0,
  "total_abstract_resource_expenditure": 2.0,
  "budget_remaining": null,
  "excluded_objects": {},
  "selection_reasons": {
    "29734": "Eligible and rankable; additive proxy 0.3; selected within the declared candidate pool and resource constraints (OPTIMAL_WITHIN_CANDIDATE_POOL)",
    "29737": "Eligible and rankable; additive proxy 0.3; selected within the declared candidate pool and resource constraints (OPTIMAL_WITHIN_CANDIDATE_POOL)"
  },
  "unique_screening_encounters_represented": 6,
  "shared_screening_encounter_ids": [],
  "policy": {
    "exposure_weight": 1.0,
    "persistence_weight": 0.0,
    "radar_cross_section_weight": 0.0,
    "exposure_saturation_count": 10,
    "persistence_saturation_days": 30.0,
    "radar_cross_section_saturation_m2": 10.0
  },
  "constraints": {
    "max_targets": 2,
    "max_candidates": 5,
    "excluded_ids": [],
    "effort_costs": null,
    "effort_budget": null,
    "solver_timeout_seconds": 10.0
  },
  "coverage": {
    "catalog": {
      "objects_available": 19505,
      "coverage": "PARTIAL",
      "freshness_status": "STALE",
      "sources": [
        {
          "source_url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=JSON",
          "content_sha256": "c89aff71574eb31d47d648badca6f494f864c8c83ba90523670cc8043110c7b6",
          "retrieved_at": "2026-10-11T08:18:13.482780Z",
          "dataset_timestamp": "2026-10-11T08:18:13.482780Z",
          "timestamp_basis": "FETCH_TIME",
          "retrieval_mode": "CACHE",
          "usable_records": 16701,
          "rejected_records": 0,
          "duplicate_records": 0
        },
        {
          "source_url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=cosmos-2251-debris&FORMAT=JSON",
          "content_sha256": "86dc8a5f346e5195cd7290a6cb8ebcc986a4bbadf6904cc296d613035bd12ac5",
          "retrieved_at": "2026-10-11T08:18:13.482780Z",
          "dataset_timestamp": "2026-10-11T08:18:13.482780Z",
          "timestamp_basis": "FETCH_TIME",
          "retrieval_mode": "CACHE",
          "usable_records": 588,
          "rejected_records": 0,
          "duplicate_records": 0
        },
        {
          "source_url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=iridium-33-debris&FORMAT=JSON",
          "content_sha256": "7f65418e427db3cf7db8d7cb410af64155a0d636cc281e90fa05da6b96f2a22e",
          "retrieved_at": "2026-10-11T08:18:13.482780Z",
          "dataset_timestamp": "2026-10-11T08:18:13.482780Z",
          "timestamp_basis": "FETCH_TIME",
          "retrieval_mode": "CACHE",
          "usable_records": 109,
          "rejected_records": 0,
          "duplicate_records": 0
        },
        {
          "source_url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=fengyun-1c-debris&FORMAT=JSON",
          "content_sha256": "293b2d758ba0ef80b1fbacb4fe1d06c4f2c5e1496a0845881adbb264deaac139",
          "retrieved_at": "2026-10-11T08:18:13.482780Z",
          "dataset_timestamp": "2026-10-11T08:18:13.482780Z",
          "timestamp_basis": "FETCH_TIME",
          "retrieval_mode": "CACHE",
          "usable_records": 1979,
          "rejected_records": 0,
          "duplicate_records": 0
        },
        {
          "source_url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=JSON",
          "content_sha256": "cd42a4ff3c60600d032720170017beed4f85101f7a925f72c70708470ebf7b1f",
          "retrieved_at": "2026-10-11T08:18:13.482780Z",
          "dataset_timestamp": "2026-10-11T08:18:13.482780Z",
          "timestamp_basis": "FETCH_TIME",
          "retrieval_mode": "CACHE",
          "usable_records": 156,
          "rejected_records": 0,
          "duplicate_records": 0
        }
      ],
      "snapshot_sha256": "e13054e93164ac9bf0affe6c95b2729229a29fc94327efc9c978734ea46ba305",
      "assembled_at": "2026-10-11T10:07:07.185023Z",
      "oldest_element_epoch": "2026-09-11T12:27:56.057184Z",
      "newest_element_epoch": "2026-10-12T17:36:20.007360Z",
      "rejected_record_count": 0,
      "duplicate_count": 28,
      "failed_sources": [],
      "coverage_limitations": [
        "PARTIAL catalog: only the selected available public GP groups, local OMM datasets and explicitly selected caches.",
        "GROUP=active does not contain all debris; debris groups cover only their named populations.",
        "Not all tracked objects have public GP data; untracked and restricted objects are absent.",
        "No completeness against the full orbiting population has been established.",
        "Newest element epoch retained per canonical NORAD ID; source datasets may have different retrieval times."
      ],
      "warnings": [
        "215 records have epochs more than seven days from assembly time; retained but must not be silently screened as current."
      ]
    },
    "screening": {
      "status": "VALID",
      "source_url": "https://celestrak.org/SOCRATES/sort-minRange.csv",
      "content_sha256": "4e8b1a87555c4ef98cec6327e5c4140ee3893f7ada7818f1faa3f0f3c8745fb7",
      "dataset_timestamp": "2026-10-10T15:48:20+00:00",
      "fetched_at": "2026-10-11T02:40:21.988220+00:00",
      "upcoming_unique_encounters": 160761,
      "tca_start": "2026-10-11T10:07:38.760000+00:00",
      "tca_end": "2026-10-17T01:59:57.920000+00:00",
      "selection_start": "2026-10-11T10:07:38.298965+00:00",
      "limitations": [
        "Published predicted screening events, not observed collisions or a complete long-term collision frequency.",
        "No matches means no published matches within this limited snapshot/window, not zero actual risk.",
        "SOCRATES MAX_PROB is retained separately and is not covariance-based Pc or a priority probability."
      ]
    },
    "classification": {
      "source": "CelesTrak SATCAT",
      "source_url": "https://celestrak.org/pub/satcat.csv",
      "fetched_at": "2026-10-11T09:24:23.939547+00:00",
      "dataset_timestamp": "2026-10-10T18:22:58+00:00",
      "content_sha256": "f43644ebcbf57575a9e937f785a3cb8b828c7df8f54cbe2c51cfafcaf37fb294",
      "retrieval_mode": "CACHE",
      "records": 70980,
      "rejected_records": 0,
      "duplicate_records": 0
    },
    "candidate_pool_truncated": 0,
    "scope": "Explicit selected IDs"
  },
  "model_assumptions": [
    "ILLUSTRATIVE POLICY CHOICE \u2014 additive priority proxy, not a mission plan or scientifically universal weighting.",
    "Exposure=min(count/saturation,1); persistence=min(modeled days/saturation,1); RCS=min(log1p(RCS)/log1p(saturation),1).",
    "Weights normalized once across configured criteria, not renormalized over available metadata; missing positively weighted evidence is unrankable, not zero.",
    "Data quality controls eligibility/comparability and is disclosed, never a bonus for more metadata.",
    "Persistence is explicitly modeled/censored scenario evidence, never inferred infinite lifetime or an observed reentry date.",
    "Shared source conjunctions can contribute to both object priorities, but this additive proxy is NOT independently prevented collisions; unique/shared event identities are reported.",
    "Abstract effort units are user-provided, not dollars, removal feasibility or estimated mission cost.",
    "Fixed-count selection sorts genuine scores; effort selection uses bounded binary HiGHS MILP and verifies actual resource sums."
  ],
  "warnings": [
    "SATCAT type/status are catalog metadata, not verified removal feasibility.",
    "Radar cross section is not aerodynamic area, dimensions or mass; these remain unknown.",
    "Catalog metadata can lag actual physical/operational status; unknown/conflicting types are not eligible."
  ]
}
```

<!-- GENERATED API SCHEMAS BELOW -->

## Exact generated endpoint and schema appendix

Generated from the running application models, not guessed endpoints. `openapi.json` is the machine-readable authority. Missing optional fields and null are distinct; required is shown below. Objects/maps declared open-ended retain their documented scientific/provenance contents.


### GET /api/health

| Input | Location | Required | Schema |
| --- | --- | --- | --- |

Responses:

- HTTP200: HealthResponse
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### GET /api/status

| Input | Location | Required | Schema |
| --- | --- | --- | --- |

Responses:

- HTTP200: StatusResponse
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### GET /api/catalog/status

| Input | Location | Required | Schema |
| --- | --- | --- | --- |

Responses:

- HTTP200: CatalogStatusResponse
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### GET /api/encounters

| Input | Location | Required | Schema |
| --- | --- | --- | --- |
| sort | query | False | `screening`, `max_probability`, `minimum_separation`, `time` |
| limit | query | False | integer {"minimum":1,"maximum":1000} |
| object_id | query | False | string \| null |
| name | query | False | string \| null |
| offset | query | False | integer {"minimum":0,"maximum":1000000} |
| start_time | query | False | string (date-time) \| null |
| end_time | query | False | string (date-time) \| null |

Responses:

- HTTP200: EncounterListResponse
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### GET /api/encounters/{encounter_id}

| Input | Location | Required | Schema |
| --- | --- | --- | --- |
| encounter_id | path | True | string |

Responses:

- HTTP200: ScreenedEncounter
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### POST /api/probability/calculate

| Input | Location | Required | Schema |
| --- | --- | --- | --- |
| body | JSON | True | DirectProbabilityRequest \| ReferenceProbabilityRequest |

Responses:

- HTTP200: ProbabilityAnalysis \| ReferenceComparison
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### POST /api/encounters/{encounter_id}/analyze

| Input | Location | Required | Schema |
| --- | --- | --- | --- |
| encounter_id | path | True | string |
| body | JSON | False | AnalyzeRequest \| null |

Responses:

- HTTP200: ProbabilityBaselineAnalysis \| BaselineAnalysis
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### POST /api/encounters/{encounter_id}/simulate

| Input | Location | Required | Schema |
| --- | --- | --- | --- |
| encounter_id | path | True | string |
| body | JSON | True | SimulateRequest |

Responses:

- HTTP200: ProbabilityManeuverSimulation \| ManeuverSimulation
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### POST /api/encounters/{encounter_id}/optimize

| Input | Location | Required | Schema |
| --- | --- | --- | --- |
| encounter_id | path | True | string |
| body | JSON | True | OptimizeRequest |

Responses:

- HTTP200: OptimizationResult
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### POST /api/encounters/{encounter_id}/screen

| Input | Location | Required | Schema |
| --- | --- | --- | --- |
| encounter_id | path | True | string |
| body | JSON | True | ScreenRequest |

Responses:

- HTTP200: ScreeningResult
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### GET /api/objects/{object_id}

| Input | Location | Required | Schema |
| --- | --- | --- | --- |
| object_id | path | True | string |

Responses:

- HTTP200: OrbitalRecord
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### GET /api/space-weather/status

| Input | Location | Required | Schema |
| --- | --- | --- | --- |
| load | query | False | boolean |

Responses:

- HTTP200: SpaceWeatherStatus
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### POST /api/atmosphere/density

| Input | Location | Required | Schema |
| --- | --- | --- | --- |
| body | JSON | True | DensityRequest |

Responses:

- HTTP200: DensityResult
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### POST /api/objects/{object_id}/decay

| Input | Location | Required | Schema |
| --- | --- | --- | --- |
| object_id | path | True | string |
| body | JSON | True | PersistenceRequest |

Responses:

- HTTP200: PersistenceVisualization \| PersistenceAnalysis
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### POST /api/objects/{object_id}/persistence

| Input | Location | Required | Schema |
| --- | --- | --- | --- |
| object_id | path | True | string |
| body | JSON | True | PersistenceRequest |

Responses:

- HTTP200: PersistenceVisualization \| PersistenceAnalysis
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### GET /api/objects

| Input | Location | Required | Schema |
| --- | --- | --- | --- |
| search | query | False | string {"maxLength":100} \| null |
| classification | query | False | `PAYLOAD`, `ROCKET_BODY`, `DEBRIS`, `UNKNOWN` \| null |
| offset | query | False | integer {"minimum":0,"maximum":1000000} |
| limit | query | False | integer {"minimum":1,"maximum":500} |

Responses:

- HTTP200: CatalogPage
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### POST /api/positions

| Input | Location | Required | Schema |
| --- | --- | --- | --- |
| body | JSON | True | PositionRequest |

Responses:

- HTTP200: PositionBatch
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### GET /api/objects/{object_id}/metadata

| Input | Location | Required | Schema |
| --- | --- | --- | --- |
| object_id | path | True | string |

Responses:

- HTTP200: ObjectInfo
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### GET /api/objects/{object_id}/trajectory

| Input | Location | Required | Schema |
| --- | --- | --- | --- |
| object_id | path | True | string |
| start_time | query | False | string (date-time) \| null |
| end_time | query | False | string (date-time) \| null |
| sample_count | query | False | integer {"minimum":2,"maximum":1001} |

Responses:

- HTTP200: ObjectTrajectory
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### GET /api/encounters/{encounter_id}/trajectories

| Input | Location | Required | Schema |
| --- | --- | --- | --- |
| encounter_id | path | True | string |
| half_window_seconds | query | False | number {"exclusiveMinimum":0,"maximum":1800} |
| sample_count | query | False | integer {"minimum":2,"maximum":1001} |

Responses:

- HTTP200: EncounterTrajectories
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### POST /api/encounters/{encounter_id}/trajectories

| Input | Location | Required | Schema |
| --- | --- | --- | --- |
| encounter_id | path | True | string |
| body | JSON | True | ManeuverTrajectoryRequest |

Responses:

- HTTP200: ManeuverTrajectories
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### POST /api/cleanup/optimize

| Input | Location | Required | Schema |
| --- | --- | --- | --- |
| body | JSON | True | CleanupRequest |

Responses:

- HTTP200: CleanupPortfolio
- HTTP422: ScientificErrorResponse \| ValidationFailure
- HTTP404: ScientificErrorResponse
- HTTP503: ScientificErrorResponse
- HTTP429: ScientificErrorResponse

### Schema: AnalyzeRequest



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| half_window_seconds | False | number {"exclusiveMinimum":0.0,"maximum":1800.0} | 300 |
| probability_analysis | False | boolean | false |
| probability_inputs | False | ProbabilityInputs \| null | — |

### Schema: BaselineAnalysis



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| encounter_id | True | string | — |
| source | False | `SOCRATES` | "SOCRATES" |
| published | True | PublishedPrediction | — |
| calculated | True | ClosestApproach | — |
| model | False | `SGP4 / TEME / WGS72` | "SGP4 / TEME / WGS72" |
| element_epochs | True | tuple[string (date-time), string (date-time)] {"minItems":2,"maxItems":2} | — |
| orbital_source_checksums | True | tuple[string, string] {"minItems":2,"maxItems":2} | — |
| source_model_disagreement | True | boolean | — |
| warnings | True | array<string> | — |

### Schema: BoundaryAnalysis



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| prediction_status | True | `BOUNDARY_REACHED`, `NOT_REACHED_WITHIN_HORIZON`, `INSUFFICIENT_OBJECT_PROPERTIES`, `INSUFFICIENT_ENVIRONMENT_DATA`, `INITIAL_STATE_UNSUPPORTED`, `NUMERICAL_FAILURE`, `MODEL_OUT_OF_VALIDITY` | — |
| boundary_altitude_m | True | number | — |
| crossing_occurred | False | boolean | false |
| crossing_time | False | string (date-time) \| null | — |
| modeled_time_until_crossing_seconds | False | number {"minimum":0.0} \| null | — |
| prediction_horizon_days | True | number {"exclusiveMinimum":0.0,"maximum":90.0} | — |
| propagation | False | DecayPropagation \| null | — |
| assumptions | True | array<string> | — |
| warnings | True | array<string> | — |

### Schema: CandidateScreeningAssessment



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| primary_rank | True | integer {"minimum":1.0} | — |
| maneuver_time | True | string (date-time) | — |
| delta_v_rtn_m_s | True | tuple[number, number, number] {"minItems":3,"maxItems":3} | — |
| primary_miss_distance_m | True | number | — |
| primary_improvement_m | True | number | — |
| screening | True | ScreeningResult \| null | — |
| policy_passed | True | boolean \| null | — |
| selected | False | boolean | false |
| warnings | False | array<string> | — |

### Schema: CatalogMetadata



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| objects_available | True | integer {"minimum":0.0} | — |
| coverage | False | `PARTIAL` | "PARTIAL" |
| freshness_status | True | `FRESH`, `STALE`, `UNAVAILABLE` | — |
| sources | True | array<CatalogSource> | — |
| snapshot_sha256 | True | string | — |
| assembled_at | True | string (date-time) | — |
| oldest_element_epoch | True | string (date-time) \| null | — |
| newest_element_epoch | True | string (date-time) \| null | — |
| rejected_record_count | True | integer {"minimum":0.0} | — |
| duplicate_count | True | integer {"minimum":0.0} | — |
| failed_sources | False | array<string> | — |
| coverage_limitations | True | array<string> | — |
| warnings | False | array<string> | — |

### Schema: CatalogPage



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| items | True | array<ObjectSummary> | — |
| total | True | integer | — |
| offset | True | integer | — |
| limit | True | integer | — |
| next_offset | True | integer \| null | — |
| catalog | True | CatalogMetadata | — |
| metadata_source | True | object \| null | — |
| warnings | True | array<string> | — |

### Schema: CatalogSelection



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| groups | False | array<string> | ["active", "cosmos-2251-debris", "iridium-33-debris", "fengyun-1c-debris", "visual"] |
| local_files | False | array<string (path)> | [] |
| include_cached_records | False | boolean | false |

### Schema: CatalogSource



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| source_url | True | string | — |
| content_sha256 | True | string | — |
| retrieved_at | True | string (date-time) | — |
| dataset_timestamp | True | string (date-time) | — |
| timestamp_basis | True | string | — |
| retrieval_mode | True | `HTTP`, `CACHE`, `LOCAL`, `STALE_CACHE` | — |
| usable_records | True | integer {"minimum":0.0} | — |
| rejected_records | True | integer {"minimum":0.0} | — |
| duplicate_records | True | integer {"minimum":0.0} | — |

### Schema: CatalogStatusResponse



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| status | True | `NOT_LOADED`, `LOADED` | — |
| catalog | True | CatalogMetadata \| null | — |
| warnings | True | array<string> | — |

### Schema: CleanupCandidate



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| id | True | string | — |
| name | True | string | — |
| classification | True | `PAYLOAD`, `ROCKET_BODY`, `DEBRIS`, `UNKNOWN` | — |
| eligible | True | boolean | — |
| eligibility_reason | True | string \| null | — |
| element_epoch | True | string (date-time) | — |
| inclination_deg | True | number | — |
| orbit_metadata | True | object | — |
| screening_exposure | True | object | — |
| persistence | True | PersistenceEvidence \| null | — |
| physical_metadata | True | object | — |
| missing_data | True | array<string> | — |
| provenance | True | object | — |
| warnings | True | array<string> | — |

### Schema: CleanupConstraints



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| max_targets | False | integer {"minimum":0.0,"maximum":1000.0} | 3 |
| max_candidates | False | integer {"minimum":1.0,"maximum":1000.0} | 200 |
| excluded_ids | False | array<string> {"maxItems":1000} | [] |
| effort_costs | False | map<string,number> \| null | — |
| effort_budget | False | number {"minimum":0.0,"maximum":1000000000000.0} \| null | — |
| solver_timeout_seconds | False | number {"exclusiveMinimum":0.0,"maximum":30.0} | 10 |

### Schema: CleanupPortfolio



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| status | True | `OPTIMAL_WITHIN_CANDIDATE_POOL`, `PARTIAL`, `UNAVAILABLE` | — |
| selected_objects | True | array<CleanupCandidate> | — |
| priority_ranking | True | array<PriorityScore> | — |
| candidates | True | array<CleanupCandidate> | — |
| total_priority_proxy | True | number | — |
| resource_model | True | `TARGET_COUNT`, `USER_SUPPLIED_ABSTRACT_EFFORT` | — |
| targets_remaining | True | integer | — |
| total_abstract_resource_expenditure | True | number | — |
| budget_remaining | True | number \| null | — |
| excluded_objects | True | map<string,array<string>> | — |
| selection_reasons | False | map<string,string> | — |
| unique_screening_encounters_represented | True | integer | — |
| shared_screening_encounter_ids | True | array<string> | — |
| policy | True | PriorityPolicy | — |
| constraints | True | CleanupConstraints | — |
| coverage | True | object | — |
| model_assumptions | True | array<string> | — |
| warnings | True | array<string> | — |

### Schema: CleanupRequest



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| constraints | False | CleanupConstraints | — |
| policy | False | PriorityPolicy | — |
| candidate_ids | False | array<string> {"maxItems":1000} \| null | — |

### Schema: ClosestApproach



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| tca | True | string (date-time) | — |
| miss_distance_m | True | number {"minimum":0.0} | — |
| relative_speed_m_s | True | number {"minimum":0.0} | — |
| relative_position_m | True | tuple[number, number, number] {"minItems":3,"maxItems":3} | — |
| relative_velocity_m_s | True | tuple[number, number, number] {"minItems":3,"maxItems":3} | — |
| frame | True | `TEME`, `GCRS` | — |
| searched_start | True | string (date-time) | — |
| searched_end | True | string (date-time) | — |
| sampled_minimum_m | True | number {"minimum":0.0} | — |
| status | True | `COMPLETE`, `SEARCH_BOUNDARY` | — |

### Schema: ConjunctionClassification



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |

`NEW_CLOSE_APPROACH`, `WORSENED_CLOSE_APPROACH`, `IMPROVED_CLOSE_APPROACH`, `UNCHANGED`

### Schema: CrossCovariance



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| matrix_m2 | True | tuple[tuple[number, number, number] {"minItems":3,"maxItems":3}, tuple[number, number, number] {"minItems":3,"maxItems":3}, tuple[number, number, number] {"minItems":3,"maxItems":3}] {"minItems":3,"maxItems":3} | — |
| frame | True | `TEME`, `GCRS`, `EME2000`, `GCRF` | — |
| epoch | True | string (date-time) | — |
| units | False | `m2` | "m2" |

### Schema: DecayPropagation



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| status | True | string | — |
| start_time | True | string (date-time) | — |
| requested_end_time | True | string (date-time) | — |
| integrated_end_time | True | string (date-time) | — |
| horizon_days | True | number | — |
| samples | True | array<DecaySample> | — |
| elapsed_seconds | True | number | — |
| derivative_evaluations | True | integer | — |
| solver_settings | True | SolverSettings | — |
| environment | True | object | — |
| aerodynamic_properties | True | object | — |
| boundary_altitude_m | False | number | 120000 |
| boundary_crossing_time | False | string (date-time) \| null | — |
| model | False | string | "DOP853 / GCRS / WGS84 central gravity + J2 + co-rotating drag" |
| assumptions | True | array<string> | — |
| warnings | True | array<string> | — |

### Schema: DecaySample



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| state | True | StateVector | — |
| geodetic | True | GeodeticPosition | — |
| central_specific_energy_j_kg | True | number | — |
| total_specific_energy_j_kg | True | number | — |
| semimajor_axis_m | True | number | — |
| eccentricity | True | number {"minimum":0.0} | — |
| perigee_altitude_m | True | number | — |
| apogee_altitude_m | True | number | — |
| density_kg_m3 | True | number {"minimum":0.0} | — |
| model_status | False | string | "MODEL_CALCULATED" |

### Schema: DensityRequest



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| timestamp | True | string (date-time) | — |
| latitude_deg | True | number {"minimum":-90.0,"maximum":90.0} | — |
| longitude_deg | True | number {"minimum":-180.0,"maximum":180.0} | — |
| altitude_m | True | number {"minimum":0.0,"maximum":1000000.0} | — |
| space_weather | False | WeatherForcing \| null | — |

### Schema: DensityResult



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| density_kg_m3 | True | number {"exclusiveMinimum":0.0} | — |
| position | True | GeodeticPosition | — |
| model | False | `NRLMSIS 2.1` | "NRLMSIS 2.1" |
| implementation | False | `pymsis 0.12.0` | "pymsis 0.12.0" |
| space_weather | True | WeatherForcing | — |
| assumptions | True | array<string> | — |
| warnings | True | array<string> | — |

### Schema: DirectProbabilityRequest



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| kind | True | `SUPPLIED`, `ASSUMED` | — |
| tca | True | string (date-time) | — |
| frame | True | `TEME`, `GCRS`, `EME2000`, `GCRF` | — |
| relative_position_m | True | tuple[number, number, number] {"minItems":3,"maxItems":3} | — |
| relative_velocity_m_s | True | tuple[number, number, number] {"minItems":3,"maxItems":3} | — |
| covariance_primary_m2 | True | tuple[tuple[number, number, number] {"minItems":3,"maxItems":3}, tuple[number, number, number] {"minItems":3,"maxItems":3}, tuple[number, number, number] {"minItems":3,"maxItems":3}] {"minItems":3,"maxItems":3} | — |
| covariance_secondary_m2 | True | tuple[tuple[number, number, number] {"minItems":3,"maxItems":3}, tuple[number, number, number] {"minItems":3,"maxItems":3}, tuple[number, number, number] {"minItems":3,"maxItems":3}] {"minItems":3,"maxItems":3} | — |
| combined_hard_body_radius_m | True | number {"exclusiveMinimum":0.0} | — |
| cross_covariance_m2 | False | tuple[tuple[number, number, number] {"minItems":3,"maxItems":3}, tuple[number, number, number] {"minItems":3,"maxItems":3}, tuple[number, number, number] {"minItems":3,"maxItems":3}] {"minItems":3,"maxItems":3} \| null | — |
| correlation | False | `UNSPECIFIED`, `INDEPENDENT`, `CORRELATED` | "UNSPECIFIED" |
| relative_tolerance | False | number {"minimum":1e-12,"maximum":0.0001} | 1e-09 |
| model_applicable | False | boolean | true |

### Schema: EncounterListResponse



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| items | True | array<ScreenedEncounter> | — |
| sort | True | string | — |
| dataset_timestamp | True | string (date-time) | — |
| data_status | True | `VALID`, `STALE_CACHE` | — |
| source_url | True | string | — |
| content_sha256 | True | string | — |

### Schema: EncounterTrajectories



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| encounter_id | True | string | — |
| participant_ids | True | tuple[string, string] {"minItems":2,"maxItems":2} | — |
| trajectories | True | array<ObjectTrajectory> | — |
| warnings | True | array<string> | — |

### Schema: FixedCovarianceScenario



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| kind | True | `SUPPLIED`, `ASSUMED` | — |
| primary | True | PositionCovariance | — |
| secondary | True | PositionCovariance | — |
| combined_hard_body_radius_m | True | number {"exclusiveMinimum":0.0} | — |
| primary_object_id | False | string {"pattern":"^\\d{1,9}$"} \| null | — |
| secondary_object_id | False | string {"pattern":"^\\d{1,9}$"} \| null | — |
| correlation | False | `UNSPECIFIED`, `INDEPENDENT`, `CORRELATED` | "UNSPECIFIED" |
| cross_covariance | False | CrossCovariance \| null | — |
| model_applicable | False | boolean | true |
| fixed_covariance | True | `True` | — |

### Schema: GPElements



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| object_id | True | string {"pattern":"^[0-9]{1,9}$"} | — |
| object_name | False | string | "" |
| international_designator | False | string | "" |
| epoch | True | string (date-time) | — |
| mean_motion_rev_day | True | number {"exclusiveMinimum":0.0,"maximum":20.0} | — |
| eccentricity | True | number {"minimum":0.0} | — |
| inclination_deg | True | number {"minimum":0.0,"maximum":180.0} | — |
| raan_deg | True | number {"minimum":0.0} | — |
| argument_of_pericenter_deg | True | number {"minimum":0.0} | — |
| mean_anomaly_deg | True | number {"minimum":0.0} | — |
| bstar | True | number | — |
| mean_motion_dot | True | number | — |
| mean_motion_ddot | True | number | — |
| ephemeris_type | True | `0` | — |
| classification | True | string {"maxLength":1} | — |
| element_set_number | True | integer {"minimum":0.0} | — |
| revolutions_at_epoch | True | integer {"minimum":0.0} | — |
| center | False | `EARTH` | "EARTH" |
| frame | False | `TEME` | "TEME" |
| time_system | False | `UTC` | "UTC" |
| mean_element_theory | False | `SGP4` | "SGP4" |

### Schema: GeodeticPosition



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| latitude_deg | True | number {"minimum":-90.0,"maximum":90.0} | — |
| longitude_deg | True | number {"minimum":-180.0,"maximum":180.0} | — |
| altitude_m | True | number | — |
| ellipsoid | False | `WGS84` | "WGS84" |

### Schema: HealthResponse



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| status | True | `ok` | — |
| service | True | `Kessler` | — |
| version | True | `0.1.0` | — |

### Schema: ManeuverConstraints



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| encounter_id | True | string | — |
| maneuvering_object_id | True | string {"pattern":"^[0-9]+$"} | — |
| max_delta_v_m_s | True | number {"minimum":0.0} | — |
| min_lead_time_minutes | True | number {"exclusiveMinimum":0.0} | — |
| max_lead_time_hours | True | number {"exclusiveMinimum":0.0,"maximum":48.0} | — |
| target_miss_distance_km | True | number {"exclusiveMinimum":0.0} | — |
| objective | True | Objective | — |
| hypothetical_capability_assumed | True | `True` | — |
| initial_mass_kg | False | number {"exclusiveMinimum":0.0} \| null | — |
| available_propellant_mass_kg | False | number {"minimum":0.0} \| null | — |
| specific_impulse_s | False | number {"exclusiveMinimum":0.0} \| null | — |

### Schema: ManeuverOption



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| maneuver_time | True | string (date-time) | — |
| delta_v_m_s | True | number | — |
| delta_v_rtn_m_s | True | tuple[number, number, number] {"minItems":3,"maxItems":3} | — |
| new_miss_distance_m | True | number | — |
| change_in_miss_distance_m | True | number | — |
| meets_target | True | boolean | — |
| is_clearance_improvement | True | boolean | — |
| calculated_tca | True | string (date-time) | — |
| matched_baseline_miss_distance_m | True | number | — |

### Schema: ManeuverProbabilityComparison



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| probability_status | True | `SCENARIO_WITH_ASSUMED_COVARIANCE`, `UNSUPPORTED_MODEL` | — |
| label | False | string | "ILLUSTRATIVE \u2014 USER-SUPPLIED UNCERTAINTY ASSUMPTIONS." |
| covariance_treatment | False | `FIXED_INERTIAL_GCRS_AT_ORIGINAL_TCA` | "FIXED_INERTIAL_GCRS_AT_ORIGINAL_TCA" |
| original_tca | True | string (date-time) | — |
| published_tca | True | string (date-time) | — |
| covariance_epoch | True | string (date-time) | — |
| baseline_tca | True | string (date-time) | — |
| modified_tca | True | string (date-time) | — |
| baseline_tca_offset_seconds | True | number | — |
| modified_tca_offset_seconds | True | number | — |
| baseline_pc | False | number \| null | — |
| modified_scenario_pc | False | number \| null | — |
| delta_pc | False | number \| null | — |
| baseline_calculation | False | ProbabilityResult \| null | — |
| modified_calculation | False | ProbabilityResult \| null | — |
| assumptions | True | array<string> | — |
| warnings | True | array<string> | — |

### Schema: ManeuverSimulation



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| encounter_id | True | string | — |
| maneuvering_object_id | True | string | — |
| maneuver_time | True | string (date-time) | — |
| delta_v_rtn_m_s | True | tuple[number, number, number] {"minItems":3,"maxItems":3} | — |
| delta_v_gcrs_m_s | True | tuple[number, number, number] {"minItems":3,"maxItems":3} | — |
| delta_v_m_s | True | number {"minimum":0.0} | — |
| state_before_maneuver | True | StateVector | — |
| state_after_maneuver | True | StateVector | — |
| matched_baseline | True | ClosestApproach | — |
| modified | True | ClosestApproach | — |
| change_in_miss_distance_m | True | number | — |
| change_in_tca_seconds | True | number | — |
| baseline_trajectory | True | array<StateVector> | — |
| modified_trajectory | True | array<StateVector> | — |
| sgp4_reference | True | BaselineAnalysis | — |
| model | False | `Matched central gravity + J2 / GCRS / WGS84` | "Matched central gravity + J2 / GCRS / WGS84" |
| model_assumptions | True | array<string> | — |
| warnings | True | array<string> | — |

### Schema: ManeuverTrajectories



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| encounter_id | True | string | — |
| participant_ids | True | tuple[string, string] {"minItems":2,"maxItems":2} | — |
| numerical_reference_epoch | True | string (date-time) | — |
| baseline | True | ObjectTrajectory | — |
| modified | True | ObjectTrajectory | — |
| counterpart | True | ObjectTrajectory | — |
| simulation | True | ProbabilityManeuverSimulation \| ManeuverSimulation | — |
| warnings | True | array<string> | — |

### Schema: ManeuverTrajectoryRequest



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| maneuvering_object_id | True | string {"pattern":"^[0-9]+$"} | — |
| maneuver_time | True | string (date-time) | — |
| delta_v_rtn_m_s | True | tuple[number, number, number] {"minItems":3,"maxItems":3} | — |
| hypothetical_capability_assumed | True | `True` | — |
| probability_scenario | False | FixedCovarianceScenario \| null | — |
| sample_count | False | integer {"minimum":2.0,"maximum":1001.0} | 121 |
| numerical_reference_epoch | False | string (date-time) \| null | — |

### Schema: ObjectAerodynamicProperties



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| input_category | True | `USER_SUPPLIED`, `HYPOTHETICAL_ASSUMPTION` | — |
| mass_kg | False | number {"exclusiveMinimum":0.0} \| null | — |
| area_m2 | False | number {"minimum":0.0} \| null | — |
| drag_coefficient | False | number {"exclusiveMinimum":0.0,"maximum":5.0} \| null | — |
| cd_area_over_mass_m2_kg | False | number {"minimum":0.0,"maximum":100.0} \| null | — |

### Schema: ObjectInfo



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| object | True | ObjectSummary | — |
| orbit | True | OrbitalRecord | — |
| metadata | True | ObjectMetadata \| null | — |
| warnings | True | array<string> | — |

### Schema: ObjectMetadata



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| id | True | string | — |
| name | True | string | — |
| classification | True | `PAYLOAD`, `ROCKET_BODY`, `DEBRIS`, `UNKNOWN` | — |
| source_object_type | True | string | — |
| operational_status_code | True | string \| null | — |
| decay_date | True | string \| null | — |
| orbit_center | True | string \| null | — |
| orbit_type | True | string \| null | — |
| radar_cross_section_m2 | False | number {"minimum":0.0} \| null | — |
| apogee_km | False | number \| null | — |
| perigee_km | False | number \| null | — |
| mass_kg | False | number \| null | — |
| dimensions_m | False | array<number> \| null | — |
| aerodynamic_area_m2 | False | number \| null | — |
| provenance | True | object | — |

### Schema: ObjectPosition



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| epoch | True | string (date-time) | — |
| position_km | True | tuple[number, number, number] {"minItems":3,"maxItems":3} \| null | — |
| propagation_status | True | `OK`, `SGP4_ERROR`, `UNSUPPORTED_EPOCH`, `NOT_IN_CATALOG` | — |
| error | False | string \| null | — |
| id | True | string | — |
| name | True | string \| null | — |
| classification | True | `PAYLOAD`, `ROCKET_BODY`, `DEBRIS`, `UNKNOWN` | — |
| frame | False | `ITRS` | "ITRS" |
| position_units | False | `km` | "km" |

### Schema: ObjectSummary



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| id | True | string | — |
| name | True | string | — |
| classification | True | `PAYLOAD`, `ROCKET_BODY`, `DEBRIS`, `UNKNOWN` | — |
| element_epoch | True | string (date-time) | — |
| inclination_deg | True | number | — |
| operational_status_code | True | string \| null | — |
| cleanup_eligible | True | boolean | — |
| apogee_km | True | number \| null | — |
| perigee_km | True | number \| null | — |

### Schema: ObjectTrajectory



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| id | True | string | — |
| name | True | string | — |
| frame | False | `ITRS` | "ITRS" |
| position_units | False | `km` | "km" |
| samples | True | array<PositionSample> | — |
| provenance | True | object | — |
| model | True | string | — |
| warnings | True | array<string> | — |

### Schema: Objective



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |

`MINIMUM_DELTA_V`, `MAXIMUM_CLEARANCE`

### Schema: OptimizationResult



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| encounter_id | True | string | — |
| maneuvering_object_id | True | string | — |
| status | True | `COMPLETE`, `PARTIAL`, `NO_FEASIBLE_SOLUTION`, `INCOMPLETE`, `UNAVAILABLE`, `NO_ACCEPTABLE_SCREENED_SOLUTION` | — |
| result_label | False | `Best evaluated maneuvers; no global optimality guarantee` | "Best evaluated maneuvers; no global optimality guarantee" |
| objective | True | Objective | — |
| constraints | True | ManeuverConstraints | — |
| search_settings | True | SearchSettings | — |
| baseline | True | ClosestApproach | — |
| sgp4_reference | True | BaselineAnalysis | — |
| numerical_reference_epoch | True | string (date-time) | — |
| solutions | True | array<ManeuverOption> | — |
| candidates_evaluated | True | integer | — |
| feasible_candidates | True | integer | — |
| target_feasible_candidates | True | integer | — |
| numerical_failures | True | integer | — |
| elapsed_seconds | True | number | — |
| fuel_budget_delta_v_m_s | True | number \| null | — |
| model_assumptions | True | array<string> | — |
| warnings | True | array<string> | — |
| secondary_screening | False | OptimizationScreeningSummary \| null | — |

### Schema: OptimizationScreeningSummary



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| status | True | `COMPLETE`, `INCOMPLETE`, `NO_ACCEPTABLE_SCREENED_SOLUTION`, `UNAVAILABLE` | — |
| policy | True | ScreeningPolicy | — |
| max_finalists | True | integer | — |
| candidates_screened | True | integer | — |
| selected_primary_rank | True | integer \| null | — |
| candidate_results | True | array<CandidateScreeningAssessment> | — |
| elapsed_seconds | True | number | — |
| warnings | True | array<string> | — |

### Schema: OptimizeRequest



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| encounter_id | True | string | — |
| maneuvering_object_id | True | string {"pattern":"^[0-9]+$"} | — |
| max_delta_v_m_s | True | number {"minimum":0.0} | — |
| min_lead_time_minutes | True | number {"exclusiveMinimum":0.0} | — |
| max_lead_time_hours | True | number {"exclusiveMinimum":0.0,"maximum":48.0} | — |
| target_miss_distance_km | True | number {"exclusiveMinimum":0.0} | — |
| objective | True | Objective | — |
| hypothetical_capability_assumed | True | `True` | — |
| initial_mass_kg | False | number {"exclusiveMinimum":0.0} \| null | — |
| available_propellant_mass_kg | False | number {"minimum":0.0} \| null | — |
| specific_impulse_s | False | number {"exclusiveMinimum":0.0} \| null | — |
| search | False | SearchSettings | — |
| secondary_screening | False | SecondaryOptimizationSettings \| null | — |

### Schema: OrbitalRecord



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| elements | True | GPElements | — |
| source | False | `CelesTrak GP`, `Local OMM` | "CelesTrak GP" |
| source_url | True | string | — |
| fetched_at | True | string (date-time) | — |
| content_sha256 | True | string | — |
| data_status | False | `VALID`, `STALE_CACHE` | "VALID" |
| warnings | False | array<string> | — |

### Schema: PersistenceAnalysis



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| object_id | True | string | — |
| object_name | True | string | — |
| gp_epoch | True | string (date-time) | — |
| initial_state | True | StateVector | — |
| initial_orbit | True | object | — |
| assumed_physical_parameters | True | ObjectAerodynamicProperties \| null | — |
| prediction_status | True | string | — |
| prediction_horizon_days | True | number | — |
| scenario_analysis | True | ScenarioAnalysis \| null | — |
| persistence_metrics | True | array<object> | — |
| provenance | True | object | — |
| assumptions | True | array<string> | — |
| warnings | True | array<string> | — |

### Schema: PersistenceEvidence



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| object_id | True | string | — |
| initial_epoch | True | string (date-time) | — |
| modeled_duration_days | True | number {"minimum":0.0,"maximum":90.0} | — |
| horizon_days | True | number {"exclusiveMinimum":0.0,"maximum":90.0} | — |
| boundary_status | True | `BOUNDARY_REACHED`, `NOT_REACHED_WITHIN_HORIZON` | — |
| censored_at_horizon | True | boolean | — |
| provenance | True | object | — |
| warnings | True | array<string> | — |

### Schema: PersistenceRequest



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| horizon_days | False | number {"exclusiveMinimum":0.0,"maximum":90.0} | 1 |
| boundary_altitude_m | False | number {"minimum":80000.0,"maximum":500000.0} | 120000 |
| scenario_mode | False | `NOMINAL`, `COMPARE` | "NOMINAL" |
| weather_mode | False | `SOURCE_ONLY`, `HYPOTHETICAL_CONSTANT`, `SOURCE_WITH_EXPLICIT_FALLBACK` | "SOURCE_ONLY" |
| nominal_f107_sfu | False | number {"exclusiveMinimum":0.0,"maximum":500.0} \| null | — |
| nominal_ap | False | number {"minimum":0.0,"maximum":400.0} \| null | — |
| min_cd_area_over_mass_m2_kg | False | number {"minimum":0.0,"maximum":100.0} \| null | — |
| max_cd_area_over_mass_m2_kg | False | number {"minimum":0.0,"maximum":100.0} \| null | — |
| solver | False | SolverSettings | — |
| aerodynamic_properties | False | ObjectAerodynamicProperties \| null | — |
| start_time | False | string (date-time) \| null | — |
| visualization | False | boolean | false |

### Schema: PersistenceSettings



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| horizon_days | False | number {"exclusiveMinimum":0.0,"maximum":90.0} | 1 |
| boundary_altitude_m | False | number {"minimum":80000.0,"maximum":500000.0} | 120000 |
| scenario_mode | False | `NOMINAL`, `COMPARE` | "NOMINAL" |
| weather_mode | False | `SOURCE_ONLY`, `HYPOTHETICAL_CONSTANT`, `SOURCE_WITH_EXPLICIT_FALLBACK` | "SOURCE_ONLY" |
| nominal_f107_sfu | False | number {"exclusiveMinimum":0.0,"maximum":500.0} \| null | — |
| nominal_ap | False | number {"minimum":0.0,"maximum":400.0} \| null | — |
| min_cd_area_over_mass_m2_kg | False | number {"minimum":0.0,"maximum":100.0} \| null | — |
| max_cd_area_over_mass_m2_kg | False | number {"minimum":0.0,"maximum":100.0} \| null | — |
| solver | False | SolverSettings | — |

### Schema: PersistenceVisualization



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| object_id | True | string | — |
| prediction_status | True | string | — |
| analysis | True | object | — |
| trajectories | True | map<string,ObjectTrajectory> | — |
| warnings | True | array<string> | — |

### Schema: PositionBatch



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| items | True | array<ObjectPosition> | — |
| epoch | True | string (date-time) | — |
| frame | False | `ITRS` | "ITRS" |
| position_units | False | `km` | "km" |
| catalog | True | CatalogMetadata | — |
| metadata_source | True | object \| null | — |
| warnings | True | array<string> | — |

### Schema: PositionCovariance



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| matrix_m2 | True | tuple[tuple[number, number, number] {"minItems":3,"maxItems":3}, tuple[number, number, number] {"minItems":3,"maxItems":3}, tuple[number, number, number] {"minItems":3,"maxItems":3}] {"minItems":3,"maxItems":3} | — |
| frame | True | `RTN`, `RIC`, `TEME`, `GCRS`, `EME2000`, `GCRF` | — |
| epoch | True | string (date-time) | — |
| units | False | `m2` | "m2" |

### Schema: PositionRequest



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| object_ids | True | array<string> {"minItems":1,"maxItems":2000} | — |
| epoch | False | string (date-time) \| null | — |

### Schema: PositionSample



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| epoch | True | string (date-time) | — |
| position_km | True | tuple[number, number, number] {"minItems":3,"maxItems":3} \| null | — |
| propagation_status | True | `OK`, `SGP4_ERROR`, `UNSUPPORTED_EPOCH`, `NOT_IN_CATALOG` | — |
| error | False | string \| null | — |

### Schema: PriorityPolicy



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| exposure_weight | False | number {"minimum":0.0,"maximum":100.0} | 1 |
| persistence_weight | False | number {"minimum":0.0,"maximum":100.0} | 0 |
| radar_cross_section_weight | False | number {"minimum":0.0,"maximum":100.0} | 0 |
| exposure_saturation_count | False | integer {"minimum":1.0,"maximum":100000.0} | 10 |
| persistence_saturation_days | False | number {"exclusiveMinimum":0.0,"maximum":90.0} | 30 |
| radar_cross_section_saturation_m2 | False | number {"exclusiveMinimum":0.0,"maximum":10000.0} | 10 |

### Schema: PriorityScore



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| id | True | string | — |
| score | True | number {"minimum":0.0,"maximum":1.0} \| null | — |
| score_interval | True | tuple[number, number] {"minItems":2,"maxItems":2} | — |
| status | True | `RANKABLE`, `INSUFFICIENT_EVIDENCE`, `INELIGIBLE` | — |
| components | True | object | — |
| reasons | True | array<string> | — |

### Schema: ProbabilityAnalysis



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| probability_status | True | `CALCULATED_FROM_SUPPLIED_COVARIANCE`, `SCENARIO_WITH_ASSUMED_COVARIANCE`, `UNAVAILABLE_NO_COVARIANCE`, `UNAVAILABLE_INVALID_COVARIANCE`, `UNSUPPORTED_MODEL` | — |
| source | False | `SOCRATES`, `USER_SUPPLIED_GEOMETRY` | "SOCRATES" |
| socrates_max_probability | False | number {"minimum":0.0,"maximum":1.0} \| null | — |
| calculated_pc | False | number {"minimum":0.0,"maximum":1.0} \| null | — |
| tca | False | string (date-time) \| null | — |
| frame | False | string \| null | — |
| label | False | string \| null | — |
| covariance_treatment | False | string | "NONE" |
| calculation | False | ProbabilityResult \| null | — |
| assumptions | False | array<string> | — |
| warnings | False | array<string> | — |

### Schema: ProbabilityBaselineAnalysis



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| encounter_id | True | string | — |
| source | False | `SOCRATES` | "SOCRATES" |
| published | True | PublishedPrediction | — |
| calculated | True | ClosestApproach | — |
| model | False | `SGP4 / TEME / WGS72` | "SGP4 / TEME / WGS72" |
| element_epochs | True | tuple[string (date-time), string (date-time)] {"minItems":2,"maxItems":2} | — |
| orbital_source_checksums | True | tuple[string, string] {"minItems":2,"maxItems":2} | — |
| source_model_disagreement | True | boolean | — |
| warnings | True | array<string> | — |
| probability_analysis | True | ProbabilityAnalysis | — |

### Schema: ProbabilityInputs



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| kind | True | `SUPPLIED`, `ASSUMED` | — |
| primary | True | PositionCovariance | — |
| secondary | True | PositionCovariance | — |
| combined_hard_body_radius_m | True | number {"exclusiveMinimum":0.0} | — |
| primary_object_id | False | string {"pattern":"^\\d{1,9}$"} \| null | — |
| secondary_object_id | False | string {"pattern":"^\\d{1,9}$"} \| null | — |
| correlation | False | `UNSPECIFIED`, `INDEPENDENT`, `CORRELATED` | "UNSPECIFIED" |
| cross_covariance | False | CrossCovariance \| null | — |
| model_applicable | False | boolean | true |

### Schema: ProbabilityManeuverSimulation



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| encounter_id | True | string | — |
| maneuvering_object_id | True | string | — |
| maneuver_time | True | string (date-time) | — |
| delta_v_rtn_m_s | True | tuple[number, number, number] {"minItems":3,"maxItems":3} | — |
| delta_v_gcrs_m_s | True | tuple[number, number, number] {"minItems":3,"maxItems":3} | — |
| delta_v_m_s | True | number {"minimum":0.0} | — |
| state_before_maneuver | True | StateVector | — |
| state_after_maneuver | True | StateVector | — |
| matched_baseline | True | ClosestApproach | — |
| modified | True | ClosestApproach | — |
| change_in_miss_distance_m | True | number | — |
| change_in_tca_seconds | True | number | — |
| baseline_trajectory | True | array<StateVector> | — |
| modified_trajectory | True | array<StateVector> | — |
| sgp4_reference | True | BaselineAnalysis | — |
| model | False | `Matched central gravity + J2 / GCRS / WGS84` | "Matched central gravity + J2 / GCRS / WGS84" |
| model_assumptions | True | array<string> | — |
| warnings | True | array<string> | — |
| probability_comparison | True | ManeuverProbabilityComparison | — |

### Schema: ProbabilityResult



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| status | True | `CALCULATED`, `UNSUPPORTED_MODEL`, `NUMERICAL_FAILURE` | — |
| calculated_pc | False | number {"minimum":0.0,"maximum":1.0} \| null | — |
| encounter_plane_miss_m | False | tuple[number, number] {"minItems":2,"maxItems":2} \| null | — |
| projected_covariance_m2 | False | tuple[tuple[number, number] {"minItems":2,"maxItems":2}, tuple[number, number] {"minItems":2,"maxItems":2}] {"minItems":2,"maxItems":2} \| null | — |
| combined_hard_body_radius_m | True | number | — |
| numerical_method | False | string | "2D Gaussian disk: eigenbasis, stable normal-CDF difference, adaptive QUADPACK" |
| numerical_status | True | `CONVERGED`, `UNDERFLOW`, `UNSUPPORTED`, `FAILED` | — |
| estimated_absolute_error | False | number \| null | — |
| requested_relative_tolerance | True | number | — |
| projected_condition_number | False | number \| null | — |
| integrand_evaluations | False | integer | 0 |
| assumptions | True | array<string> | — |
| warnings | True | array<string> | — |

### Schema: PublishedPrediction



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| tca | True | string (date-time) | — |
| miss_distance_m | True | number | — |
| relative_speed_m_s | True | number | — |
| max_probability_screening_metric | True | number \| null | — |

### Schema: ReferenceComparison



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| source | False | `NASA_CARA_HISTORICAL_REFERENCE` | "NASA_CARA_HISTORICAL_REFERENCE" |
| reference_only | False | `True` | true |
| reference_case | True | string | — |
| reference_url | False | string | "https://github.com/nasa/CARA_Analysis_Tools/tree/ce0f00722c56808755ee0adbe47a4e3d56439484/DataFiles/PcTestCaseCDMs" |
| source_sha256 | True | string | — |
| original_tca | True | string (date-time) | — |
| linear_closest_approach_tca | True | string (date-time) | — |
| linear_tca_offset_seconds | True | number | — |
| state_frame | True | string | — |
| covariance_frame | False | `INDIVIDUAL_OBJECT_RTN` | "INDIVIDUAL_OBJECT_RTN" |
| reference_model | False | `NASA_INDEPENDENT_2D_BENCHMARK` | "NASA_INDEPENDENT_2D_BENCHMARK" |
| published_reference_pc | True | number | — |
| cdm_rounded_reference_pc | True | number \| null | — |
| calculated_pc | True | number \| null | — |
| numerical_difference | True | number \| null | — |
| relative_difference | True | number \| null | — |
| calculation | True | ProbabilityResult | — |
| assumptions | True | array<string> | — |
| warnings | True | array<string> | — |

### Schema: ReferenceProbabilityRequest



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| reference_case | True | string | — |
| independent_benchmark | True | `True` | — |

### Schema: ScenarioAnalysis



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| settings | True | PersistenceSettings | — |
| scenarios | True | array<ScenarioResult> | — |
| status | True | `COMPLETE`, `PARTIAL`, `UNAVAILABLE` | — |
| scenario_envelope | True | object | — |
| assumptions | True | array<string> | — |
| warnings | True | array<string> | — |

### Schema: ScenarioResult



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| scenario | True | `LOW_DRAG`, `NOMINAL`, `HIGH_DRAG` | — |
| aerodynamic_properties | True | ObjectAerodynamicProperties | — |
| environment_assumptions | True | object | — |
| boundary | True | BoundaryAnalysis | — |
| total_specific_energy_change_j_kg | False | number \| null | — |
| semimajor_axis_change_m | False | number \| null | — |
| initial_period_mean_semimajor_axis_m | False | number \| null | — |
| final_period_mean_semimajor_axis_m | False | number \| null | — |
| warnings | False | array<string> | — |

### Schema: ScientificErrorResponse



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| status | True | `NOT_FOUND`, `UNAVAILABLE`, `UNSUPPORTED`, `BUSY` | — |
| detail | True | string | — |

### Schema: ScreenRequest



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| alert_distance_km | False | number {"exclusiveMinimum":0.0,"maximum":1000.0} | 5 |
| post_tca_horizon_hours | False | number {"exclusiveMinimum":0.0,"maximum":24.0} | 6 |
| coarse_step_seconds | False | number {"exclusiveMinimum":0.0,"maximum":120.0} | 30 |
| relative_acceleration_margin_m_s2 | False | number {"exclusiveMinimum":0.0,"maximum":1000.0} | 40 |
| batch_size | False | integer {"minimum":1.0,"maximum":1024.0} | 256 |
| max_objects | False | integer {"minimum":1.0,"maximum":100000.0} | 50000 |
| max_refinements | False | integer {"minimum":1.0,"maximum":10000.0} | 1000 |
| timeout_seconds | False | number {"exclusiveMinimum":0.0,"maximum":300.0} | 30 |
| max_epoch_distance_days | False | number {"exclusiveMinimum":0.0,"maximum":7.0} | 7 |
| classification_tolerance_m | False | number {"minimum":0.001,"maximum":100.0} | 1 |
| event_matching_tolerance_seconds | False | number {"minimum":1.0,"maximum":600.0} | 120 |
| catalog_selection | False | CatalogSelection | — |
| encounter_id | False | string \| null | — |
| maneuvering_object_id | True | string | — |
| maneuver_time | True | string (date-time) | — |
| delta_v_rtn_m_s | True | tuple[number, number, number] {"minItems":3,"maxItems":3} | — |
| hypothetical_capability_assumed | True | `True` | — |

### Schema: ScreenedEncounter



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| id | True | string | — |
| object_1_id | True | string {"pattern":"^[0-9]+$"} | — |
| object_1_name | True | string | — |
| object_2_id | True | string {"pattern":"^[0-9]+$"} | — |
| object_2_name | True | string | — |
| time_of_closest_approach | True | string (date-time) | — |
| source_miss_distance_m | True | number {"minimum":0.0} | — |
| source_relative_speed_m_s | True | number {"minimum":0.0} | — |
| socrates_max_probability | False | number {"minimum":0.0,"maximum":1.0} \| null | — |
| source_dse_1_days | False | number \| null | — |
| source_dse_2_days | False | number \| null | — |
| source_dilution_m | False | number {"minimum":0.0} \| null | — |
| source | False | `SOCRATES` | "SOCRATES" |
| dataset_timestamp | True | string (date-time) | — |
| data_status | False | `VALID`, `STALE_CACHE` | "VALID" |
| warnings | True | array<string> | — |

### Schema: ScreeningPolicy



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |

`REPORT_ONLY`, `REJECT_NEW_ALERTS`, `REJECT_ALL_ALERTS`

### Schema: ScreeningResult



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| encounter_id | True | string | — |
| maneuvering_object_id | True | string | — |
| alert_distance_km | False | number {"exclusiveMinimum":0.0,"maximum":1000.0} | 5 |
| screening_status | True | ScreeningStatus | — |
| screening_complete | True | boolean | — |
| catalog | True | CatalogMetadata | — |
| screening_window | True | ScreeningWindow | — |
| objects_screened | True | integer {"minimum":0.0} | — |
| candidate_objects_refined | True | integer {"minimum":0.0} | — |
| additional_close_approaches | True | integer {"minimum":0.0} | — |
| newly_introduced | True | integer {"minimum":0.0} | — |
| worsened | True | integer {"minimum":0.0} | — |
| improved | True | integer {"minimum":0.0} | — |
| closest_additional_encounter | True | SecondaryConjunction \| null | — |
| secondary_encounters | True | array<SecondaryConjunction> | — |
| skipped_objects | False | map<string,string> | — |
| elapsed_seconds | True | number {"minimum":0.0} | — |
| timings_seconds | False | map<string,number> | — |
| model_limitations | False | array<string> | — |
| warnings | False | array<string> | — |

### Schema: ScreeningStatus



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |

`SCREENED_WITHIN_COVERAGE`, `ALERTS_FOUND`, `INCOMPLETE`, `UNAVAILABLE`

### Schema: ScreeningWindow



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| start | True | string (date-time) | — |
| end | True | string (date-time) | — |

### Schema: SearchSettings



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| time_samples | False | integer {"minimum":1.0,"maximum":8.0} | 6 |
| magnitude_samples | False | integer {"minimum":1.0,"maximum":5.0} | 3 |
| max_evaluations | False | integer {"minimum":1.0,"maximum":500.0} | 150 |
| timeout_seconds | False | number {"exclusiveMinimum":0.0,"maximum":120.0} | 25 |
| refinement_evaluations | False | integer {"minimum":0.0,"maximum":60.0} | 20 |

### Schema: SecondaryConjunction



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| primary_object_id | True | string | — |
| secondary_object_id | True | string | — |
| secondary_object_name | True | string | — |
| is_original_counterpart | True | boolean | — |
| time_of_closest_approach | True | string (date-time) | — |
| baseline_time_of_closest_approach | True | string (date-time) \| null | — |
| baseline_miss_distance_m | True | number {"minimum":0.0} \| null | — |
| maneuvered_miss_distance_m | True | number {"minimum":0.0} | — |
| change_in_miss_distance_m | True | number \| null | — |
| change_in_tca_seconds | True | number \| null | — |
| relative_speed_m_s | True | number {"minimum":0.0} | — |
| classification | True | ConjunctionClassification | — |
| baseline_below_threshold | True | boolean \| null | — |
| maneuvered_below_threshold | True | boolean | — |
| screening_window | True | ScreeningWindow | — |
| frame | True | `TEME`, `GCRS` | — |
| source | True | map<string,string> | — |
| warnings | False | array<string> | — |

### Schema: SecondaryOptimizationSettings



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| alert_distance_km | False | number {"exclusiveMinimum":0.0,"maximum":1000.0} | 5 |
| post_tca_horizon_hours | False | number {"exclusiveMinimum":0.0,"maximum":24.0} | 6 |
| coarse_step_seconds | False | number {"exclusiveMinimum":0.0,"maximum":120.0} | 30 |
| relative_acceleration_margin_m_s2 | False | number {"exclusiveMinimum":0.0,"maximum":1000.0} | 40 |
| batch_size | False | integer {"minimum":1.0,"maximum":1024.0} | 256 |
| max_objects | False | integer {"minimum":1.0,"maximum":100000.0} | 50000 |
| max_refinements | False | integer {"minimum":1.0,"maximum":10000.0} | 1000 |
| timeout_seconds | False | number {"exclusiveMinimum":0.0,"maximum":300.0} | 30 |
| max_epoch_distance_days | False | number {"exclusiveMinimum":0.0,"maximum":7.0} | 7 |
| classification_tolerance_m | False | number {"minimum":0.001,"maximum":100.0} | 1 |
| event_matching_tolerance_seconds | False | number {"minimum":1.0,"maximum":600.0} | 120 |
| catalog_selection | False | CatalogSelection | — |
| policy | False | ScreeningPolicy | "REPORT_ONLY" |
| max_finalists | False | integer {"minimum":1.0,"maximum":10.0} | 3 |
| total_timeout_seconds | False | number {"exclusiveMinimum":0.0,"maximum":600.0} | 90 |

### Schema: SimulateRequest



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| maneuvering_object_id | True | string {"pattern":"^[0-9]+$"} | — |
| maneuver_time | True | string (date-time) | — |
| delta_v_rtn_m_s | True | tuple[number, number, number] {"minItems":3,"maxItems":3} | — |
| hypothetical_capability_assumed | True | `True` | — |
| probability_scenario | False | FixedCovarianceScenario \| null | — |

### Schema: SolverSettings



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| rtol | False | number {"minimum":1e-12,"maximum":1e-06} | 1e-09 |
| position_atol_m | False | number {"exclusiveMinimum":0.0,"maximum":0.1} | 0.0001 |
| velocity_atol_m_s | False | number {"exclusiveMinimum":0.0,"maximum":0.001} | 1e-07 |
| max_step_seconds | False | number {"exclusiveMinimum":0.0,"maximum":120.0} | 120 |
| sample_step_seconds | False | number {"minimum":10.0,"maximum":3600.0} | 600 |
| timeout_seconds | False | number {"exclusiveMinimum":0.0,"maximum":600.0} | 180 |

### Schema: SpaceWeatherStatus



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| status | True | string | — |
| coverage | False | object \| null | — |
| warnings | False | array<string> | — |

### Schema: StateVector



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| timestamp | True | string (date-time) | — |
| position_m | True | tuple[number, number, number] {"minItems":3,"maxItems":3} | — |
| velocity_m_s | True | tuple[number, number, number] {"minItems":3,"maxItems":3} | — |
| frame | True | `TEME`, `GCRS` | — |
| position_units | False | `m` | "m" |
| velocity_units | False | `m/s` | "m/s" |
| propagation_status | False | `OK` | "OK" |

### Schema: StatusResponse



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| service | False | `Kessler` | "Kessler" |
| version | False | `0.1.0` | "0.1.0" |
| source_status | True | `NOT_LOADED`, `VALID`, `STALE_CACHE` | — |
| encounters_loaded | True | integer | — |
| cache_directory | True | string | — |
| warnings | True | array<string> | — |

### Schema: ValidationFailure



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| detail | True | array<ValidationIssue> | — |

### Schema: ValidationIssue



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| loc | True | array<string \| integer> | — |
| msg | True | string | — |
| type | True | string | — |
| input | False | any JSON | — |
| ctx | False | object \| null | — |

### Schema: WeatherForcing



| Field | Required | Type / constraints | Default |
| --- | --- | --- | --- |
| date | True | string (date) | — |
| f107_previous_day_sfu | True | number {"exclusiveMinimum":0.0,"maximum":500.0} | — |
| f107_center81_sfu | True | number {"exclusiveMinimum":0.0,"maximum":500.0} | — |
| ap_history | True | tuple[number, number, number, number, number, number, number] {"minItems":7,"maxItems":7} | — |
| geomagnetic_mode | False | `-1`, `1` | -1 |
| input_category | True | `SOURCE_OBSERVATION`, `SOURCE_FORECAST`, `SOURCE_INTERPOLATED`, `USER_SUPPLIED_ASSUMPTION` | — |
| provenance | True | object | — |
| warnings | False | array<string> | — |
