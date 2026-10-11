"""Benchmark the public HTTP workflows; never substitute scientific results.

From backend: ../.venv/bin/python scripts/benchmark_frontend.py --base-url URL
Requires the same real sources as app.frontend_smoke. Outputs dated measurements,
not latency promises; warm trials include JSON transport and serialization.
"""
import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import statistics
import sys
import time

import httpx

# Allow direct script execution from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.routing import APIRoute
from pydantic import TypeAdapter
from app.frontend_smoke import run_smoke, require
from app.main import app
from app.probability.cdm import reference_cases


def validate(entry):
    if entry['path'] == '/openapi.json':
        require(entry['response'] == app.openapi(), 'Served OpenAPI differs from actual app')
        return
    routes = [route for route in app.routes if isinstance(route, APIRoute)
              and entry['method'] in route.methods and route.path_regex.fullmatch(entry['path'])]
    require(len(routes) == 1, 'Unknown public response model')
    TypeAdapter(routes[0].response_model).validate_python(entry['response'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--report', type=Path, default=Path('../performance.json'))
    parser.add_argument('--transcript', type=Path)
    args = parser.parse_args()
    with httpx.Client(base_url=args.base_url, timeout=240, trust_env=False) as client:
        smoke = run_smoke(client, progress=lambda line: print(line, flush=True))
        for entry in smoke['entries']:
            validate(entry)
        labels = ['A.search', 'A.bulk_benchmark', 'A.orbit', 'B.analyze', 'C.optimize',
                  'C.screen.2', 'D.reference', 'E.persistence', 'F.cleanup']
        measurements = []
        for label in labels:
            entry = next(entry for entry in smoke['entries'] if entry['label'] == label)
            seconds = []
            sizes = []
            for _ in range(3):
                tick = time.perf_counter()
                response = client.request(entry['method'], entry['path'], params=entry['params'], json=entry['request'])
                elapsed = time.perf_counter() - tick
                require(response.status_code == 200, f'{label}: HTTP{response.status_code}: {response.text[:1500]}')
                validate(entry | {'response': response.json()})
                seconds.append(elapsed)
                sizes.append(len(response.content))
            measurements.append({'label': label, 'warm_trial_seconds': seconds,
                                 'median_seconds': statistics.median(seconds), 'payload_bytes': sizes,
                                 'initial_smoke_seconds': entry['elapsed_seconds'],
                                 'params': entry['params'], 'request': entry['request']})
            print(f'{label}: warm median {statistics.median(seconds):.6f}s', flush=True)
        nasa = []
        for case in reference_cases():
            response = client.post('/api/probability/calculate', json={'reference_case': case, 'independent_benchmark': True})
            require(response.status_code == 200, response.text[:1500])
            comparison = response.json()
            require(comparison['relative_difference'] is not None and abs(comparison['relative_difference']) <= 2e-9,
                    f'NASA validation failed: {comparison}')
            nasa.append(comparison)
        weather = client.get('/api/space-weather/status', params={'load': 'true'})
        require(weather.status_code == 200, weather.text[:1500])
        weather_data = weather.json()
        require(weather_data['coverage'] is not None, 'Actual weather source not loaded')
        density = client.post('/api/atmosphere/density', json={'timestamp': datetime.now(UTC).isoformat(),
                              'latitude_deg': 0, 'longitude_deg': 0, 'altitude_m': 400000})
        require(density.status_code == 200 and density.json()['density_kg_m3'] > 0, 'Actual-source MSIS density failed')
    selected = {key: value for key, value in smoke.items() if key != 'entries'}
    report = {'status': 'PASSED', 'recorded_at': datetime.now(UTC).isoformat(),
              'method': 'HTTP end-to-end; 3 warm trials after all-six-workflow smoke; no concurrent benchmark load',
              'smoke': selected, 'measurements': measurements, 'nasa_comparisons': nasa,
              'catalog': next(entry['response']['catalog'] for entry in smoke['entries'] if entry['label'] == 'A.bulk_benchmark'),
              'actual_space_weather': weather_data, 'actual_source_density': density.json()}
    args.report.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    if args.transcript:
        args.transcript.write_text(json.dumps(smoke, indent=2, allow_nan=False) + '\n')
    print('FINAL PUBLIC API INTEGRATION AND BENCHMARK: PASSED', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
