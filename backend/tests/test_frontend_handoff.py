"""Public contract/exports validate against the real route models, including errors."""
import json
from pathlib import Path
import re
from fastapi.routing import APIRoute
from pydantic import TypeAdapter
from app.export_frontend import export
from app.frontend_smoke import run_smoke
from app.main import app
from app.api.error_schemas import ScientificErrorResponse,ValidationFailure
from test_visualization import visual_api

ROOT=Path(__file__).resolve().parents[2]

def test_smoke_uses_real_public_scientific_routes_and_response_models(visual_api):
    client,_=visual_api
    report=run_smoke(client,encounter_object_id='53495',persistence_object_id='34452',min_positions=2)
    assert report['status']=='PASSED' and len(report['workflow_results'])==6
    assert report['live_probability_status']=='UNAVAILABLE_NO_COVARIANCE'
    for entry in report['entries']:
        if entry['path']=='/openapi.json': continue
        matches=[r for r in app.routes if isinstance(r,APIRoute) and entry['method'] in r.methods
            and r.path_regex.fullmatch(entry['path'])]
        assert len(matches)==1
        TypeAdapter(matches[0].response_model).validate_python(entry['response'])
        assert entry['status_code']==200 and entry['payload_bytes']>0 and entry['elapsed_seconds']>0
    assert any(e['label']=='D.reference' for e in report['entries'])
    assert any(e['label']=='C.screen.2' for e in report['entries'])

def test_exact_openapi_contract_export_and_all_refs(tmp_path):
    (tmp_path/'FRONTEND_CONTRACT.md').write_text('Local contract test\n')
    export(tmp_path)
    expected=app.openapi()
    actual=json.loads((tmp_path/'openapi.json').read_text())
    assert actual==expected and len(actual['paths'])==21
    document=(tmp_path/'FRONTEND_CONTRACT.md').read_text()
    for path,operations in actual['paths'].items():
        for method in operations:
            assert f'{method.upper()} {path}' in document
    for model in actual['components']['schemas']:
        assert f'Schema: {model}' in document
    def walk(node):
        if isinstance(node,dict):
            if '$ref' in node:
                resolved=actual
                for key in node['$ref'][2:].split('/'): resolved=resolved[key]
            for value in node.values(): walk(value)
        elif isinstance(node,list):
            for value in node: walk(value)
    walk(actual)
    exported=(tmp_path/'openapi.json').read_bytes()
    export(tmp_path)
    assert exported==(tmp_path/'openapi.json').read_bytes()
    assert '/workspace/' not in exported.decode() and '/Users/' not in exported.decode()

def test_both_documented_error_shapes_are_actual(visual_api):
    client,_=visual_api
    scientific=client.get('/api/encounters/missing')
    assert scientific.status_code==404
    ScientificErrorResponse.model_validate(scientific.json())
    invalid=client.post('/api/positions',json={'object_ids':['0']})
    assert invalid.status_code==422
    ValidationFailure.model_validate(invalid.json())
    schema=client.get('/openapi.json').json()
    error=schema['paths']['/api/positions']['post']['responses']['422']['content']['application/json']['schema']
    assert len(error['anyOf'])==2

def test_checked_in_contract_matches_export():
    assert json.loads((ROOT/'openapi.json').read_text())==app.openapi()
    document=(ROOT/'FRONTEND_CONTRACT.md').read_text()
    assert 'no verified fully offline six-workflow server mode' in document
    assert 'ILLUSTRATIVE' in document and 'ITRS' in document
