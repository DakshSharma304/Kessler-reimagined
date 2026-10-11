"""Export actual OpenAPI and exact schema/endpoint appendix into the contract."""
import argparse
import json
from pathlib import Path
from app.main import app

MARKER='<!-- GENERATED API SCHEMAS BELOW -->'

def describe(schema):
    if not any(k in schema for k in ('type','$ref','anyOf','allOf','enum','const')): return 'any JSON'
    if '$ref' in schema: return schema['$ref'].rsplit('/',1)[-1]
    if 'anyOf' in schema: return ' \\| '.join(describe(s) for s in schema['anyOf'])
    if 'allOf' in schema: return ' & '.join(describe(s) for s in schema['allOf'])
    if 'enum' in schema: return ', '.join('`'+str(v)+'`' for v in schema['enum'])
    if 'const' in schema: return '`'+str(schema['const'])+'`'
    if schema.get('type')=='array':
        result='tuple['+', '.join(describe(s) for s in schema['prefixItems'])+']' if 'prefixItems' in schema else 'array<'+describe(schema.get('items',{}))+'>'
        bounds={k:schema[k] for k in ('minItems','maxItems') if k in schema}
        return result+(' '+json.dumps(bounds,separators=(',',':')) if bounds else '')
    if schema.get('type')=='object' and isinstance(schema.get('additionalProperties'),dict): return 'map<string,'+describe(schema['additionalProperties'])+'>'
    result=schema.get('type','object')
    if schema.get('format'): result+=' ('+schema['format']+')'
    if 'prefixItems' in schema: result+=' ['+', '.join(describe(s) for s in schema['prefixItems'])+']'
    limits={k:schema[k] for k in ('minimum','exclusiveMinimum','maximum','maxItems','minItems','pattern','maxLength') if k in schema}
    if limits: result+=' '+json.dumps(limits,separators=(',',':'))
    return result.replace('|','\\|')

def export(directory):
    schema=app.openapi()
    (directory/'openapi.json').write_text(json.dumps(schema,indent=2,sort_keys=True,allow_nan=False)+'\n')
    text=['\n## Exact generated endpoint and schema appendix\n',
        'Generated from the running application models, not guessed endpoints. `openapi.json` is the machine-readable authority. Missing optional fields and null are distinct; required is shown below. Objects/maps declared open-ended retain their documented scientific/provenance contents.\n']
    for path,operations in schema['paths'].items():
        for method,operation in operations.items():
            if method not in {'get','post'}: continue
            text.extend([f'\n### {method.upper()} {path}\n','| Input | Location | Required | Schema |\n| --- | --- | --- | --- |'])
            for param in operation.get('parameters',[]):
                text.append(f"| {param['name']} | {param['in']} | {param.get('required',False)} | {describe(param['schema'])} |")
            body=operation.get('requestBody')
            if body: text.append(f"| body | JSON | {body.get('required',False)} | {describe(body['content']['application/json']['schema'])} |")
            text.append('\nResponses:\n')
            for status,response in operation['responses'].items():
                content=response.get('content',{}).get('application/json',{})
                text.append(f"- HTTP{status}: {describe(content.get('schema',{}))}")
    for name,model in sorted(schema['components']['schemas'].items()):
        text.extend([f'\n### Schema: {name}\n',model.get('description',''),
            '\n| Field | Required | Type / constraints | Default |\n| --- | --- | --- | --- |'])
        for field,definition in model.get('properties',{}).items():
            default=json.dumps(definition['default']) if 'default' in definition else '—'
            text.append(f"| {field} | {field in model.get('required',[])} | {describe(definition)} | {default} |")
        if not model.get('properties'): text.append('\n'+describe(model))
    contract=directory/'FRONTEND_CONTRACT.md'
    base=contract.read_text().split(MARKER)[0].rstrip()
    contract.write_text(base+'\n\n'+MARKER+'\n'+'\n'.join(text)+'\n')
    print(f'Exported {len(schema["paths"])} paths / {len(schema["components"]["schemas"])} schemas to {directory}')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory',type=Path,default=Path(__file__).resolve().parents[2])
    export(parser.parse_args().output_directory)

if __name__=='__main__': main()
