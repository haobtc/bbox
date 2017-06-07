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

def parse_method(method):
    return re.match(r'(?P<srv>\w[\.\w]*)::(?P<method>\w+)$',
                    method)

def parse_int(v):
    assert isinstance(v, (int, long))
    return v

def parse_float(v):
    assert isinstance(v, (int, float, long))
    return v

def parse_str(v):
    assert isinstance(v, str)

def assert_type(v, t):
    assert isinstance(v, t)
