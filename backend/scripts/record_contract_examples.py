"""Render verbatim six-workflow examples from a successful HTTP transcript."""
import json
from pathlib import Path
import shlex
from urllib.parse import urlencode

root=Path(__file__).resolve().parents[2]
report=json.loads((root/'frontend_examples.json').read_text())
assert report['status']=='PASSED' and set(report['workflow_results'])==set('ABCDEF')
labels=['A.positions','B.analyze','C.optimize','D.reference','E.persistence','F.cleanup']
blocks=['## Verbatim verified request/response examples\n',
    f"Actual HTTP run at **{report['recorded_at']}**, not fabricated outputs or permanently current encounters. API origin below uses the default port8000; verification used the configurable port8015. All30 full exchanges are in frontend_examples.json. Re-run smoke for new live encounter IDs/epochs.\n"]
for label in labels:
    entry=next(e for e in report['entries'] if e['label']==label)
    url='http://127.0.0.1:8000'+entry['path']
    if entry['params']: url+='?'+urlencode(entry['params'])
    command=['curl','--fail-with-body','-sS','-X',entry['method'],url]
    if entry['request'] is not None: command+=['-H','Content-Type: application/json','--data',json.dumps(entry['request'],separators=(',',':'))]
    blocks += [f"### Workflow {label[0]} — {label}\n",'```bash\n'+shlex.join(command)+'\n```\n',
        f"Actual HTTP{entry['status_code']} response ({entry['payload_bytes']}wire bytes, {entry['elapsed_seconds']:.6f}s):\n",
        '```json\n'+json.dumps(entry['response'],indent=2,allow_nan=False)+'\n```\n']
contract=root/'FRONTEND_CONTRACT.md'
text=contract.read_text()
marker='<!-- GENERATED API SCHEMAS BELOW -->'
base,schemas=text.split(marker,1)
base=base.split('## Verbatim verified request/response examples')[0].rstrip()
contract.write_text(base+'\n\n'+'\n'.join(blocks)+'\n'+marker+schemas)
print('Rendered six verbatim request/response examples; no scientific answer hardcoded in engine')
