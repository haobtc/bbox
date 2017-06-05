import re
import json

def guess_json(p):
    if p == 'null':
        p = None
    elif p.isdigit():
        p = int(p)
    elif p.startswith('{') or p.startswith('['):
        p = json.loads(p)
    elif p.startswith('"'):
        p = json.loads(p)
    elif re.match(r'-?\d+$', p):
        p = int(p)
    elif re.match(r'-?\d*(\.\d+)?$', p):
        p = float(p)
    return p

def json_pp(v):
    return json.dumps(v, indent=2, sort_keys=True)

def json_to_str(v):
    return json.dumps(v, sort_keys=True)    

def import_module(spec):
    mod = __import__(spec)
    for sec in spec.split('.')[1:]:
        mod = getattr(mod, sec)
    return mod

        
