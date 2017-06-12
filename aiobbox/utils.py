import re
import os
import json

def guess_json(p):
    if p in ('null', 'true', 'false'):
        p = json.loads(p)
    elif p.startswith('{') or p.startswith('['):
        p = json.loads(p)
    elif p.startswith('"'):
        p = json.loads(p)
    elif p.isdigit() or re.match(r'\-?\d+$', p):
        p = int(p)
    elif re.match(r'\-?\d*(\.\d+)?$', p):
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

def abs_path(path):
    return os.path.join(os.getcwd(), path)

def home_path(path):
    return os.path.join(os.getenv('HOME'), path)

def force_str(v, encoding='utf-8'):
    if type(v) == bytes:
        return v.decode(encoding)
    else:
        return str(v)
