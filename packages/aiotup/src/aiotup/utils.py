import re
import json

def guess_json(p):
    if p == 'null':
        p = None
    elif p.isdigit():
        p = int(p)
    elif p.startswith('{') or p.startswith('['):
        p = json.loads(p)
    elif re.match(r'-?\d+$', p):
        p = int(p)
    elif re.match(r'-?\d*(\.\d+)?$', p):
        p = float(p)
    return p

def json_dumps(v):
    return json.dumps(v, indent=2, sort_keys=True)
