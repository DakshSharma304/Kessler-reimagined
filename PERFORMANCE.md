# Phase 5 public API performance and live integration

Verified on October 11, 2026, 06:38 EDT (10:38 UTC), Python3.12, four-core
CPU quota, one backend process, BLAS/OMP threads1. Benchmark ran before the
parallel regression suite, without concurrent synthetic load. Times include
HTTP transport, actual calculation, validation and JSON serialization. Three
warm trials per operation after a real six-workflow smoke; raw timings,
requests, provenance and NASA comparisons are in `performance.json`.
These are workload-specific measurements, not latency guarantees.

Reproduce from backend with the API running separately:

```sh
../.venv/bin/python scripts/benchmark_frontend.py --base-url http://127.0.0.1:8000
```

| Operation / actual workload | Warm median seconds | Response bytes |
| --- | ---: | ---: |
| Catalog ID substring search, limit1 | 0.010600 | 4,068 |
| Bulk positions, 1,200 objects, one epoch | 0.064365 | 305,305 |
| Single-object orbit, 21 samples | 0.006758 | 4,096 |
| Encounter analysis plus Pc availability | 0.007710 | 1,780 |
| Maneuver optimization, 13 evaluated proposals | 0.245380 | 5,043–5,044 |
| Secondary screen, max128 objects, 5s compute cap | 0.090469 | 782,853–782,854 |
| NASA Terra historical Pc comparison | 0.018017 | 3,601 |
| Actual MSIS persistence, 3 scenarios, .001day | 0.150503 | 26,502 |
| Cleanup portfolio, explicit5-object pool, max2targets | 1.005915 | 21,802 |

The short persistence horizon is86.4seconds, not a benchmark of months-long
propagation or a predicted lifetime. Physical/weather inputs are explicit
hypothetical assumptions; MSIS/force-model calculations are actual. Previous
long-horizon scientific tests remain mandatory in the regression suite.
Optimization uses the existing clearance objective, no Pc-based replacement.

## Actual integration evidence

- All six HTTP workflows PASSED; every response validated against its actual
  FastAPI response model. API/source failures produce a nonzero benchmark exit.
- Public GP scope19,505 records; all five configured CelesTrak groups refreshed
  over HTTP at2026-10-11T10:38:09.004652Z. Snapshot SHA-256
  `ea0e8eec4e741293418de97804383d6593db946d4c797bd82baf881a03366dec`.
  Coverage remains PARTIAL, with207 old element epochs explicitly warned.
- 1,200 successful finite actual SGP4-to-ITRS positions, kilometers/UTC.
  Metadata/search/select/orbit and participant/modified paths also work.
- Actual SOCRATES encounter `socrates-599855ce2ca729ae50cb34e9`, dataset
  timestamp2026-10-10T15:48:20Z, nominal analysis, optimization, two secondary
  alternatives and JSON responses. Both screens are INCOMPLETE: measured
  bounds/public coverage never imply absent secondary collisions. Original
  source metric retained; live Pc UNAVAILABLE_NO_COVARIANCE. Assumed and
  fixed-covariance maneuver scenarios explicitly ILLUSTRATIVE.
- Actual NASA historical references independently integrated through API:

| NASA CDM fixture stem | Calculated Pc | Relative difference |
| --- | ---: | ---: |
| 000020580_conj_000022015_20210315_212955_20210313_065123 | 0.000611479323158796 | +1.242e-10 |
| 000025994_conj_000026980_20220928_223445_20220924_220647 | 0.00010824948102745792 | +7.608e-13 |
| 000025994_conj_000037558_20210324_151047_20210323_154356 | 0.021173811560374473 | +2.936e-13 |
| 000028485_conj_000044777_20220407_231108_20220406_140506 | 0.00232368496509251 | −8.736e-12 |

All meet the unchanged relative tolerance2e-9; reference answers remain only
in reference data/test assertions, never in the calculation engine.

- Actual CelesTrak space weather loaded from its integrity-checked cache,
  timestamp2026-10-11T06:57:19.081233Z; coverage includes observed and forecast
  categories. Actual-source MSIS density also calculated without hypothetical
  forcing, retaining forecast/centered-average limitations. Source/forecast
  metadata are in performance.json, not a claim of wholly observed inputs.
- Cleanup selected debris29734/29737 in an explicitly bounded five-object
  pool. This is a modeled proxy ranking, not a mission plan; mass unknown.

## Bottleneck investigation and safe caching

Previously the second public screen spent3.735s reparsing already loaded
catalog files. Default matching scopes now reuse the five-minute public
snapshot; local/custom scopes are not substituted. Targeted tests verify
expiry refresh, exact scope/fingerprint, local isolation and catalog status.
Existing propagation-cache entries also speed repeated matching computations.
The final first screen took3.701s (not warm); second0.077s. The warm median
above benefits from both caches and is not a promise for new geometries.
All requested geometries still undergo the verified screening calculation.

The legacy complete skipped-object list accounts for the roughly0.8MB screen
payload; this was measured and its existing contract retained. Workload caps
and response metadata disclose scope. Trajectory/persistence visualization
payloads stay bounded; atmospheric calculations never run on ordinary browsing.
First source downloads/GP parsing/Astropy initialization can take seconds or
tens of seconds. Long optimization/screening/persistence requests are synchronous;
show waiting and permit adequate timeouts. The application no longer rejects
calculations at a fixed concurrent slot count; too many simultaneous requests
can exhaust local CPU/RAM or hit hosting limits. No job infrastructure was added.
