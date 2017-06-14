import re
import ssl
import os
import json
import netifaces

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

_localbox_ip_list = None
def get_localbox_iplist():
    global _localbox_ip_list
    if _localbox_ip_list is not None:
        return _localbox_ip_list

    _localbox_ip_list = []
    for intf in netifaces.interfaces():
        for infos in netifaces.ifaddresses(intf).values():
            for info in infos:
                addr = info.get('addr')
                if addr and re.match(r'\d+\.\d+\.\d+\.\d+', addr):
                    _localbox_ip_list.append(addr)
    return _localbox_ip_list

def localbox_ip(*iplist):
    return set(get_localbox_iplist()).intersection(set(iplist))

def get_ssl_context(ssl_prefix):
    if ssl_prefix:
        ssl_cert = abs_path(
            'certs/{}/{}.crt'.format(ssl_prefix, ssl_prefix))
        ssl_key = abs_path(
            'certs/{}/{}.key'.format(ssl_prefix, ssl_prefix))
        ssl_context = ssl.create_default_context(
            purpose=ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(
            ssl_cert, ssl_key)
        return ssl_context

def get_cert_ssl_context(ssl_prefix):
    if ssl_prefix:
        ssl_cert = abs_path(
            'certs/{}/{}.crt'.format(ssl_prefix, ssl_prefix))
        ssl_context = ssl.create_default_context(
            purpose=ssl.Purpose.CLIENT_AUTH,
            cafile=ssl_cert)
        return ssl_context

